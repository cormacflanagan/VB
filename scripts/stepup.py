"""Why do teams stepping up in class underperform? Two controls that tell the causes apart.

  python3 scripts/stepup.py

scripts/extrapolation.py found a clean, monotone effect: a team playing far above its usual
opposition wins 11.9% of the time where the model predicts 18.0%. Three explanations fit
that shape, and they call for completely different responses, so guessing between them is
not an option.

  Winner's curse. "Reach" is measured against a player's own *estimated* rating, so a
  rating inflated by luck automatically looks like it has been playing soft opposition, and
  the step-up match is where the luck runs out. This is a property of every estimated
  rating and would appear even in a perfectly specified model. It predicts the bias is
  concentrated in imprecisely-determined teams and near-absent in well-determined ones.

  A scale that is too flat. One rating point might simply buy more than the model thinks
  at the top. scripts/curvesweep.py already argues against this: curvature does flatten the
  step-up bias, from -6.2% to -2.3%, but makes held-out log-loss monotonically worse, which
  is what a knob fixing a selected subgroup at the expense of everyone else looks like.
  Kept here as the null to beat.

  The standings pairs. Two thirds of the training weight comes from real matches and the
  rest from finish orders expanded into pairwise rows -- in a 32-team draw the winner is
  paired against the last-placed team, an enormous implied gap that never actually played.
  Those pairs are concentrated exactly in the large-gap region where the miscalibration
  lives, and the holdout is real matches only. Dropping them is a one-line control.

The first is checked by splitting the same step-up matches by how precisely the stretching
team is determined, using the training-window bootstrap saved by scripts/shrink.py. The
third is checked by refitting with finish_weight = 0.
"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "stepup.json")


def setup(r, d, c, tr, ok):
    """Per-match: predicted and actual for the stretching side, its reach, and its size."""
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
    is_a = (zb - ma) >= (za - mb)
    return dict(p=np.where(is_a, p0, 1 - p0), won=np.where(is_a, y, 1 - y),
                reach=np.where(is_a, zb - ma, za - mb),
                busy=(na >= 50) & (nb >= 50), is_a=is_a)


def worst(s, extra=None):
    sel = s["busy"] if extra is None else (s["busy"] & extra)
    if sel.sum() < 200:
        return None
    cut = np.quantile(s["reach"][sel], 0.8)
    g = sel & (s["reach"] >= cut)
    return (int(g.sum()), float(s["p"][g].mean()), float(s["won"][g].mean()))


def show(lab, t):
    if not t:
        print(f"  {lab:>26}      too few matches")
        return
    n, pr, ac = t
    print(f"  {lab:>26}{n:>9,}{pr:>12.1%}{ac:>9.1%}{ac - pr:>+8.1%}")


def main(argv):
    base = rate.conf(argv)
    ids, ix, d = rate.load(base)
    n = len(ids)
    tr, ok = d["train"], (~d["train"] & d["real"])
    res = {}

    print("\n  refitting the training window")
    r = rate.fit(n, d, base, quiet=True)
    s = setup(r, d, base, tr, ok)
    print(f"\n  {'':>26}{'MATCHES':>9}{'PREDICTED':>12}{'ACTUAL':>9}{'ERROR':>8}")
    show("all step-ups", worst(s))

    # ---- control 1: is it winner's curse? split by how precisely determined -------
    z = np.load(os.path.join(DATA, "se_train.npz"))
    if list(z["ids"]) == list(ids):
        se = z["se"]
        a1, a2, b1, b2 = d["a1"][ok], d["a2"][ok], d["b1"][ok], d["b2"][ok]
        sa = 0.5 * (se[a1] + se[a2])
        sb = 0.5 * (se[b1] + se[b2])
        stretch_se = np.where(s["is_a"], sa, sb)
        q = np.quantile(stretch_se[s["busy"]], [0.5])
        print("\n  split by how precisely the stretching team is determined:")
        show("precise half", worst(s, stretch_se <= q[0]))
        show("imprecise half", worst(s, stretch_se > q[0]))
        res["bySe"] = {"precise": worst(s, stretch_se <= q[0]),
                       "imprecise": worst(s, stretch_se > q[0])}
        print("  Winner's curse predicts a much larger error in the imprecise half. If the\n"
              "  two are close, the bias is structural and no amount of shrinkage cures it.")
    else:
        print("\n  (se_train.npz has a stale player index -- skipping the precision split)")

    # ---- control 2: is it the standings pairs? -----------------------------------
    print("\n  refitting on real matches only (finish_weight = 0)")
    c0 = dict(base, finish_weight=0.0)
    ids0, ix0, d0 = rate.load(c0, quiet=True)
    r0 = rate.fit(len(ids0), d0, c0, quiet=True)
    tr0, ok0 = d0["train"], (~d0["train"] & d0["real"])
    s0 = setup(r0, d0, c0, tr0, ok0)
    ll, acc, br = rate.score(r0, d0, c0, ok0)
    llb, accb, brb = rate.score(r, d, base, ok)
    print(f"\n  {'':>26}{'MATCHES':>9}{'PREDICTED':>12}{'ACTUAL':>9}{'ERROR':>8}")
    show("with standings pairs", worst(s))
    show("matches only", worst(s0))
    print(f"\n  holdout log-loss  with standings {llb:.4f}   matches only {ll:.4f}")
    res["byFinish"] = {"with": worst(s), "without": worst(s0),
                       "llWith": float(llb), "llWithout": float(ll)}

    json.dump(res, open(OUT, "w"), indent=1)
    print(f"\nwrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
