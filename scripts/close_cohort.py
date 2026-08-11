"""Close an *age-eligible* cohort: python3 close_cohort.py 2027

A graduating-class group answers "who else is in her year". A bracket does not work that
way — an 18U field is grad 2027 *and younger*, so the girls a 2027 player actually meets
include every strong 2028, 2029 and 2030 playing up. This crawls to closure on the
predicate `gradYear >= year` rather than `== year`, and writes cohort<year>.json.

It starts from the class populations already closed (pop2027, pop2028, …) and from the
candidates those crawls *rejected*: a rejected id is one that partnered with a girl in
the class and failed the equality test, which is exactly the pool the inequality admits.
That makes round 0 a re-check rather than a re-expansion, saving several thousand fetches.

  python3 scripts/close_cohort.py 2027   ->  data/cohort2027.json
"""
import glob, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
DATA = os.path.join(os.path.dirname(__file__) or ".", "..", "data")
FLOOR = 7.0        # comfortably below any plausible top-60 cut
MAX_ROUNDS = 8
WORKERS = 10
CHUNK = 400        # expansion checkpoint size


def get(path):
    for a in range(4):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.5 * (a + 1))
    return None


def known_classes():
    """Every class population already closed, keyed by graduating year."""
    out = {}
    for p in sorted(glob.glob(os.path.join(DATA, "pop*.json"))):
        m = re.search(r"pop(\d{4})\.json$", p)
        if m:
            out[int(m.group(1))] = {int(k): v for k, v in json.load(open(p)).items()}
    return out


def rejected_pool():
    """Ids checked by an earlier class crawl and turned away for being the wrong year."""
    checked, known = set(), set()
    for p in glob.glob(os.path.join(DATA, "checked*.json")):
        checked |= set(json.load(open(p)))
    for pop in known_classes().values():
        known |= set(pop)
    return checked - known


def profile(pid, year):
    pr = get(f"/playerprofile/{pid}")
    if not pr or pr.get("male") or (pr.get("gradYear") or 0) < year:
        return pid, None
    tv = get(f"/playerprofile/{pid}/truvolley") or {}
    return pid, {
        "id": pid, "name": f'{pr.get("firstName")} {pr.get("lastName")}'.strip(),
        "grad": pr.get("gradYear"), "height": pr.get("height"), "club": pr.get("club"),
        "city": pr.get("city"), "state": pr.get("state"),
        "tv": tv.get("truVolley"), "peak": tv.get("peak"), "conf": tv.get("confidence"),
        "w": tv.get("wins"), "m": tv.get("matchesPlayed"),
    }


def main(year):
    classes = known_classes()
    pop = {}
    for y, members in classes.items():
        if y >= year:
            pop.update(members)
    checked = set(pop)
    print(f"seed: {len(pop)} girls from classes {sorted(y for y in classes if y >= year)}")

    # a crawl this long will not always survive the machine it runs on, so pick up any
    # partial cohort left behind rather than paying for the early rounds twice
    resumed, expanded = False, set(pop)
    try:
        prior = {int(k): v for k, v in
                 json.load(open(f"{DATA}/cohort{year}.json")).items()}
        if len(prior) > len(pop):
            pop, resumed = prior, True
            checked = set(pop) | set(json.load(open(f"{DATA}/cohortchecked{year}.json")))
            try:
                expanded = set(json.load(open(f"{DATA}/cohortexpanded{year}.json")))
            except FileNotFoundError:
                expanded = set()
            print(f"resuming: {len(pop)} admitted, {len(checked)} checked, "
                  f"{len(expanded)} already expanded")
    except FileNotFoundError:
        pass

    def expand(frontier):
        """Fetch partners in chunks, checkpointing as we go: a long round has to survive
        the machine restarting under it, or the crawl never finishes at all."""
        out = set()
        for i in range(0, len(frontier), CHUNK):
            part = frontier[i:i + CHUNK]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                profs = list(ex.map(lambda p: get(f"/playerprofile/{p}"), part))
            out |= {q["id"] for pr in profs for t in (pr or {}).get("tournaments", [])
                    for q in (t.get("partners") or [])
                    if q.get("id") and q["id"] not in checked}
            expanded.update(part)
            json.dump(sorted(expanded), open(f"{DATA}/cohortexpanded{year}.json", "w"))
            print(f"    expanded {min(i + CHUNK, len(frontier))}/{len(frontier)}, "
                  f"{len(out)} candidates so far", flush=True)
        return out

    # round 0 is a re-check of what the class crawls threw away, not a fresh expansion
    cand = rejected_pool() - checked
    for rnd in range(MAX_ROUNDS):
        if rnd or resumed:
            frontier = [p for p in pop if p not in expanded]
            if not frontier:
                print("converged: nobody left to expand")
                break
            print(f"round {rnd}: expanding partners of {len(frontier)} new girls")
            cand = expand(frontier)
        else:
            print(f"round 0: re-checking {len(cand)} ids the class crawls rejected")
        if not cand:
            print("converged: no unseen partners")
            break

        added = above = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for pid, rec in ex.map(lambda p: profile(p, year), sorted(cand)):
                checked.add(pid)
                if rec is None:
                    continue
                pop[pid] = rec
                added += 1
                if (rec["tv"] or 0) >= FLOOR:
                    above += 1
        print(f"  admitted {added} (above {FLOOR}: {above}); cohort now {len(pop)}")
        json.dump({str(k): v for k, v in pop.items()},
                  open(f"{DATA}/cohort{year}.json", "w"), indent=1)
        json.dump(sorted(checked), open(f"{DATA}/cohortchecked{year}.json", "w"))
        if above == 0:
            print("  converged: no new player above the floor")
            break
    else:
        print(f"WARNING: stopped on the {MAX_ROUNDS}-round cap. The cohort is NOT closed.")

    rated = sorted([p for p in pop.values() if p["tv"]], key=lambda p: -p["tv"])
    print(f"\nfinal cohort {len(pop)} ({len(rated)} rated)")
    from collections import Counter
    print("  by class:", dict(sorted(Counter(p["grad"] for p in rated[:60]).items())),
          "in the top 60")
    for n in (15, 30, 60):
        if len(rated) > n:
            print(f"  #{n} = {rated[n-1]['tv']:.3f}  {rated[n-1]['name']} "
                  f"({rated[n-1]['grad']})")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2028)
