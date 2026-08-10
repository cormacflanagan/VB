"""Discover a graduating class of girls on Volleyball Life, then rank it.

  python3 discover_class.py 2027 [top]

Volleyball Life publishes no class ranking, so the cohort is built by crawling the
partner graph outward from a handful of known athletes in that class, keeping every
profile that reports the matching gradYear, and repeating until a full round turns up
nobody new above a rating floor. Writes pop<year>.json (the whole cohort) and
roster_<year>.json (the top N, the roster the report is built from).
"""
import json, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
FLOOR = 7.0
MAX_ROUNDS = 6

SEEDS = {
    2027: {
        # NTDP 18U roster, class of 2027
        25289: "Simrin Adams", 29854: "Sienna Castillo", 28688: "Olivia Herron",
        8426: "Lauren Leach", 61785: "Georgeann Lee", 24515: "Janie McCanna",
        23868: "Jordyn Wilson",
        # NTDP U19/U20 and frequent national partners, class of 2027
        2420: "Christy Boulware", 4517: "Ella Dueck", 150474: "Elle Gemberling",
        26871: "Abby King", 44267: "Thalia Lindahl", 25288: "Zoe Znider",
        56789: "Leah Blair", 3113: "Ella Olson", 2771: "Sandie Souza",
        40933: "Allyn Hilt", 92803: "Linnaea Nielsen", 53164: "Sammy Nammack",
        63770: "Marley Robinson",
    },
    2028: {
        84161: "Sarah Albers", 84725: "Sarah Cowan", 94909: "Sadie Harris",
        91052: "Sage Illian", 95165: "Milaniakai Padilla", 147394: "Sadie Stafford",
        64782: "Regina Stella Broshear", 98125: "Ella Buchanan", 128445: "Cayden Dorger",
        64896: "Haisley Flanagan", 99596: "Madison Gillinger", 99506: "Taylie Hansen",
        161398: "Charlotte Jansen", 22544: "Lucy Matuszak", 77570: "Elyse Smelcer",
        33084: "Elle Sossong",
    },
}


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
    pop, checked, expanded = {}, set(), set()
    frontier = set(SEEDS[year])
    converged = False

    for rnd in range(MAX_ROUNDS):
        frontier -= checked
        if frontier:
            print(f"round {rnd}: checking {len(frontier)} candidates")
            with ThreadPoolExecutor(max_workers=8) as ex:
                profs = list(ex.map(lambda i: get(f"/playerprofile/{i}"), list(frontier)))
            added = 0
            for pid, pr in zip(list(frontier), profs):
                checked.add(pid)
                if pr and pr.get("gradYear") == year and not pr.get("male"):
                    pop[pid] = pr
                    added += 1
            print(f"  +{added} class-of-{year} girls; cohort {len(pop)}")
            if added == 0:
                converged = True
                break

        todo = [i for i in pop if i not in expanded]
        if not todo:
            break
        with ThreadPoolExecutor(max_workers=8) as ex:
            profs = list(ex.map(lambda i: get(f"/playerprofile/{i}"), todo))
        expanded |= set(todo)
        nxt = set()
        for pr in profs:
            for t in (pr or {}).get("tournaments", []):
                for q in (t.get("partners") or []):
                    if q.get("id") and q["id"] not in checked:
                        nxt.add(q["id"])
        print(f"  {len(nxt)} unseen partner ids queued")
        if not nxt:
            converged = True
            break
        frontier = nxt

    if not converged:
        print(f"WARNING: stopped on the {MAX_ROUNDS}-round cap with {len(frontier)} candidates "
              f"unchecked. The cohort is NOT closed - run close_class.py {year} before "
              f"treating the cut-off as settled.")

    print(f"fetching ratings for {len(pop)}")
    with ThreadPoolExecutor(max_workers=8) as ex:
        ratings = dict(ex.map(lambda i: (i, get(f"/playerprofile/{i}/truvolley")), list(pop)))

    out = {}
    for pid, pr in pop.items():
        tv = ratings.get(pid) or {}
        out[pid] = {"id": pid, "name": f'{pr.get("firstName")} {pr.get("lastName")}'.strip(),
                    "grad": year, "height": pr.get("height"), "club": pr.get("club"),
                    "city": pr.get("city"), "state": pr.get("state"),
                    "tv": tv.get("truVolley"), "peak": tv.get("peak"),
                    "conf": tv.get("confidence"), "w": tv.get("wins"),
                    "m": tv.get("matchesPlayed")}
    json.dump({str(k): v for k, v in out.items()}, open(f"pop{year}.json", "w"), indent=1)

    rated = sorted([p for p in out.values() if p["tv"]], key=lambda p: -p["tv"])
    sel = rated[:top]
    json.dump({"label": f"Class of {year} — top {top}",
               "roster": [[p["name"], p["id"], p["state"] or "?"] for p in sel],
               "meta": {p["id"]: {"height": p["height"], "club": p["club"],
                                  "city": p["city"], "state": p["state"], "tv": p["tv"]}
                        for p in sel},
               "population": len(out), "rated": len(rated),
               "cut": {"nTop": sel[-1]["tv"], "next": rated[top]["tv"] if len(rated) > top else None,
                       "nextName": rated[top]["name"] if len(rated) > top else None}},
              open(f"roster_{year}.json", "w"), indent=1)
    print(f"\ncohort {len(out)} ({len(rated)} rated); #{top} = {sel[-1]['tv']:.3f}"
          + (f", #{top+1} = {rated[top]['tv']:.3f} {rated[top]['name']}" if len(rated) > top else ""))
    for i, p in enumerate(sel[:20], 1):
        print(f"{i:3d} {p['name'][:26]:26s}{p['tv']:>7.3f}{str(p['height']):>7} {str(p['state']):>3}  {str(p['club'])[:28]}")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 60)
