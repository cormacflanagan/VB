"""Which combination of the benchmark's models predicts best, chosen honestly.

  python3 scripts/ensemble.py

scripts/bench.py found that a plain three-way average beats every model in it, including
each of its own members and including the learned stacker. That is worth pushing on, but
carefully: there are sixty-three non-empty subsets of six models, and picking the best of
sixty-three on the test set would be the same mistake this repository has now made twice.

So the subsets are ranked on validation and exactly one of them is scored on test. The
selection effect for a choice among sixty-three at a standard error of 0.0023 is about
0.0066, which is printed alongside so the reported gain can be judged against it.

Two weighting schemes are compared at the end. Equal weights cannot overfit at all. Weights
fitted by logistic regression on the validation predictions can, and the point of showing
both is to find out whether the fitting buys anything once the test window has its say --
scripts/bench.py's `stack` suggests it does not.

Base predictions are computed once and cached, so the subset search itself is free.
"""
import itertools, json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench
import models

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OUT = os.path.join(DATA, "ensemble.json")
BASE = ["bt", "bt_fast", "bt_margin", "massey", "elo", "glicko"]


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def main(argv):
    ids, ix, d = bench.load()
    fin = bench.standings(ix)
    n = len(ids)
    yv, yt = d["y"][d["valid"]], d["y"][d["test"]]

    print("\n  computing base predictions")
    LV, LT = {}, {}
    for name in BASE:
        t0 = time.time()
        fn = models.MODELS[name]
        LV[name] = logit(fn(n, d, fin, d["train"], d["valid"]))
        LT[name] = logit(fn(n, d, fin, d["train"] | d["valid"], d["test"]))
        print(f"    {name:<12}{time.time() - t0:>5.0f}s")

    subsets = []
    for k in range(1, len(BASE) + 1):
        for combo in itertools.combinations(BASE, k):
            zv = np.mean([LV[m] for m in combo], axis=0)
            subsets.append((bench.score(models._sig(zv), yv)["ll"], combo))
    subsets.sort()

    se = 0.6 / np.sqrt(len(yv))
    bias = se * np.sqrt(2 * np.log(len(subsets)))
    print(f"\n  {len(subsets)} subsets ranked on validation "
          f"(se {se:.4f}, selection effect for this many {bias:.4f})\n")
    print(f"  {'RANK':>5}{'VALID LL':>10}   MEMBERS")
    for i, (ll, combo) in enumerate(subsets[:8], 1):
        print(f"  {i:>5}{ll:>10.4f}   {' + '.join(combo)}")
    print(f"  {'...':>5}")
    for i, (ll, combo) in enumerate(subsets[-2:], len(subsets) - 1):
        print(f"  {i:>5}{ll:>10.4f}   {' + '.join(combo)}")

    best_ll, best = subsets[0]
    zt = np.mean([LT[m] for m in best], axis=0)
    eq = bench.score(models._sig(zt), yt)

    # fitted weights, learned on the validation predictions only
    Xv = np.stack([LV[m] for m in best], 1)
    Xv = np.hstack([np.ones((len(Xv), 1)), Xv])
    Xt = np.stack([LT[m] for m in best], 1)
    Xt = np.hstack([np.ones((len(Xt), 1)), Xt])

    def grad(b):
        return Xv.T @ (models._sig(Xv @ b) - yv) + 1e-3 * len(yv) * np.concatenate(
            [[0.0], b[1:]])

    b = models._adam(grad, np.zeros(Xv.shape[1]), iters=1200, lr=0.05)
    wt = bench.score(models._sig(Xt @ b), yt)

    single = min((bench.score(models._sig(LT[m]), yt)["ll"], m) for m in BASE)
    print(f"\n  chosen on validation: {' + '.join(best)}   (valid {best_ll:.4f})")
    print(f"\n  {'':<22}{'TEST LL':>9}{'ACC':>8}{'BRIER':>9}")
    print(f"  {'best single model':<22}{single[0]:>9.4f}"
          f"{'':>8}{'':>9}   ({single[1]})")
    print(f"  {'equal weights':<22}{eq['ll']:>9.4f}{eq['acc']:>8.3f}{eq['brier']:>9.4f}")
    print(f"  {'fitted weights':<22}{wt['ll']:>9.4f}{wt['acc']:>8.3f}{wt['brier']:>9.4f}")
    print(f"\n  weights: " + "  ".join(f"{m} {v:+.2f}" for m, v in zip(best, b[1:]))
          + f"   intercept {b[0]:+.2f}")
    verdict = ("fitting the weights helps" if wt["ll"] < eq["ll"] - se
               else "fitting the weights does not beat a plain average")
    print(f"  {verdict}")

    json.dump({"base": BASE, "chosen": list(best), "validLl": best_ll,
               "se": se, "selectionBias": bias, "equal": eq, "fitted": wt,
               "weights": dict(zip(best, [float(v) for v in b[1:]])),
               "bestSingle": {"model": single[1], "testLl": single[0]},
               "ranking": [{"members": list(c), "validLl": float(l)}
                           for l, c in subsets]},
              open(OUT, "w"), indent=1)
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
