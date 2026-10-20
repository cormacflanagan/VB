"""Re-rate a closed age-eligible cohort, and show how the cut moved.

  python3 scripts/cohort_refresh.py 2027 [top] [--floor 5.5] [--workers 24]

TruVolley moves as results process, so a cut drawn days ago rests on stale numbers. This
re-fetches the rating and the profile for every player in data/cohort<year>.json -- the
cohort membership itself comes from the closed crawl and is not re-discovered -- rewrites
that file, and reports the churn rather than leaving it silent. Draw the roster afterwards
with cohort_roster.py, which reads the file this rewrites.

The cohort is large -- seventeen thousand for 2027 -- and the API answers in a couple of
seconds, so re-rating all of it takes hours. `--floor` re-rates only the players who could
plausibly reach the cut, which is what the cut actually depends on. The floor is not a
guess: across the 695 players held in two snapshots six days apart, the largest move in
either direction was 1.77 and the 99th percentile was 0.98, and exactly one player went
from unrated to rated, at 3.4. A floor three points below the standing cut therefore has
more than a point of margin on the worst move ever observed, and unrated players cannot
arrive anywhere near it. Everything below the floor keeps its previous rating, so the file
stays whole; the cut is still drawn over the entire rated cohort.

It checkpoints every thousand players and can be re-run to finish an interrupted pass.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")  # the API 404s a short UA
HDRS = {"User-Agent": UA, "Accept": "application/json"}
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def get(path):
    for a in range(4):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.5 * (a + 1))
    return None


def one(pid):
    return pid, get(f"/playerprofile/{pid}/truvolley"), get(f"/playerprofile/{pid}")


def top_of(pop, n):
    rated = sorted((p for p in pop.values() if p.get("tv")), key=lambda p: -p["tv"])
    return rated, rated[:n]


def main(year, n=60, floor=None, workers=24):
    path = os.path.join(DATA, f"cohort{year}.json")
    pop = {int(k): v for k, v in json.load(open(path)).items()}
    _, before = top_of(pop, n)
    names_before = {p["name"] for p in before}
    ids = [i for i in pop
           if floor is None or (pop[i].get("tv") or 0) >= floor]
    print(f"cohort {year}: {len(pop):,} players, re-rating {len(ids):,}"
          + (f" at or above {floor}" if floor is not None else "")
          + f" (cut #{n} stands at {before[-1]['tv']:.3f})", flush=True)

    moved = seen = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for pid, tv, pr in ex.map(one, ids):
            seen += 1
            if tv:
                old = pop[pid].get("tv")
                pop[pid].update(tv=tv.get("truVolley"), peak=tv.get("peak"),
                                conf=tv.get("confidence"), w=tv.get("wins"),
                                m=tv.get("matchesPlayed"))
                moved += old != pop[pid]["tv"]
            if pr:
                pop[pid].update(height=pr.get("height"), club=pr.get("club"),
                                city=pr.get("city"), state=pr.get("state"),
                                grad=pr.get("gradYear") or pop[pid].get("grad"))
            if seen % 1000 == 0:
                json.dump({str(k): v for k, v in pop.items()}, open(path, "w"), indent=1)
                rate = seen / max(time.time() - t0, 1)
                print(f"  {seen:,}/{len(ids):,} · {moved:,} moved · "
                      f"{(len(ids) - seen) / rate / 60:.0f} min left", flush=True)
    json.dump({str(k): v for k, v in pop.items()}, open(path, "w"), indent=1)

    rated, after = top_of(pop, n)
    names_after = {p["name"] for p in after}
    print(f"\n{moved:,} of {len(pop):,} ratings changed; {len(rated):,} rated")
    print(f"cut #{n} = {after[-1]['tv']:.3f}"
          + (f", #{n + 1} = {rated[n]['tv']:.3f} {rated[n]['name']}"
             if len(rated) > n else ""))
    ins = [p for p in after if p["name"] not in names_before]
    outs = [p for p in before if p["name"] not in names_after]
    print(f"churn: {len(ins)} in, {len(outs)} out")
    for p in ins:
        print(f"  IN   {p['name']:26} {p['tv']:.3f}")
    for p in outs:
        now = pop[p["id"]].get("tv")
        print(f"  OUT  {p['name']:26} {p['tv']:.3f} -> "
              + (f"{now:.3f}" if now else "unrated"))


def arg(flag, cast, default):
    return cast(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default


if __name__ == "__main__":
    pos = [a for a in sys.argv[1:] if not a.startswith("--")
           and not (sys.argv.index(a) and sys.argv[sys.argv.index(a) - 1].startswith("--"))]
    main(int(pos[0]), int(pos[1]) if len(pos) > 1 else 60,
         arg("--floor", float, None), arg("--workers", int, 24))
