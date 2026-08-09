"""Discover the competitive class-of-2028 girls population on Volleyball Life.

Two independent sources, merged:
  1. /vision/players  - the opt-in recruiting directory (height, side, block touch)
  2. a partner-graph crawl from known 2028 athletes - catches everyone who competes,
     whether or not they keep a Vision profile

Writes pop2028.json: {id: {name, grad, height, club, state, tv, peak, w, m, vision}}
"""
import json, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def get(path):
    for a in range(4):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.6 * (a + 1))
    return None


# ---------- 1. Vision directory ----------
vision = {}
page = 1
while True:
    d = get(f"/vision/players?page={page}&pageSize=100")
    if not d or not d.get("items"):
        break
    for it in d["items"]:
        vision[it["id"]] = it
    if page * 100 >= d.get("total", 0):
        break
    page += 1
    time.sleep(0.2)
print(f"vision directory: {len(vision)} players")
v28 = [v for v in vision.values() if v.get("gradYear") == 2028 and not v.get("male")]
print(f"  class of 2028 girls in Vision: {len(v28)}")
json.dump(vision, open("vision_all.json", "w"), indent=1)

# ---------- 2. partner-graph crawl ----------
SEEDS = {  # known 2028 girls from the two NTDP rosters
    84161: "Sarah Albers", 84725: "Sarah Cowan", 94909: "Sadie Harris",
    91052: "Sage Illian", 95165: "Milaniakai Padilla", 147394: "Sadie Stafford",
    64782: "Regina Stella Broshear", 98125: "Ella Buchanan", 128445: "Cayden Dorger",
    64896: "Haisley Flanagan", 99596: "Madison Gillinger", 99506: "Taylie Hansen",
    161398: "Charlotte Jansen", 22544: "Lucy Matuszak", 77570: "Elyse Smelcer",
    33084: "Elle Sossong",
}
SEEDS.update({v["id"]: f'{v["firstName"]} {v["lastName"]}' for v in v28})

profiles = {}


def fetch_profile(pid):
    if pid in profiles:
        return profiles[pid]
    p = get(f"/playerprofile/{pid}")
    profiles[pid] = p
    return p


def partners_of(prof):
    out = set()
    for t in (prof or {}).get("tournaments", []):
        for q in (t.get("partners") or []):
            if q.get("id"):
                out.add(q["id"])
    return out


frontier = set(SEEDS)
seen = set()
found = {}
for depth in range(3):
    frontier -= seen
    if not frontier:
        break
    print(f"depth {depth}: fetching {len(frontier)} profiles")
    with ThreadPoolExecutor(max_workers=8) as ex:
        got = list(ex.map(fetch_profile, list(frontier)))
    seen |= frontier
    nxt = set()
    for pid, prof in zip(list(frontier), got):
        if not prof:
            continue
        if prof.get("gradYear") == 2028 and not prof.get("male"):
            found[pid] = prof
            if depth < 2:
                nxt |= partners_of(prof)
    print(f"  running total class-2028 girls: {len(found)}")
    frontier = nxt

# ---------- 3. ratings ----------
def fetch_tv(pid):
    return pid, get(f"/playerprofile/{pid}/truvolley")


print(f"fetching ratings for {len(found)}")
with ThreadPoolExecutor(max_workers=8) as ex:
    ratings = dict(ex.map(fetch_tv, list(found)))

pop = {}
for pid, prof in found.items():
    tv = ratings.get(pid) or {}
    vis = vision.get(pid, {})
    pop[pid] = {
        "id": pid, "name": f'{prof.get("firstName")} {prof.get("lastName")}'.strip(),
        "grad": prof.get("gradYear"), "height": prof.get("height"),
        "club": prof.get("club"), "city": prof.get("city"), "state": prof.get("state"),
        "tv": tv.get("truVolley"), "peak": tv.get("peak"), "conf": tv.get("confidence"),
        "w": tv.get("wins"), "m": tv.get("matchesPlayed"),
        "vision": {"side": (vis.get("metrics") or {}).get("side"),
                   "blockTouch": (vis.get("metrics") or {}).get("blockTouch"),
                   "reach": (vis.get("metrics") or {}).get("reach"),
                   "position": (vis.get("metrics") or {}).get("primaryPosition")} if vis else None,
    }
json.dump(pop, open("pop2028.json", "w"), indent=1)
rated = [p for p in pop.values() if p["tv"]]
rated.sort(key=lambda p: -p["tv"])
print(f"\nclass-of-2028 girls found: {len(pop)} ({len(rated)} rated)")
print(f"{'#':>3} {'NAME':26s}{'TV':>7}{'HT':>7} {'ST':>3}  CLUB")
for i, p in enumerate(rated[:45], 1):
    print(f"{i:3d} {p['name'][:26]:26s}{p['tv']:>7.3f}{str(p['height']):>7} {str(p['state']):>3}  {str(p['club'])[:30]}")
