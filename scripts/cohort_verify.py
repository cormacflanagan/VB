"""Close the top of a cohort: expand everyone above the rating floor, one more time.

  python3 scripts/cohort_verify.py 2026

close_cohort.py converges when a round turns up nobody new above the floor. If a run dies
mid-round and is resumed, its expansion frontier can come back empty while the candidates
that round had already gathered were never checked -- which is how the 2026 crawl ended.
That leaves the tail unproven.

This re-expands every rated member at or above the floor, ignoring the expansion
checkpoint, and checks every partner not already seen. It is the test that matters for a
top-60 cut: a girl good enough to make it has to have partnered with somebody at that
level, so if re-walking all of their partner lists turns up nobody new above the floor, the
top of the cohort is closed whatever is still unexplored in the tail.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from close_cohort import DATA, FLOOR, WORKERS, get, profile


def main(year):
    pop = {int(k): v for k, v in json.load(open(f"{DATA}/cohort{year}.json")).items()}
    checked = set(json.load(open(f"{DATA}/cohortchecked{year}.json"))) | set(pop)
    strong = sorted(p["id"] for p in pop.values() if (p.get("tv") or 0) >= FLOOR)
    print(f"cohort {len(pop)}, {len(checked)} checked; re-expanding "
          f"{len(strong)} members rated >= {FLOOR}", flush=True)

    cand, t0 = set(), time.time()
    for i in range(0, len(strong), 200):
        part = strong[i:i + 200]
        with ThreadPoolExecutor(WORKERS) as ex:
            profs = list(ex.map(lambda p: get(f"/playerprofile/{p}"), part))
        cand |= {q["id"] for pr in profs for t in (pr or {}).get("tournaments", [])
                 for q in (t.get("partners") or [])
                 if q.get("id") and q["id"] not in checked}
        print(f"  expanded {min(i + 200, len(strong))}/{len(strong)}, "
              f"{len(cand)} unseen partners ({time.time() - t0:.0f}s)", flush=True)

    print(f"checking {len(cand)} ids never seen by the crawl", flush=True)
    added = above = 0
    best = []
    with ThreadPoolExecutor(WORKERS) as ex:
        for pid, rec in ex.map(lambda p: profile(p, year), sorted(cand)):
            checked.add(pid)
            if rec is None:
                continue
            pop[pid] = rec
            added += 1
            if (rec["tv"] or 0) >= FLOOR:
                above += 1
                best.append(rec)

    json.dump({str(k): v for k, v in pop.items()},
              open(f"{DATA}/cohort{year}.json", "w"), indent=1)
    json.dump(sorted(checked), open(f"{DATA}/cohortchecked{year}.json", "w"))

    rated = sorted([p for p in pop.values() if p["tv"]], key=lambda p: -p["tv"])
    cut = rated[59]["tv"] if len(rated) > 59 else None
    print(f"\nadmitted {added}; {above} above {FLOOR}; cohort now {len(pop)}")
    for r in sorted(best, key=lambda p: -(p["tv"] or 0))[:10]:
        print(f"    {r['tv']:.3f}  {r['name']} ({r['grad']})"
              + ("   << inside the top 60" if cut and r["tv"] >= cut else ""))
    inside = sum(1 for r in best if cut and (r["tv"] or 0) >= cut)
    print(f"\n{'TOP CLOSED' if not inside else 'NOT CLOSED'}: {inside} of the new admissions "
          f"reach the #60 cut of {cut:.3f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2026)
