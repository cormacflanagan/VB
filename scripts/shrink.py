"""Does the point estimate systematically overrate thin-evidence players? Measure it.

  python3 scripts/shrink.py [--reps 40]

The complaint that started this is easy to state and easy to get wrong: a player ranked
twelfth in her cohort on a record built almost entirely against people far below her looks
overrated. She might not be. Beating weak fields with a weak partner is real evidence of
something, and "her schedule looks soft to me" is not a measurement.

So measure it, on matches the model has never seen.

  1. Fit on everything older than `holdout_days`.
  2. Bootstrap that same training window by tournament-division to get each player's
     standard error -- computed inside the training data only, so nothing about the
     holdout leaks into the quantity being tested.
  3. Score the held-out matches, split by how well determined the players in them are.

If the point estimate is unbiased, teams carrying a big standard error should win about as
often as predicted. If thin evidence inflates a rating, they will win *less* often than
predicted, and the size of that shortfall is the correction the ranking needs.

Step 4 then tunes the correction the same way every other knob in this repo is tuned: try
`r - k*se` for a range of k, keep the k with the best held-out log-loss. k = 0 is the
plain point estimate, so if shrinking does not help, this reports that it does not.

The k it finds is used by scripts/cohort_rank_page.py to rank on evidence rather than on
the most flattering reading of a record.
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "shrink.json")
KS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]


def bootstrap(n, d, c, mask, reps, seed):
    cl = d["cluster"]
    uniq, cidx = np.unique(cl, return_inverse=True)
    base = d["w"].copy()
    rng = np.random.default_rng(seed)
    acc = np.zeros(n)
    acc2 = np.zeros(n)
    for b in range(reps):
        gw = rng.exponential(1.0, size=len(uniq))
        gw /= gw.mean()
        d["w"] = base * gw[cidx]
        t0 = time.time()
        rb = rate.fit(n, d, c, mask=mask, quiet=True)
        acc += rb
        acc2 += rb * rb
        print(f"    replicate {b + 1:>3}/{reps}  {time.time() - t0:.0f}s", flush=True)
    d["w"] = base
    mean = acc / reps
    var = np.maximum(acc2 / reps - mean * mean, 0.0) * reps / max(reps - 1, 1)
    return np.sqrt(var)


def probs(r, d, c, ok):
    z = (rate.team(r, d["a1"][ok], d["a2"][ok], c["pair_alpha"])
         - rate.team(r, d["b1"][ok], d["b2"][ok], c["pair_alpha"])) / c["scale"]
    return 1.0 / (1.0 + np.exp(-z))


def main(argv):
    reps = int(argv[argv.index("--reps") + 1]) if "--reps" in argv else 40
    c = rate.conf(argv)
    ids, ix, d = rate.load(c)
    n = len(ids)

    print("\n  fitting on the training window")
    r_tr = rate.fit(n, d, c, quiet=True)
    print(f"  bootstrapping the training window ({reps} replicates)")
    se = bootstrap(n, d, c, d["train"], reps, 990425)

    ok = ~d["train"] & d["real"]
    y = d["y"][ok]
    print(f"\n{int(ok.sum())} held-out matches\n")

    # 3. calibration by how well determined the four players are. The team's uncertainty
    #    is what matters for the prediction, so pair the two sides' mean standard error
    #    and split on the larger.
    sa = 0.5 * (se[d["a1"][ok]] + se[d["a2"][ok]])
    sb = 0.5 * (se[d["b1"][ok]] + se[d["b2"][ok]])
    p0 = probs(r_tr, d, c, ok)
    # orient every row as "the less well determined side": did the shakier team win?
    shaky_is_a = sa >= sb
    p_shaky = np.where(shaky_is_a, p0, 1 - p0)
    won_shaky = np.where(shaky_is_a, y, 1 - y)
    gap = np.abs(sa - sb)
    edges = np.quantile(gap, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    print("  how the shakier side does against what the model predicts for it:")
    print(f"  {'SE GAP':>14}{'MATCHES':>9}{'PREDICTED':>11}{'ACTUAL':>9}{'ERROR':>8}")
    buckets = []
    for i in range(5):
        lo, hi = edges[i], edges[i + 1]
        g = (gap >= lo) & (gap <= hi if i == 4 else gap < hi)
        if g.sum() < 50:
            continue
        pr, ac = p_shaky[g].mean(), won_shaky[g].mean()
        print(f"  {lo:>6.2f}-{hi:<7.2f}{int(g.sum()):>9}{pr:>10.1%}{ac:>9.1%}{ac - pr:>+8.1%}")
        buckets.append({"label": f"{lo:.2f}–{hi:.2f}", "lo": round(float(lo), 4),
                        "hi": round(float(hi), 4), "n": int(g.sum()),
                        "pred": round(float(pr), 5), "act": round(float(ac), 5)})

    # 4. tune the correction on the same held-out matches
    print("\n  held-out log-loss for strength = r - k*se:")
    print(f"  {'k':>6}{'LOG-LOSS':>11}{'ACCURACY':>10}{'BRIER':>9}")
    best, grid = None, []
    for k in KS:
        rk = r_tr - k * se
        p = probs(rk, d, c, ok)
        ll = -np.mean(y * np.log(p + 1e-9) + (1 - y) * np.log(1 - p + 1e-9))
        acc = np.mean((p > 0.5) == (y > 0.5))
        br = np.mean((p - y) ** 2)
        flag = ""
        if best is None or ll < best[1]:
            best, flag = (k, ll), "   <-"
        grid.append({"k": k, "ll": round(float(ll), 5), "acc": round(float(acc), 5),
                     "brier": round(float(br), 5)})
        print(f"  {k:>6.2f}{ll:>11.4f}{acc:>10.3f}{br:>9.4f}{flag}")
    print(f"\n  best k = {best[0]:.2f}")

    np.savez(os.path.join(DATA, "se_train.npz"), se=se, ids=np.array(ids))
    json.dump({"k": best[0], "reps": reps, "holdout": int(ok.sum()),
               "calibration": buckets, "grid": grid, "config": c},
              open(OUT, "w"), indent=1)
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
