import json
from collections import defaultdict

d = json.load(open("clean.json"))
entries, tour_info, tv = d["entries"], d["tour_info"], d["truvolley"]

# player -> tid -> best entry (lowest finish if multiple divisions)
pt = defaultdict(dict)
for name, es in entries.items():
    for e in es:
        tid = str(e["tid"])
        cur = pt[name].get(tid)
        if cur is None or (e["finish"] or 999) < (cur["finish"] or 999):
            pt[name][tid] = e

shared = defaultdict(list)
for name, ts in pt.items():
    for tid in ts:
        shared[tid].append(name)

rows = sorted(shared.items(), key=lambda kv: (-len(kv[1]), tour_info[kv[0]]["date"]))
dist = defaultdict(int)
for tid, ns in rows:
    dist[len(ns)] += 1
print("players-per-tournament:", dict(sorted(dist.items(), reverse=True)))
print("total distinct events:", len(rows))

print("\n%-4s %-11s %-58s %s" % ("N", "DATE", "TOURNAMENT", "SANCTION"))
for tid, ns in rows:
    if len(ns) < 3:
        continue
    ti = tour_info[tid]
    print("\n%-4d %-11s %-58s %s" % (len(ns), ti["date"], ti["name"][:58], ti["sanction"]))
    for n in sorted(ns, key=lambda n: (pt[n][tid]["finish"] or 999)):
        e = pt[n][tid]
        f = e["field"]
        print("        %-20s %3s/%-4s  %-28s  w/ %s" % (
            n, e["finish"], f if f else "?", e["division"][:28],
            ", ".join(e["partners"])[:34]))

print("\n\n=== TruVolley ===")
for n in sorted(tv, key=lambda x: -(tv[x]["truvolley"] or 0)):
    p = tv[n]
    print("%-20s TV %-6s peak %-6s conf %-4s  %d-%d matches  %s / %s" % (
        n, p["truvolley"], p["tvPeak"], p["tvConfidence"], p["tvWins"],
        p["tvMatches"] - p["tvWins"], p["cityState"], p["club"]))

miss = [(n, t) for n in pt for t in pt[n] if not pt[n][t]["field"]]
print("\nmissing field size:", len(miss), miss[:10])
json.dump({"pt": {k: v for k, v in pt.items()}, "shared": dict(shared)},
          open("final.json", "w"), indent=1)
