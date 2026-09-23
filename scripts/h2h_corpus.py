"""Head-to-head between the members of a group, rebuilt from the merged corpus.

  python3 scripts/h2h_corpus.py 19U     ->  data/19U_h2h.json

`h2h.py` reads POST /playerprofile/feed/matches, which now requires a signed-in account
and answers 401 to everyone else. That left new groups with no crosstable at all and the
existing ones frozen on a 20 August pull.

The same matches are in `data/all_matches.jsonl`: Volleyball Life's own feed as crawled
before it closed, plus CBVA's public games. So this produces the identical file shape
from the corpus instead of the API, which has two consequences worth stating on the page.
It reaches only as far as the corpus does -- a match played after the last crawl is not
here -- and it *gains* the open-draw matches Volleyball Life never filed as matches at
all, because Volleyball Life records a CBVA event as a finish order and nothing else.

Event and division names are not carried on corpus rows, so they are recovered from the
per-group `tour_info` the collectors already save and from the CBVA tournament index.
"""
import datetime, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
sys.path.insert(0, HERE)
from jsonl import read as read_jsonl


def labels():
    """tid -> (event name, division) for both sources."""
    ev = {}
    for f in sorted(os.listdir(DATA)):
        if f.endswith("_clean.json"):
            d = json.load(open(os.path.join(DATA, f)))
            for k, t in (d.get("tour_info") or {}).items():
                if isinstance(t, dict) and t.get("name"):
                    ev.setdefault(int(k), (t["name"], ""))
    p = os.path.join(DATA, "cbva", "tournaments.jsonl")
    if os.path.exists(p):
        for t in read_jsonl(p):
            nm = t.get("name") or t.get("venue") or "CBVA"
            ev.setdefault(t["id"], (nm, t.get("venue") or ""))
    return ev


def build(group):
    site = json.load(open(os.path.join(DATA, f"{group}_site.json")))
    ids = {p["id"]: p["name"] for p in site["players"]}
    lo, hi = site["window"]
    ev = labels()
    h2h = defaultdict(lambda: {"w": 0, "l": 0, "games": []})
    partnered = defaultdict(int)
    seen, n = set(), 0
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        if not (lo <= m["date"] <= hi):
            continue
        a = [i for i in m["a"] if i in ids]
        b = [i for i in m["b"] if i in ids]
        if not a and not b:
            continue
        # a pair from the group on the same side partnered; that is not a head-to-head
        for side in (a, b):
            for i in range(len(side)):
                for j in range(i + 1, len(side)):
                    partnered[tuple(sorted((side[i], side[j])))] += 1
        if not a or not b:
            continue
        sig = (m["date"], m.get("tdId"), tuple(tuple(s) for s in (m.get("sets") or [])))
        if sig in seen:
            continue
        seen.add(sig)
        n += 1
        name, div = ev.get(m.get("tid"), ("", ""))
        for x in a:
            for y in b:
                rec = h2h[(x, y)]
                rec["w" if m["aWon"] else "l"] += 1
                rec["games"].append({
                    "date": m["date"], "event": name, "division": div,
                    "tid": m.get("tid"), "tdId": m.get("tdId"),
                    "phase": m.get("phase") or "", "round": str(m.get("round") or ""),
                    "won": bool(m["aWon"]), "sets": m.get("sets") or [],
                    "with": [ids.get(i, i) for i in m["a"] if i != x],
                    "against": [ids.get(i, i) for i in m["b"] if i != y],
                })
    pairs = {}
    for (x, y) in list(h2h):
        k = tuple(sorted((x, y)))
        if k in pairs:
            continue
        fwd = h2h.get((k[0], k[1]), {"w": 0, "l": 0, "games": []})
        rev = h2h.get((k[1], k[0]), {"w": 0, "l": 0, "games": []})
        games = fwd["games"] + [dict(g, won=not g["won"],
                                     sets=[[s[1], s[0]] for s in g["sets"]])
                                for g in rev["games"]]
        games.sort(key=lambda z: z["date"])
        pairs[k] = {"a": ids[k[0]], "b": ids[k[1]], "aId": k[0], "bId": k[1],
                    "aWins": fwd["w"] + rev["l"], "bWins": fwd["l"] + rev["w"],
                    "games": games}
    out = {"group": group, "players": {str(i): nm for i, nm in ids.items()},
           "asof": datetime.date.today().isoformat(),
           "source": "corpus",       # the page says so: this is not the live feed
           "matches": n,
           "pairs": sorted(pairs.values(), key=lambda p: -(p["aWins"] + p["bWins"])),
           "partnered": [{"a": ids[k[0]], "b": ids[k[1]], "matches": v}
                         for k, v in sorted(partnered.items(), key=lambda kv: -kv[1])]}
    json.dump(out, open(os.path.join(DATA, f"{group}_h2h.json"), "w"), indent=1)
    tot = sum(p["aWins"] + p["bWins"] for p in out["pairs"])
    print(f"{group}: {len(out['pairs'])} head-to-head pairings, {tot} matches between "
          f"group members, {len(out['partnered'])} partnerships")
    return out


if __name__ == "__main__":
    for g in (sys.argv[1:] or ["19U"]):
        build(g)
