"""Close the class-of-2028 partner graph.

The first crawl was only verified complete above the #30 rating cut-off. Widening the
report to a top 50/60 needs the population complete further down, so this expands the
partners of every known 2028 girl and repeats until a round finds nobody new above the
floor. Updates pop2028.json in place.
"""
import json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
FLOOR = 7.0          # comfortably below any plausible top-60 cut
MAX_ROUNDS = 4


def get(path):
    for a in range(4):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.5 * (a + 1))
    return None


pop = json.load(open("pop2028.json"))
pop = {int(k): v for k, v in pop.items()}
checked = set(pop)                      # ids known to be class-2028 girls
try:
    checked |= set(json.load(open("checked2028.json")))
except FileNotFoundError:
    pass

expanded = set()
for rnd in range(MAX_ROUNDS):
    frontier = [pid for pid in pop if pid not in expanded]
    if not frontier:
        break
    print(f"round {rnd}: expanding partners of {len(frontier)} known 2028 girls")
    with ThreadPoolExecutor(max_workers=8) as ex:
        profs = list(ex.map(lambda i: get(f"/playerprofile/{i}"), frontier))
    expanded |= set(frontier)

    cand = set()
    for prof in profs:
        for t in (prof or {}).get("tournaments", []):
            for q in (t.get("partners") or []):
                if q.get("id") and q["id"] not in checked:
                    cand.add(q["id"])
    print(f"  unseen partner ids: {len(cand)}")
    if not cand:
        break

    def check(pid):
        pr = get(f"/playerprofile/{pid}")
        if pr and pr.get("gradYear") == 2028 and not pr.get("male"):
            tv = get(f"/playerprofile/{pid}/truvolley") or {}
            return pid, pr, tv
        return pid, None, None

    added, above = 0, 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for pid, pr, tv in ex.map(check, list(cand)):
            checked.add(pid)
            if pr is None:
                continue
            added += 1
            pop[pid] = {
                "id": pid, "name": f'{pr.get("firstName")} {pr.get("lastName")}'.strip(),
                "grad": 2028, "height": pr.get("height"), "club": pr.get("club"),
                "city": pr.get("city"), "state": pr.get("state"),
                "tv": tv.get("truVolley"), "peak": tv.get("peak"),
                "conf": tv.get("confidence"), "w": tv.get("wins"),
                "m": tv.get("matchesPlayed"), "vision": None,
            }
            if (tv.get("truVolley") or 0) >= FLOOR:
                above += 1
    print(f"  new class-2028 girls: {added} (above {FLOOR}: {above}); population now {len(pop)}")
    json.dump({str(k): v for k, v in pop.items()}, open("pop2028.json", "w"), indent=1)
    json.dump(sorted(checked), open("checked2028.json", "w"))
    if above == 0:
        print("  converged: no new player above the floor")
        break

rated = sorted([p for p in pop.values() if p["tv"]], key=lambda p: -p["tv"])
print(f"\nfinal population {len(pop)} ({len(rated)} rated)")
for n in (30, 50, 60, 70):
    if len(rated) > n:
        print(f"  #{n} = {rated[n-1]['tv']:.3f}  {rated[n-1]['name']}")
