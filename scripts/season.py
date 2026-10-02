"""The coming season's fixture list, rebuilt from the tournament crawl.

  python3 scripts/season.py            ->  data/upcoming_vb.json
                                           data/season_p1440.json

data/upcoming.json was pulled from a Volleyball Life feed whose endpoint is no longer
reachable, so it is frozen at the day it was taken and misses everything published since
-- including the whole p1440 Futures Tour calendar. The crawl walks tournament ids, which
still works, so the forward schedule is rebuilt from it instead.

Only girls' and women's DOUBLES draws count, on the same rule the rest of the repo uses:
a division of exactly two players. An event with no such draw is dropped entirely.
"""
import json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
VB = os.path.join(HERE, "..", "data", "vb")
DATA = os.path.join(HERE, "..", "data")
# p1440 runs the Futures Tour under two organiser ids; 41 is the old foundation account.
P1440_ORGS = {41, 1144}


def rows(name):
    with open(os.path.join(VB, name)) as fh:
        return [json.loads(l) for l in fh]


def main(since=None):
    since = since or "2026-08-12"
    tours = {t["id"]: t for t in rows("tournaments.jsonl")}
    divs = defaultdict(list)
    for d in rows("divisions.jsonl"):
        divs[d["tid"]].append(d)

    out = []
    for t in tours.values():
        if t["start"] < since or not t.get("public"):
            continue
        ds = [d for d in divs.get(t["id"], [])
              if d["players"] == 2 and (d["gender"] or "") in ("Girls", "Womens")
              and not d.get("canceled")]
        if not ds:
            continue
        venues = []
        for d in ds:
            if d.get("venue") and d["venue"] not in venues:
                venues.append(d["venue"])
        out.append({"id": t["id"], "startDate": t["start"], "endDate": t["end"],
                    "name": t["name"], "org": t["org"], "orgId": t["orgId"],
                    "sanctionedBy": t["sanction"], "national": t["national"],
                    "locations": venues[:2],
                    "divisions": [{"name": d["name"], "gender": d["gender"],
                                   "age": d["age"], "teams": d["teams"]} for d in ds]})
    out.sort(key=lambda e: (e["startDate"], e["name"]))
    json.dump(out, open(os.path.join(DATA, "upcoming_vb.json"), "w"), indent=1)

    tour = [e for e in out if e["orgId"] in P1440_ORGS]
    json.dump(tour, open(os.path.join(DATA, "season_p1440.json"), "w"), indent=1)
    print(f"{len(out)} upcoming events with a girls'/women's doubles draw from {since}")
    print(f"{len(tour)} of them run by p1440:")
    for e in tour:
        print(f"  {e['startDate']}  {e['name'][:56]:56} "
              f"{', '.join(d['name'] for d in e['divisions'])[:46]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
