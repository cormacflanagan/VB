"""Re-rate every tracked population and re-draw every generated roster.

  python3 refresh_all.py            # re-rate, then re-cut all six rosters
  python3 refresh_all.py --ratings  # stop after re-rating (the slow half)
  python3 refresh_all.py --cut      # re-cut only, from the cache already on disk

`refresh_class.py` does this for one graduating class. This does it for all of them at
once, including the age-eligible cohorts, so that every report is drawn on the same
rating epoch and stays comparable with the others -- which is the whole point of running
them on one window.

The rating call is cheap and the profile call is not, so they are split: TruVolley is
re-fetched for the entire population (17k players, one request each, cached to disk as it
goes so a restart resumes), while the full profile -- height, club, city, state -- is only
re-fetched for the few hundred players who actually land in a roster. Those fields change
rarely, and roster members have their profiles re-read by collect_group.py regardless.
"""
import json, os, sys, time, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CACHE = os.path.join(DATA, "tvcache.json")
WORKERS = 12
CHUNK = 600

# population file -> the rosters cut from it. `younger` marks an age-eligible cohort,
# which carries a graduating year per player and reports its class mix.
SOURCES = [
    ("pop2027.json", [("2027", 60, "Class of 2027 — top 60")], False),
    ("pop2028.json", [("2028", 60, "Class of 2028 — top 60"),
                      ("2028_top30", 30, "Class of 2028 — top 30"),
                      ("2028_top20", 20, "Class of 2028 — top 20")], False),
    ("cohort2027.json", [("2027_younger", 60, "2027 and younger — top 60")], True),
    ("cohort2028.json", [("2028_younger", 60, "2028 and younger — top 60")], True),
]


def get(path, tries=4):
    for a in range(tries):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.4 * (a + 1))
    return None


def populations():
    return {f: {int(k): v for k, v in json.load(open(os.path.join(DATA, f))).items()}
            for f, _, _ in SOURCES}


def rate(ids):
    """Fetch TruVolley for every id, checkpointing so a long run survives a restart."""
    cache = {}
    if os.path.exists(CACHE):
        cache = {int(k): v for k, v in json.load(open(CACHE)).items()}
    todo = sorted(set(ids) - set(cache))
    print(f"{len(ids)} players; {len(cache)} cached, {len(todo)} to fetch", flush=True)
    t0 = time.time()
    for i in range(0, len(todo), CHUNK):
        part = todo[i:i + CHUNK]
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for pid, tv in zip(part, ex.map(lambda p: get(f"/playerprofile/{p}/truvolley"),
                                            part)):
                cache[pid] = {} if tv is None else {
                    "tv": tv.get("truVolley"), "peak": tv.get("peak"),
                    "conf": tv.get("confidence"), "w": tv.get("wins"),
                    "m": tv.get("matchesPlayed")}
        json.dump({str(k): v for k, v in cache.items()}, open(CACHE, "w"))
        done = min(i + CHUNK, len(todo))
        rate_s = done / max(time.time() - t0, 1e-9)
        print(f"  {done}/{len(todo)} rated ({rate_s:.0f}/s, "
              f"{(len(todo) - done) / max(rate_s, 1e-9) / 60:.0f} min left)", flush=True)
    return cache


def apply_ratings(pops, cache):
    moved = 0
    for f, pop in pops.items():
        for pid, rec in pop.items():
            new = cache.get(pid)
            if not new:
                continue
            if rec.get("tv") != new["tv"]:
                moved += 1
            rec.update(new)
        json.dump({str(k): v for k, v in pop.items()},
                  open(os.path.join(DATA, f), "w"), indent=1)
    print(f"{moved} rating rows changed across the population files")


def profiles(ids):
    out = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for pid, pr in zip(ids, ex.map(lambda p: get(f"/playerprofile/{p}"), ids)):
            if pr:
                out[pid] = {"height": pr.get("height"), "club": pr.get("club"),
                            "city": pr.get("city"), "state": pr.get("state"),
                            "grad": pr.get("gradYear")}
    return out


def cut(pops):
    """Re-draw every roster and report what moved in and out of each."""
    picks = {}
    for f, rosters, younger in SOURCES:
        rated = sorted([p for p in pops[f].values() if p["tv"]], key=lambda p: -p["tv"])
        for key, n, label in rosters:
            picks[key] = (rated[:n], rated, len(pops[f]), n, label, younger)

    wanted = sorted({p["id"] for sel, *_ in picks.values() for p in sel})
    print(f"re-reading profiles for {len(wanted)} roster members")
    prof = profiles(wanted)

    for key, (sel, rated, popn, n, label, younger) in picks.items():
        path = os.path.join(HERE, f"roster_{key}.json")
        before = [r[0] for r in json.load(open(path))["roster"]] if os.path.exists(path) else []
        for p in sel:
            p.update({k: v for k, v in prof.get(p["id"], {}).items() if v is not None})
        keys = ("height", "club", "city", "state", "tv") + (("grad",) if younger else ())
        out = {
            "label": label,
            "roster": [[p["name"], p["id"], p.get("state") or "?"] for p in sel],
            "meta": {str(p["id"]): {k: p.get(k) for k in keys} for p in sel},
            "population": popn, "rated": len(rated),
            "cut": {"nTop": sel[-1]["tv"],
                    "next": rated[n]["tv"] if len(rated) > n else None,
                    "nextName": rated[n]["name"] if len(rated) > n else None},
        }
        if younger:
            out["classes"] = dict(sorted(Counter(p["grad"] for p in sel).items()))
        json.dump(out, open(path, "w"), indent=1)

        after = [p["name"] for p in sel]
        ins = [p for p in sel if p["name"] not in before]
        outs = [nm for nm in before if nm not in after]
        print(f"\nroster_{key}.json  cut #{n} = {sel[-1]['tv']:.3f}"
              + (f", next {rated[n]['tv']:.3f} {rated[n]['name']}" if len(rated) > n else ""))
        print(f"  churn: {len(ins)} in, {len(outs)} out")
        for p in ins:
            print(f"    IN   {p['name']} ({p['tv']:.3f})")
        for nm in outs:
            print(f"    OUT  {nm}")
        if younger:
            print("  by graduating year:", out["classes"])


def main(argv):
    pops = populations()
    ids = sorted({pid for pop in pops.values() for pid in pop})
    if "--cut" not in argv:
        cache = rate(ids)
        apply_ratings(pops, cache)
        pops = populations()
    if "--ratings" in argv:
        return
    cut(pops)


if __name__ == "__main__":
    main(sys.argv[1:])
