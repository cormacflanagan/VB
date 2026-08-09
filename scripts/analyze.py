import json
from collections import defaultdict

raw = json.load(open("raw.json"))
players, counts = raw["players"], raw["counts"]

# division id -> teamCount
divcount = {}
tour_divs = defaultdict(list)
for tid, divs in counts.items():
    for d in divs or []:
        divcount[d["id"]] = d["teamCount"]
        tour_divs[int(tid)].append(d)

# player -> tournament id -> list of entries
entries = defaultdict(dict)
tour_info = {}
for name, p in players.items():
    full = p.get("full", {})
    for t in p["tournaments"]:
        tid = t["id"]
        ft = full.get(str(tid)) or full.get(tid) or {}
        tdid = ft.get("tdId")
        y = divcount.get(tdid)
        entries[name][tid] = {
            "finish": t["finish"], "division": t["division"], "tdId": tdid,
            "field": y, "date": t["date"][:10],
            "partners": [x["name"] for x in (t.get("partners") or [])],
        }
        tour_info[tid] = {"name": t["tournament"], "date": t["date"][:10],
                          "sanction": t.get("sanctioningBodyId")}

# how many players per tournament
shared = defaultdict(list)
for name, ts in entries.items():
    for tid in ts:
        shared[tid].append(name)

by_n = defaultdict(int)
for tid, ns in shared.items():
    by_n[len(ns)] += 1
print("players-per-tournament distribution:", dict(sorted(by_n.items(), reverse=True)))

print("\n=== Tournaments with >=3 of the 13 girls ===")
rows = sorted(shared.items(), key=lambda kv: (-len(kv[1]), tour_info[kv[0]]["date"]))
for tid, ns in rows:
    if len(ns) < 3:
        continue
    ti = tour_info[tid]
    print(f"\n[{len(ns)}] {ti['date']}  {ti['name'][:70]}  (id={tid}, {ti['sanction']})")
    for n in sorted(ns, key=lambda n: entries[n][tid]["finish"] or 999):
        e = entries[n][tid]
        print(f"     {n:20s} {str(e['finish']):>4s}/{str(e['field']):<4s} {e['division'][:26]}")

print("\n=== Tournaments with exactly 2 ===")
for tid, ns in rows:
    if len(ns) == 2:
        ti = tour_info[tid]
        det = ", ".join(f"{n} {entries[n][tid]['finish']}/{entries[n][tid]['field']}" for n in ns)
        print(f"  {ti['date']} {ti['name'][:55]:55s} | {det}")

missing = [(n, tid) for n in entries for tid in entries[n] if entries[n][tid]["field"] is None]
print("\nentries missing field size:", len(missing))
json.dump({"entries": {k: {str(a): b for a, b in v.items()} for k, v in entries.items()},
           "tour_info": {str(k): v for k, v in tour_info.items()},
           "shared": {str(k): v for k, v in shared.items()}},
          open("analysis.json", "w"), indent=1)
