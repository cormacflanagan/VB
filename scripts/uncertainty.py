"""How much of each rating is actually pinned down by results.

  python3 scripts/uncertainty.py [--reps 40]   ->  data/rating_se.json

scripts/rate.py returns a maximum-likelihood point estimate and nothing else, which is
fine for prediction and misleading for ranking. The two uses differ because the estimate
carries no notion of how much evidence produced it, and in this corpus the amount varies
enormously between players who look equally busy.

Two things starve a rating of evidence, and neither is fixed by playing more matches:

  Lopsided matches say almost nothing. A logistic model learns from an outcome in
  proportion to p(1-p), so a match you win 96% of the time carries a twentieth of the
  information of a coin-flip. A player who is 100-14 against fields she towers over has a
  long record and a badly determined rating: everything from 7.5 upward fits her results
  about equally well, and where she lands inside that range is decided by the ridge, not
  by anything she did.

  A steady partner hides the split. `strength(team) = mean(r1, r2)` determines the pair
  well and the halves poorly. Two players who appear almost exclusively together are one
  observation wearing two names; the model has to divide their joint strength between
  them, and if one of them also plays elsewhere, she gets pinned down and the other
  absorbs whatever is left over.

Both are properties of the *shape* of a schedule rather than its length, so no threshold
on match count detects either. What does detect them is refitting the whole model on
resampled evidence and watching which ratings move. A rating held in place by
well-matched opponents and varied partners barely shifts; one resting on lopsided results
with a single partner swings by more than a point.

Resampling is by tournament-division, not by match. Six pool results out of one draw
share a venue, a day, a bracket and an opponent pool, so treating them as six independent
draws would understate every interval here by roughly the square root of the pool size.
Each division gets an Exp(1) weight, normalised to mean 1, and the model is refit from
scratch -- a Bayesian bootstrap, which needs no reindexing and leaves every observation in
place with a smoothly varying weight.

The output carries `raw` (the point estimate), `se`, and `lo = raw - se` on the fitted
scale, plus each one mapped through the same quantile map that scripts/rate.py publishes,
so `lo` is directly comparable to a TruVolley number. Ranking on `lo` asks a different
question from ranking on `raw`: not "how good might she be" but "how good do the results
oblige us to say she is".
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "rating_se.json")
REPS = 40


def quantile_map(path=os.path.join(DATA, "rating.json")):
    """Rebuild rate.py's published rating -> TruVolley map, so both live on one scale."""
    m = json.load(open(path))["map"]
    kx, ky = np.array(m["x"], float), np.array(m["y"], float)
    if len(kx) < 2:
        return lambda v: np.asarray(v, float)
    lo_s = (ky[20] - ky[0]) / max(kx[20] - kx[0], 1e-9)
    hi_s = (ky[-1] - ky[-21]) / max(kx[-1] - kx[-21], 1e-9)

    def to_tv(v):
        v = np.asarray(v, float)
        out = np.interp(v, kx, ky)
        out = np.where(v < kx[0], ky[0] + (v - kx[0]) * lo_s, out)
        out = np.where(v > kx[-1], ky[-1] + (v - kx[-1]) * hi_s, out)
        return out

    return to_tv


def information(r, d, c):
    """Per-player weighted Fisher information, sum_k w_k p_k(1-p_k) (dz/dr)^2.

    Not used for the intervals -- it ignores the correlation between a player and her
    regular partner, which is half the problem. It is reported because it separates the
    two causes cleanly: a low count of *effective* observations against a high count of
    actual ones is the lopsided-schedule case specifically.
    """
    a1, a2, b1, b2 = d["a1"], d["a2"], d["b1"], d["b2"]
    z = (rate.team(r, a1, a2, c["pair_alpha"]) - rate.team(r, b1, b2, c["pair_alpha"])) / c["scale"]
    p = 1.0 / (1.0 + np.exp(-z))
    v = d["w"] * p * (1 - p)
    info = np.zeros(len(r))
    for k in ("a1", "a2", "b1", "b2"):
        np.add.at(info, d[k], v)
    return info * 0.25 / c["scale"] ** 2


def main(argv):
    reps = int(argv[argv.index("--reps") + 1]) if "--reps" in argv else REPS
    c = rate.conf(argv)
    ids, ix, d = rate.load(c)
    n = len(ids)
    everything = np.ones(len(d["y"]), bool)

    print(f"\n  point estimate")
    t0 = time.time()
    r0 = rate.fit(n, d, c, mask=everything, quiet=True)
    print(f"    {time.time() - t0:.0f}s")

    # dense cluster index, so a replicate is one draw per division rather than per row
    cl = d["cluster"]
    uniq, cidx = np.unique(cl, return_inverse=True)
    print(f"  {len(uniq)} tournament-divisions across {len(cl)} observations "
          f"(median {np.median(np.bincount(cidx)):.0f} observations each)")

    base_w = d["w"].copy()
    rng = np.random.default_rng(20260825)
    acc = np.zeros(n)
    acc2 = np.zeros(n)
    for b in range(reps):
        gw = rng.exponential(1.0, size=len(uniq))
        gw /= gw.mean()
        d["w"] = base_w * gw[cidx]
        t0 = time.time()
        rb = rate.fit(n, d, c, mask=everything, quiet=True)
        acc += rb
        acc2 += rb * rb
        print(f"    replicate {b + 1:>3}/{reps}  {time.time() - t0:.0f}s", flush=True)
    d["w"] = base_w

    mean = acc / reps
    var = np.maximum(acc2 / reps - mean * mean, 0.0) * reps / max(reps - 1, 1)
    se = np.sqrt(var)

    nm = rate.counts(ids, d)
    info = information(r0, d, c)
    to_tv = quantile_map()
    lo = r0 - se
    r_tv, lo_tv = to_tv(r0), to_tv(lo)

    out = {}
    for i, p in enumerate(ids):
        out[str(p)] = {"r": round(float(r_tv[i]), 3), "lo": round(float(lo_tv[i]), 3),
                       "raw": round(float(r0[i]), 4), "se": round(float(se[i]), 4),
                       "eff": round(float(info[i]), 2), "n": int(nm[i])}
    json.dump({"config": c, "reps": reps, "clusters": int(len(uniq)), "ratings": out},
              open(OUT, "w"), indent=1)
    print(f"\nwrote {os.path.relpath(OUT)} ({len(out)} players, {reps} replicates)")

    solid = nm >= 20
    print(f"\nstandard error among the {int(solid.sum())} players with 20+ observations:")
    for q in (10, 25, 50, 75, 90, 99):
        print(f"  {q:>2}th percentile  {np.percentile(se[solid], q):.3f}")
    print("\neffective observations vs actual, for the same players -- the ratio is how "
          "\ncompetitive a schedule was, and it is what a match count cannot show:")
    ratio = np.where(nm > 0, info / np.maximum(nm, 1), 0.0)
    for q in (10, 50, 90):
        print(f"  {q:>2}th percentile  {ratio[solid][np.argsort(ratio[solid])][int(q / 100 * (solid.sum() - 1))]:.3f}")


if __name__ == "__main__":
    main(sys.argv[1:])
