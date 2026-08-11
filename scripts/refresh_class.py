"""Re-rate an already-closed cohort and re-draw its cut.

  python3 refresh_class.py 2028 [top]

TruVolley moves as results process, so a roster cut days ago is drawn on stale numbers.
This re-fetches the rating for every player in pop<year>.json — the cohort itself comes
from the closed crawl and is not re-discovered — then rewrites pop<year>.json and
roster_<year>.json. Reports how the cut moved so the churn is visible rather than silent.
"""
import json, sys, time, urllib.request
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
            time.sleep(0.5 * (a + 1))
    return None


def main(year, top=60):
    pop = {int(k): v for k, v in json.load(open(f"pop{year}.json")).items()}
    before = [p["name"] for p in
              sorted([q for q in pop.values() if q["tv"]], key=lambda q: -q["tv"])[:top]]
    print(f"re-rating {len(pop)} class-of-{year} girls")

    def one(pid):
        return pid, get(f"/playerprofile/{pid}/truvolley"), get(f"/playerprofile/{pid}")

    moved = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for pid, tv, pr in ex.map(one, list(pop)):
            if tv:
                old = pop[pid].get("tv")
                pop[pid].update(tv=tv.get("truVolley"), peak=tv.get("peak"),
                                conf=tv.get("confidence"), w=tv.get("wins"),
                                m=tv.get("matchesPlayed"))
                if old != pop[pid]["tv"]:
                    moved += 1
            if pr:
                pop[pid].update(height=pr.get("height"), club=pr.get("club"),
                                city=pr.get("city"), state=pr.get("state"))
    json.dump({str(k): v for k, v in pop.items()}, open(f"pop{year}.json", "w"), indent=1)

    rated = sorted([p for p in pop.values() if p["tv"]], key=lambda p: -p["tv"])
    sel = rated[:top]
    after = [p["name"] for p in sel]
    json.dump({"label": f"Class of {year} — top {top}",
               "roster": [[p["name"], p["id"], p["state"] or "?"] for p in sel],
               "meta": {p["id"]: {"height": p["height"], "club": p["club"], "city": p["city"],
                                  "state": p["state"], "tv": p["tv"]} for p in sel},
               "population": len(pop), "rated": len(rated),
               "cut": {"nTop": sel[-1]["tv"],
                       "next": rated[top]["tv"] if len(rated) > top else None,
                       "nextName": rated[top]["name"] if len(rated) > top else None}},
              open(f"roster_{year}.json", "w"), indent=1)

    ins, outs = [n for n in after if n not in before], [n for n in before if n not in after]
    print(f"  {moved} ratings changed; cohort {len(pop)} ({len(rated)} rated)")
    print(f"  cut #{top} = {sel[-1]['tv']:.3f}"
          + (f", #{top+1} = {rated[top]['tv']:.3f} {rated[top]['name']}" if len(rated) > top else ""))
    print(f"  roster churn: {len(ins)} in, {len(outs)} out")
    for n in ins:
        print(f"    IN   {n} ({[p['tv'] for p in sel if p['name'] == n][0]:.3f})")
    for n in outs:
        print(f"    OUT  {n}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 60)
