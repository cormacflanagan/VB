import json
from collections import defaultdict

d = json.load(open("clean.json"))
entries, tour_info, tv = d["entries"], d["tour_info"], d["truvolley"]

REGION = {
    "Simrin Adams": "So. Cal / So. Nevada", "Sarah Albers": "Gateway",
    "Sienna Castillo": "Northern California", "Sarah Cowan": "Florida",
    "Sadie Harris": "So. Cal / So. Nevada", "Olivia Herron": "North Texas",
    "Sage Illian": "Heart of America", "Lauren Leach": "So. Cal / So. Nevada",
    "Georgeann Lee": "Aloha", "Janie McCanna": "Puget Sound",
    "Milaniakai Padilla": "Aloha", "Sadie Stafford": "Old Dominion",
    "Jordyn Wilson": "So. Cal / So. Nevada",
}
SHORT = json.load(open("shortnames.json"))
TEAM_DIVS = {"Open (5v5)", "OPEN Division", "Club Open"}

# key = (tournament id, tournament-division id) -> one competition
comp = {}
who = defaultdict(dict)
for name, es in entries.items():
    for e in es:
        k = f'{e["tid"]}:{e["tdId"]}'
        ti = tour_info[str(e["tid"])]
        comp[k] = {
            "key": k, "tid": e["tid"], "tdId": e["tdId"],
            "event": ti["name"].strip(),
            "short": SHORT.get(ti["name"], ti["name"][:24]),
            "division": e["division"].strip(), "field": e["field"],
            "date": ti["date"], "sanction": ti["sanction"] or "—",
            "team": e["division"].strip() in TEAM_DIVS,
        }
        # a player should have exactly one row per competition
        who[k][name] = e

dist = defaultdict(int)
for k, m in who.items():
    dist[len(m)] += 1
print("players-per-competition:", dict(sorted(dist.items(), reverse=True)))
print("total competitions:", len(who))
for t in (2, 3, 4):
    print(f"  shared by >={t}: {sum(v for n, v in dist.items() if n >= t)}")

dupes = [(k, n) for k, m in who.items() for n in m
         if len([x for x in entries[n] if f'{x["tid"]}:{x["tdId"]}' == k]) > 1]
print("duplicate player-competition rows:", len(dupes))

THRESH = 3
cols = [comp[k] for k, m in who.items() if len(m) >= THRESH]
cols.sort(key=lambda c: (-len(who[c["key"]]), c["date"], c["division"]))
for c in cols:
    c["n"] = len(who[c["key"]])

print(f"\n{'N':>3}  {'DATE':10}  {'FIELD':>5}  EVENT / DIVISION")
for c in cols:
    print(f"{c['n']:3d}  {c['date']}  {str(c['field']):>5}  {c['short']} — {c['division']}")

pl = []
for name in sorted(tv, key=lambda x: -(tv[x]["truvolley"] or 0)):
    p = tv[name]
    cells = {}
    for c in cols:
        e = who[c["key"]].get(name)
        if e:
            cells[c["key"]] = {"f": e["finish"], "partners": e["partners"]}
    pl.append({
        "name": name, "region": REGION[name], "club": p["club"], "city": p["cityState"],
        "tv": p["truvolley"], "peak": p["tvPeak"], "w": p["tvWins"],
        "l": p["tvMatches"] - p["tvWins"], "played": len(entries[name]),
        "comps": len({f'{x["tid"]}:{x["tdId"]}' for x in entries[name]}),
        "cells": cells,
    })

pairs = []
for k, m in who.items():
    if len(m) == 2:
        c = dict(comp[k])
        c["players"] = sorted(({"name": n, "f": e["finish"]} for n, e in m.items()),
                              key=lambda x: x["f"])
        pairs.append(c)
pairs.sort(key=lambda c: c["date"], reverse=True)

json.dump({"players": pl, "comps": cols, "totalComps": len(who), "pairs": pairs},
          open("site_data2.json", "w"), indent=1)
print("two-player competitions:", len(pairs))
print("\nplayers:", len(pl), "columns:", len(cols))
for p in pl:
    pod = sum(1 for c in p["cells"].values() if c["f"] <= 3)
    print(f"  {p['name']:20s} TV{p['tv']:<7} in {len(p['cells']):2d} shared comps, {pod} podiums")
