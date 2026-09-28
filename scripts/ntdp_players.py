"""Resolve every Beach NTDP roster athlete to a Volleyball Life profile and pull
her current TruVolley.

  python3 scripts/ntdp_players.py    ->  data/ntdp/players.json

Names are canonicalised first (ntdp_names.py). Every roster spelling of an
athlete is searched, because one spelling often resolves where another does not.
Two canonical names that land on the same profile id are then merged -- that is
what catches "Jess"/"Jessica Horwath" and "Babi"/"Gabriella Gubbins", which no
amount of string cleaning would.

TruVolley is refetched rather than read from data/tvcache.json: that cache
predates the September 2026 rating replacement, and mixing the two epochs is
what put a 9.2 next to a 10.5 on an earlier page.

Home town and club come from the same profile. They are what the athlete last
put there, so a club can be a season or two out of date -- USAV's own roster
region is carried separately, per series, and is the fallback when the profile
gives no town.
"""
import json, os, re, sys, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ntdp_names import clean, key, display

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "ntdp")
API = "https://api-v8.volleyballlife.com"
H = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"),
     "Accept": "application/json"}


def get(p, tries=3):
    for _ in range(tries):
        try:
            r = urllib.request.Request(API + p, headers=H)
            return json.loads(urllib.request.urlopen(r, timeout=30).read())
        except Exception:
            pass
    return None


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def variants_of_rosters():
    rows = [r for r in json.load(open(os.path.join(DATA, "rosters.json")))
            if not re.match(r"(boys|men)", (r["division"] or ""), re.I)]
    v = defaultdict(set)
    for r in rows:
        # Keep first and last apart: rebuilding them from the joined string
        # splits "Le Blanc" down the middle and loses the profile.
        v[key(r["first"], r["last"])].add((clean(r["first"]), clean(r["last"])))
    return v


def resolve(spellings):
    """Search every spelling; keep the profile with a birthdate and most matches."""
    best = None
    for first, last in sorted(spellings):
        res = get("/playerprofile/search/" + urllib.parse.quote(f"{first} {last}")) or []
        cands = [p for p in res if norm(p.get("firstName")) == norm(first)
                 and norm(p.get("lastName")) == norm(last)]
        if not cands:
            # A nickname on the profile ("Babi" for a roster's "Gabriella") only
            # ever resolves on the surname, so accept that -- but only when the
            # surname picks out a single profile, never one of several.
            sur = [p for p in res if norm(p.get("lastName")) == norm(last)]
            cands = sur if len(sur) == 1 else []
        for c in cands[:4]:
            pr = get(f"/playerprofile/{c['id']}") or {}
            tv = get(f"/playerprofile/{c['id']}/truvolley") or {}
            cand = {"id": c["id"], "dob": (pr.get("dob") or "")[:10] or None,
                    "grad": pr.get("gradYear") or None, "club": pr.get("club") or None,
                    "city": pr.get("city") or None, "state": pr.get("state") or None,
                    "tv": tv.get("truVolley") or None, "conf": tv.get("confidence") or 0,
                    "peak": tv.get("peak") or None, "m": tv.get("matchesPlayed") or 0,
                    "w": tv.get("wins") or 0}
            if best is None or (cand["dob"] and not best["dob"]) or \
               (bool(cand["dob"]) == bool(best["dob"]) and cand["m"] > best["m"]):
                best = cand
    return best or {}


def main():
    v = variants_of_rosters()
    print(f"{len(v)} canonical athletes", flush=True)
    out = {}
    with ThreadPoolExecutor(8) as ex:
        for i, (k, r) in enumerate(zip(v, ex.map(resolve, v.values())), 1):
            names = sorted(f"{f} {l}" for f, l in v[k])
            out[k] = {"name": display(names), "spellings": names, **r}
            if i % 40 == 0:
                print(f"  {i}/{len(v)}", flush=True)

    # Two canonical names on one profile are one athlete. Fold the later key
    # into the earlier and record the fold, so the page can drop the duplicate.
    byid = defaultdict(list)
    for k, r in out.items():
        if r.get("id"):
            byid[r["id"]].append(k)
    for pid, ks in byid.items():
        if len(ks) < 2:
            continue
        keep = max(ks, key=lambda k: len(out[k]["spellings"][0]))
        for k in ks:
            if k != keep:
                out[keep]["spellings"] = sorted(set(out[keep]["spellings"])
                                                | set(out[k]["spellings"]))
                out[k] = {"same_as": keep}
        out[keep]["name"] = display(out[keep]["spellings"])
        print(f"  profile {pid}: {' = '.join(ks)} -> {out[keep]['name']}")

    json.dump(out, open(os.path.join(DATA, "players.json"), "w"), indent=1, sort_keys=True)
    live = {k: r for k, r in out.items() if "same_as" not in r}
    print(f"wrote players.json -- {len(live)} athletes, "
          f"{sum(1 for r in live.values() if r.get('id'))} with a profile, "
          f"{sum(1 for r in live.values() if r.get('tv'))} with a TruVolley, "
          f"{sum(1 for r in live.values() if r.get('city'))} with a town, "
          f"{sum(1 for r in live.values() if r.get('club'))} with a club")


if __name__ == "__main__":
    main()
