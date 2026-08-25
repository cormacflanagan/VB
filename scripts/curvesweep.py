"""Tune the link's curvature on held-out matches, and check it fixes what it was for.

  python3 scripts/curvesweep.py

A knob that improves held-out log-loss has earned its place; a knob that also removes the
specific miscalibration it was introduced to remove has earned it twice. So this reports
both: the holdout score at each setting, and what happens to the step-up bias measured in
scripts/extrapolation.py -- teams playing far above their usual level losing 6.2% more
often than predicted.

If curvature is the right explanation, the best setting by log-loss should also be the one
that flattens that bias toward zero. If the two disagree, the knob is fitting something
else and should be treated with suspicion.
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "curve.json")
CURVES = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.45]


def reach_bias(r, d, c, tr, ok):
    """Worst-quintile step-up error: actual minus predicted for the stretching side."""
    alpha = c["pair_alpha"]
    a1, a2, b1, b2 = d["a1"], d["a2"], d["b1"], d["b2"]
    w = d["w"][tr]
    ta = rate.team(r, a1[tr], a2[tr], alpha)
    tb = rate.team(r, b1[tr], b2[tr], alpha)
    n = len(r)
    oppsum, oppw, nobs = np.zeros(n), np.zeros(n), np.zeros(n)
    for ks, opp in (("a1", tb), ("a2", tb), ("b1", ta), ("b2", ta)):
        idx = d[ks][tr]
        np.add.at(oppsum, idx, w * opp)
        np.add.at(oppw, idx, w)
        np.add.at(nobs, idx, 1.0)
    meanopp = np.where(oppw > 0, oppsum / np.maximum(oppw, 1e-9), 0.0)

    za = rate.team(r, a1[ok], a2[ok], alpha)
    zb = rate.team(r, b1[ok], b2[ok], alpha)
    p0 = 1.0 / (1.0 + np.exp(-rate.link(za - zb, c) / c["scale"]))
    y = d["y"][ok]
    ma = 0.5 * (meanopp[a1[ok]] + meanopp[a2[ok]])
    mb = 0.5 * (meanopp[b1[ok]] + meanopp[b2[ok]])
    na = 0.5 * (nobs[a1[ok]] + nobs[a2[ok]])
    nb = 0.5 * (nobs[b1[ok]] + nobs[b2[ok]])
    ra, rb = zb - ma, za - mb
    is_a = ra >= rb
    p = np.where(is_a, p0, 1 - p0)
    won = np.where(is_a, y, 1 - y)
    rr = np.where(is_a, ra, rb)
    sel = (na >= 50) & (nb >= 50)
    cut = np.quantile(rr[sel], 0.8)
    g = sel & (rr >= cut)
    return float(won[g].mean() - p[g].mean()), float(p[g].mean()), float(won[g].mean()), int(g.sum())


def main(argv):
    base = rate.conf(argv)
    ids, ix, d = rate.load(base)
    n = len(ids)
    tr, ok = d["train"], (~d["train"] & d["real"])
    print(f"\n{int(ok.sum()):,} held-out matches\n")
    print(f"  {'CURVE':>7}{'LOG-LOSS':>11}{'ACCURACY':>10}{'BRIER':>9}"
          f"{'STEP-UP PRED':>14}{'ACTUAL':>9}{'ERROR':>8}")
    rows, best = [], None
    for k in CURVES:
        c = dict(base, curve=k)
        t0 = time.time()
        r = rate.fit(n, d, c, quiet=True)
        ll, acc, br = rate.score(r, d, c, ok)
        bias, pr, ac, cnt = reach_bias(r, d, c, tr, ok)
        flag = ""
        if best is None or ll < best[1]:
            best, flag = (k, ll), "  <-"
        rows.append({"curve": k, "ll": round(float(ll), 5), "acc": round(float(acc), 5),
                     "brier": round(float(br), 5), "stepPred": round(pr, 5),
                     "stepAct": round(ac, 5), "stepErr": round(bias, 5), "stepN": cnt})
        print(f"  {k:>7.2f}{ll:>11.4f}{acc:>10.3f}{br:>9.4f}"
              f"{pr:>13.1%}{ac:>9.1%}{bias:>+8.1%}{flag}   ({time.time() - t0:.0f}s)")
    print(f"\n  best curve by held-out log-loss: {best[0]:g}")
    flat = min(rows, key=lambda t: abs(t["stepErr"]))
    print(f"  flattest step-up bias at curve {flat['curve']:g} ({flat['stepErr']:+.1%})")
    json.dump({"best": best[0], "flattest": flat["curve"], "grid": rows},
              open(OUT, "w"), indent=1)
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
