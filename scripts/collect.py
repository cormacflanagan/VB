import json, urllib.request, urllib.parse, time, datetime

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def req(path, data=None):
    url = API + path
    body = None
    hdrs = dict(HDRS)
    if data is not None:
        body = json.dumps(data).encode()
        hdrs["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=hdrs)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == 4:
                print("FAIL", path, e)
                return None
            time.sleep(2 ** attempt)


PLAYERS = [
    ("Simrin Adams", 25289, "SCSN"),
    ("Sarah Albers", 84161, "Gateway"),
    ("Sienna Castillo", 29854, "N. California"),
    ("Sarah Cowan", 84725, "Florida"),
    ("Sadie Harris", 94909, "SCSN"),
    ("Olivia Herron", 28688, "North Texas"),
    ("Sage Illian", 91052, "Heart of America"),
    ("Lauren Leach", 8426, "SCSN"),
    ("Georgeann Lee", 61785, "Aloha"),
    ("Janie McCanna", 24515, "Puget Sound"),
    ("Milaniakai Padilla", 95165, "Aloha"),
    ("Sadie Stafford", 147394, "Old Dominion"),
    ("Jordyn Wilson", 23868, "SCSN"),
]

CUTOFF = "2025-08-09"
TODAY = "2026-08-09"

data = {}
for name, pid, region in PLAYERS:
    fin = req(f"/playerprofile/{pid}/finishes")
    tv = req(f"/playerprofile/{pid}/truvolley")
    tours = [t for t in (fin or {}).get("tournaments", [])
             if CUTOFF <= t["date"][:10] <= TODAY]
    data[name] = {
        "id": pid, "region": region,
        "club": (fin or {}).get("club"),
        "cityState": (fin or {}).get("cityState"),
        "truvolley": (tv or {}).get("truVolley"),
        "tvConfidence": (tv or {}).get("confidence"),
        "tvPeak": (tv or {}).get("peak"),
        "tvMatches": (tv or {}).get("matchesPlayed"),
        "tvWins": (tv or {}).get("wins"),
        "allCount": len((fin or {}).get("tournaments", [])),
        "tournaments": tours,
    }
    print(f"{name:20s} id={pid:6d} TV={data[name]['truvolley']} "
          f"lastYear={len(tours):3d} allTime={data[name]['allCount']}")
    time.sleep(0.3)

# Need full tournament objects (finishes lacks tdId); refetch via /playerprofile/{id}
for name, pid, region in PLAYERS:
    prof = req(f"/playerprofile/{pid}")
    tmap = {}
    for t in (prof or {}).get("tournaments", []):
        if CUTOFF <= t["date"][:10] <= TODAY:
            tmap[t["id"]] = t
    data[name]["full"] = tmap
    time.sleep(0.3)

# Collect all tournament ids and fetch division counts in bulk
tids = sorted({t["id"] for p in data.values() for t in p["tournaments"]})
print("unique tournaments:", len(tids))

counts = {}
B = 40
for i in range(0, len(tids), B):
    chunk = tids[i:i + B]
    res = req("/Tournament/CountsV3Bulk", {"tournamentIds": chunk})
    if res:
        counts.update(res)
    print("counts batch", i, "->", len(counts))
    time.sleep(0.4)

json.dump({"players": data, "counts": counts}, open("raw.json", "w"), indent=1)
print("saved raw.json")
