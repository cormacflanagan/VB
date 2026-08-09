import json, urllib.request, time
from collections import defaultdict

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def req(path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    h = dict(HDRS)
    if data is not None:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(API + path, data=body, headers=h)
    for a in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if a == 4:
                print("FAIL", path, e); return None
            time.sleep(2 ** a)


PLAYERS = [("Simrin Adams", 25289), ("Sarah Albers", 84161), ("Sienna Castillo", 29854),
           ("Sarah Cowan", 84725), ("Sadie Harris", 94909), ("Olivia Herron", 28688),
           ("Sage Illian", 91052), ("Lauren Leach", 8426), ("Georgeann Lee", 61785),
           ("Janie McCanna", 24515), ("Milaniakai Padilla", 95165),
           ("Sadie Stafford", 147394), ("Jordyn Wilson", 23868)]
CUTOFF, TODAY = "2025-08-09", "2026-08-09"

raw = json.load(open("raw.json"))
profiles = {}
for name, pid in PLAYERS:
    prof = req(f"/playerprofile/{pid}")
    profiles[name] = [t for t in (prof or {}).get("tournaments", [])
                      if CUTOFF <= t["date"][:10] <= TODAY]
    print(f"{name:20s} {len(profiles[name])} entries in window")
    time.sleep(0.3)

tids = sorted({t["id"] for v in profiles.values() for t in v})
counts = dict(raw["counts"])
missing = [t for t in tids if str(t) not in counts]
print("tournaments:", len(tids), "need counts:", len(missing))
for i in range(0, len(missing), 40):
    res = req("/Tournament/CountsV3Bulk", {"tournamentIds": missing[i:i + 40]})
    if res:
        counts.update(res)
    time.sleep(0.4)

divcount, divname = {}, {}
for tid, divs in counts.items():
    for d in divs or []:
        divcount[d["id"]] = d["teamCount"]
        divname[d["id"]] = d["name"]

COACH = ("coach", "coaches", "spectator", "parent")
entries = defaultdict(list)
tour_info = {}
for name, ts in profiles.items():
    for t in ts:
        dn = (t.get("division") or "")
        if any(c in dn.lower() for c in COACH):
            continue
        if t.get("finish") in (None, 0):
            continue
        entries[name].append({
            "tid": t["id"], "tdId": t.get("tdId"), "division": dn,
            "finish": t["finish"], "field": divcount.get(t.get("tdId")),
            "date": t["date"][:10],
            "partners": [p["name"] for p in (t.get("partners") or [])],
        })
        tour_info[t["id"]] = {"name": t["tournament"], "date": t["date"][:10],
                              "sanction": t.get("sanctioningBodyId")}

for n in entries:
    print(f"{n:20s} competitive entries: {len(entries[n])}")
json.dump({"entries": dict(entries), "tour_info": tour_info,
           "divcount": divcount, "divname": divname,
           "truvolley": {n: raw["players"][n] for n, _ in PLAYERS}},
          open("clean.json", "w"), indent=1)
print("saved clean.json")
