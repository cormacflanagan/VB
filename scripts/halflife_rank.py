"""Where one player ranks as the rating's memory is shortened.

  python3 scripts/halflife_rank.py <id-or-name> [more ids...]

The fit weights a result by 0.5 ** (age / halflife_days), and 365 days was chosen because
it predicts held-out matches best *for the population*. For an individual that choice is
not neutral. A player whose level a year ago is the same as today is unaffected by it; a
player who has improved sharply is averaged with a version of herself that no longer
exists, and ranks below where she is now.

That is a specific, checkable claim rather than an excuse. Refit at a range of half-lives
and watch the player's rank. A rank that barely moves says the rating disagrees with
TruVolley about her for some other reason. A rank that climbs steeply as the memory
shortens says the disagreement is about *when* her results happened, and roughly locates
the point at which the two ratings would agree.

Each half-life is a full refit, so this takes a few minutes.
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "halflife_rank.json")
HALFLIVES = [90, 120, 180, 240, 365, 550, 730, None]
MIN_OBS = 4


def cohort():
    pop = {int(k): v for k, v in json.load(open(os.path.join(DATA, "cohort2027.json"))).items()}
    al = json.load(open(os.path.join(DATA, "aliases.json")))["alias"]
    for p in al:
        pop.pop(int(p), None)
    return pop


def resolve(q, pop):
    if q.isdigit():
        return int(q)
    hit = [p for p, v in pop.items() if q.lower() in (v.get("name") or "").lower()]
    if len(hit) != 1:
        sys.exit(f"{q!r} matches {len(hit)} cohort players")
    return hit[0]


def main(argv):
    if not argv:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    pop = cohort()
    who = [resolve(q, pop) for q in argv]
    base = rate.conf([])

    tvsort = sorted(((v.get("tv") or 0, p) for p, v in pop.items() if v.get("tv")),
                    reverse=True)
    tvrank = {p: i for i, (_, p) in enumerate(tvsort, 1)}

    print(f"\ncohort of {len(pop):,}; TruVolley rank shown for reference\n")
    head = "".join(f"{pop[p]['name'].split()[-1][:11]:>12}" for p in who)
    print(f"  {'HALF-LIFE':>10}{head}")
    print(f"  {'TruVolley':>10}" + "".join(f"{tvrank.get(p, 0):>12}" for p in who))
    rows = {}
    for hl in HALFLIVES:
        c = dict(base, halflife_days=hl or 0)
        t0 = time.time()
        ids, ix, d = rate.load(c, quiet=True)
        r = rate.fit(len(ids), d, c, mask=np.ones(len(d["y"]), bool), quiet=True)
        nm = rate.counts(ids, d)
        pool = [(r[i], p) for i, p in enumerate(ids) if p in pop and nm[i] >= MIN_OBS]
        pool.sort(reverse=True)
        rk = {p: i for i, (_, p) in enumerate(pool, 1)}
        rows[hl or "none"] = {str(p): rk.get(p) for p in who}
        lab = f"{hl}d" if hl else "no decay"
        print(f"  {lab:>10}" + "".join(f"{rk.get(p, 0):>12}" for p in who)
              + f"   ({time.time() - t0:.0f}s)")

    json.dump({"halflives": [h or 0 for h in HALFLIVES],
               "tv": {str(p): tvrank.get(p) for p in who},
               "ranks": rows,
               "names": {str(p): pop[p]["name"] for p in who}},
              open(OUT, "w"), indent=1)
    print(f"\nwrote {os.path.relpath(OUT)}")
    print("\nA rank that climbs as the half-life shortens is a player whose recent results\n"
          "are better than her older ones. The population holdout still prefers 365 days,\n"
          "so a short half-life is not a better rating -- it is a rating that reads a fast\n"
          "improver correctly and everyone else slightly worse.")


if __name__ == "__main__":
    main(sys.argv[1:])
