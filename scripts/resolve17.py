import json, urllib.request, urllib.parse, time

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def get(path):
    r = urllib.request.Request(API + path, headers=HDRS)
    for a in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if a == 4:
                print("FAIL", path, e); return None
            time.sleep(2 ** a)


ROSTER = [
    ("Regina Stella", "Broshear", "Northern California"),
    ("Ella", "Buchanan", "So. Cal / So. Nevada"),
    ("Reagan", "Carlin", "So. Cal / So. Nevada"),
    ("Sienna", "Cicero", "So. Cal / So. Nevada"),
    ("Cayden", "Dorger", "Gulf Coast"),
    ("Haisley", "Flanagan", "Northern California"),
    ("Madison", "Gillinger", "So. Cal / So. Nevada"),
    ("Julianna", "Godbey", "North Texas"),
    ("Taylie", "Hansen", "Florida"),
    ("Emerson", "Harper", "So. Cal / So. Nevada"),
    ("Charlotte", "Jansen", "So. Cal / So. Nevada"),
    ("Nariah", "Johnson", "So. Cal / So. Nevada"),
    ("Olivia", "Ledoyen", "So. Cal / So. Nevada"),
    ("Lucy", "Matuszak", "So. Cal / So. Nevada"),
    ("Brooke", "Proctor", "So. Cal / So. Nevada"),
    ("Milana", "Rivera", "Lone Star"),
    ("Ashley", "Ruschill", "North Texas"),
    ("Elyse", "Smelcer", "Carolina"),
    ("Elle", "Sossong", "Keystone"),
    ("Ella", "Whiteside", "North Texas"),
]

out = {}
for first, last, region in ROSTER:
    cands = []
    for q in (f"{first} {last}", last):
        res = get("/playerprofile/search/" + urllib.parse.quote(q)) or []
        for p in res:
            if p.get("male") or p["lastName"].lower() != last.lower():
                continue
            if p["id"] not in [c["id"] for c in cands]:
                cands.append(p)
        if any(c["fullName"].lower() == f"{first} {last}".lower() for c in cands):
            break
    exact = [c for c in cands if c["fullName"].lower() == f"{first} {last}".lower()]
    pool = exact or cands
    print(f"--- {first} {last} ({region}) : {len(cands)} candidates, {len(exact)} exact")
    for c in pool[:8]:
        n = get(f"/playerprofile/{c['id']}/finishes") or {}
        c["_n"] = len(n.get("tournaments") or [])
        c["_club"] = n.get("club")
        print(f"    id={c['id']:7d} {c['fullName']:24s} {str(c.get('cityState')):26s} "
              f"grad={c.get('gradYear')} dob={str(c.get('dob'))[:10]} tourneys={c['_n']} club={c['_club']}")
        time.sleep(0.15)
    out[f"{first} {last}"] = {"region": region, "cands": pool}

json.dump(out, open("resolve17.json", "w"), indent=1)
