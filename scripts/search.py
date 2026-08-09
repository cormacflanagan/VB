import json, urllib.request, urllib.parse, time

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

def get(path):
    req = urllib.request.Request(API + path, headers=HDRS)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

ROSTER = [
    ("Simrin", "Adams", "Southern California Southern Nevada"),
    ("Sarah", "Albers", "Gateway"),
    ("Sienna", "Castillo", "Northern California"),
    ("Sarah", "Cowan", "Florida"),
    ("Sadie", "Harris", "Southern California Southern Nevada"),
    ("Olivia", "Herron", "North Texas"),
    ("Sage", "Illian", "Heart of America"),
    ("Lauren", "Leach", "Southern California Southern Nevada"),
    ("Georgeann", "Lee", "Aloha"),
    ("Janie", "McCanna", "Puget Sound"),
    ("Milaniakai", "Padilla", "Aloha"),
    ("Sadie", "Stafford", "Old Dominion"),
    ("Jordyn", "Wilson", "Southern California Southern Nevada"),
]

out = {}
for first, last, region in ROSTER:
    key = f"{first} {last}"
    results = []
    for q in (f"{first} {last}", last):
        try:
            res = get("/playerprofile/search/" + urllib.parse.quote(q))
        except Exception as e:
            print("ERR", q, e)
            continue
        for p in res or []:
            if p.get("male"):
                continue
            if p["lastName"].lower() != last.lower():
                continue
            if p["id"] not in [x["id"] for x in results]:
                results.append(p)
        if results and q == f"{first} {last}":
            break
    out[key] = results
    print(f"--- {key} ({region})")
    for p in results:
        print(f"    id={p['id']:6d} {p['fullName']:28s} {str(p.get('cityState')):24s} "
              f"grad={p.get('gradYear')} dob={str(p.get('dob'))[:10]} age={p.get('ageGroup')}")

json.dump(out, open("search_results.json", "w"), indent=1)
