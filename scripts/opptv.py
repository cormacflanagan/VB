"""Published TruVolley for the opponents the junior cache does not carry.

  python3 scripts/opptv.py                  ->  data/opptv.json
  python3 scripts/opptv.py 64896 12345      ->  the same, for named players

`tvcache.json` holds the 17,178 juniors the rosters are cut from, which is the right
population for a roster cut and the wrong one for an opponent list. A Santa Cruz Women's
Open field is mostly adults: college players, post-college, the occasional AVP entrant.
None of them are in the junior cache, so every match against them was silently dropped as
"unrated" -- including the two results that most distinguish this player's year, the
playoff wins over Fleming/Vugrincic and Reese/Stowell, both teams rated above her.

Fetching TruVolley for the whole opponent graph would be a second 17k crawl. Fetching it
for one player's opponents is a few hundred requests, so the scan is deliberately scoped
to the players named on the command line and their opponents only.

Ids at or above 90,000,000 are the synthetic ones merge.py assigns to CBVA and college
players it could not resolve to a Volleyball Life profile. They have no profile to fetch
and are skipped rather than retried every run.
"""
import json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")  # the API 404s a short UA
HDRS = {"User-Agent": UA, "Accept": "application/json"}
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "opptv.json")
SYNTH = 90_000_000
DEFAULT = [64896]

sys.path.insert(0, HERE)
from jsonl import read as read_jsonl


def get(path, tries=3):
    for _ in range(tries):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception:
            pass
    return None


def main(players):
    tv = {int(k) for k, v in json.load(open(os.path.join(DATA, "tvcache.json"))).items()
          if v.get("tv")}
    cache = json.load(open(OUT)) if os.path.exists(OUT) else {}
    want = set()
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        side = set(m["a"]) & set(players) or set(m["b"]) & set(players)
        if not side:
            continue
        opp = m["b"] if set(m["a"]) & set(players) else m["a"]
        for o in opp:
            if o < SYNTH and o not in tv and str(o) not in cache:
                want.add(o)
    print(f"{len(want)} opponents to look up ({len(cache)} already cached)", flush=True)
    if want:
        def one(i):
            t = get(f"/playerprofile/{i}/truvolley") or {}
            p = get(f"/playerprofile/{i}") or {}
            return str(i), {"tv": t.get("truVolley") or None,
                            "conf": t.get("confidence"),
                            "name": (f"{p.get('firstName','')} {p.get('lastName','')}".strip()
                                     or None),
                            "grad": p.get("gradYear") or None}
        with ThreadPoolExecutor(8) as ex:
            for k, v in ex.map(one, sorted(want)):
                cache[k] = v
    json.dump(cache, open(OUT, "w"), indent=1, sort_keys=True)
    rated = sum(1 for v in cache.values() if v.get("tv"))
    print(f"data/opptv.json: {len(cache)} players, {rated} carrying a rating")


if __name__ == "__main__":
    main([int(x) for x in sys.argv[1:]] or DEFAULT)
