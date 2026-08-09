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

SHORT = {
    "AVP Juniors National Championships 2026": "AVP Jrs Nationals",
    "2026 USA Volleyball U18 Beach National Team Trials": "USAV U18 Trials",
    "2026 USA Volleyball Youth Olympic Games Trials": "USAV YOG Trials",
    "AVP Juniors West Coast Championships 2025": "AVP Jrs West Coast",
    "2026 Futures Tour: Arizona": "Futures Tour: Arizona",
    "2026 Futures Tour Spring Championship": "Futures Spring Champ",
    "33rd AAU Hermosa Beach National Pairs Championships ": "AAU Hermosa Nat'l Pairs",
    "2025-26 BVCA Orange County Winter": "BVCA Orange Cty Winter",
    "2025-26 BVCA Orange County Spring": "BVCA Orange Cty Spring",
    "2025-26 USA Volleyball Beach Tour - Gulf Coast Region - BeachFest National Qualifier": "USAV BeachFest Qualifier",
    "6/13/26, Manhattan Pier, Manhattan Beach": "Manhattan Pier Open",
    "2026 BVCA Individual Pairs National Championship ": "BVCA Pairs Nationals",
    "Kauai Beach Volleyball BVCA National Qualifier '25": "BVCA Kauai Qualifier",
    "2025-26 BVCA Orange County Fall": "BVCA Orange Cty Fall",
    "2026 Futures Tour: Alabama": "Futures Tour: Alabama",
    "2026 BVCA Club V Club National Championships ": "BVCA Club v Club Nats",
    "AAU Herrmosa Beach Winter Series Championships": "AAU Hermosa Winter",
    "BVCA 300 Open Invitational- Oceanside CA.": "BVCA 300 Oceanside",
    "2026 Futures Tour: Florida": "Futures Tour: Florida",
    "AAU Super Regional ": "AAU Super Regional",
    ", 6/14/26, North Beach, Santa Monica": "North Beach Santa Monica",
    "AVP Next Men’s & Women’s Fall Triple Crown Series #1 $8,000 Purse": "AVP Next Triple Crown 1",
    "Women's Open at Newland, Huntington Beach": "Newland Women's Open",
    "Beach Elite SoCal Series Winter #5 (AVP 3 STAR)-  2026 ": "Beach Elite SoCal W5",
    "AVP Austin Open": "AVP Austin Open",
    "West Coast Championships (p1440) & Boys 17U ISF Trials ": "p1440 West Coast Champ",
    "BVCA Pairs West Coast Championships 2026": "BVCA Pairs West Coast",
}

TEAM_EVENTS = {"Open (5v5)", "OPEN Division", "Club Open"}

# player -> tid -> best entry, plus all entries
best, allent = defaultdict(dict), defaultdict(lambda: defaultdict(list))
for name, es in entries.items():
    for e in es:
        tid = str(e["tid"])
        allent[name][tid].append(e)
        cur = best[name].get(tid)
        if cur is None or (e["finish"] or 999) < (cur["finish"] or 999):
            best[name][tid] = e

shared = defaultdict(list)
for name, ts in best.items():
    for tid in ts:
        shared[tid].append(name)

events = [(tid, ns) for tid, ns in shared.items() if len(ns) >= 3]
events.sort(key=lambda kv: (-len(kv[1]), tour_info[kv[0]]["date"]))

ev_out = []
for tid, ns in events:
    ti = tour_info[tid]
    fmt = "team"
    for n in ns:
        if best[n][tid]["division"] not in TEAM_EVENTS:
            fmt = "pairs"
            break
    ev_out.append({
        "id": tid, "name": ti["name"].strip(), "short": SHORT.get(ti["name"], ti["name"][:22]),
        "date": ti["date"], "sanction": ti["sanction"] or "—",
        "n": len(ns), "format": fmt,
    })

pl_out = []
for name in sorted(tv, key=lambda x: -(tv[x]["truvolley"] or 0)):
    p = tv[name]
    cells = {}
    for tid, ns in events:
        if name not in ns:
            continue
        e = best[name][tid]
        extra = [x for x in allent[name][tid] if x is not e]
        cells[tid] = {
            "f": e["finish"], "y": e["field"], "div": e["division"],
            "partners": e["partners"],
            "extra": [{"f": x["finish"], "y": x["field"], "div": x["division"]} for x in extra],
        }
    pl_out.append({
        "name": name, "region": REGION[name], "club": p["club"], "city": p["cityState"],
        "tv": p["truvolley"], "peak": p["tvPeak"], "conf": p["tvConfidence"],
        "w": p["tvWins"], "l": p["tvMatches"] - p["tvWins"],
        "played": len(entries[name]), "cells": cells,
    })

out = {"players": pl_out, "events": ev_out,
       "window": {"from": "2025-08-09", "to": "2026-08-09"}}
json.dump(out, open("site_data.json", "w"), indent=1)
print("events:", len(ev_out), "players:", len(pl_out))
for p in pl_out:
    pod = sum(1 for c in p["cells"].values() if c["f"] and c["f"] <= 3)
    print(f"  {p['name']:20s} TV{p['tv']:<7} shared={len(p['cells']):2d} podiums={pod}")
