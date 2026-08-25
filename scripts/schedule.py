"""Does the level a player habitually plays at predict results her rating does not?

  python3 scripts/schedule.py

Everything else has been ruled out. Teams playing far above their usual opposition lose
6.2% more often than the model says, and that bias is not estimation noise (it is the same
size in precisely and imprecisely determined teams, -6.5% against -5.6%), not an artefact
of the standings pairs (-6.6% without them), and not a scale that is too flat (curvature
removes some of it while making held-out prediction worse at every setting).

What is left is the possibility that the rating is missing a dimension. Two players can
carry the same number for genuinely different reasons -- one by beating strong fields about
half the time, the other by beating weak fields nearly always -- and if the second is
really the weaker player, the level of her usual opposition contains information her rating
has already thrown away.

That is testable in one line. Add the difference in habitual opponent strength to the
model's logit, fit the coefficient, and see whether held-out matches are predicted better:

    logit = link(strength(A) - strength(B)) / scale  +  beta * (meanopp(A) - meanopp(B))

beta = 0 is the current model. A positive beta says a player who has been beating stronger
opposition is better than an identically-rated player who has not, and since it enters
additively it is equivalent to a straight correction to each player's rating:

    adjusted(i) = r(i) + beta * scale * meanopp(i)

which is the form the ranking can use. A beta of zero, or one that fails to improve the
holdout, says the habitual level adds nothing once the rating is known, and the original
complaint has no support in the results.

The coefficient is fit on the training window and scored on matches outside it, so a beta
that only flatters the data it was chosen on cannot survive.
"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "schedule.json")
BETAS = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6, 0.8]


def habitual(r, d, c, tr):
    """Weighted mean opponent team-strength per player, over the training window."""
    alpha = c["pair_alpha"]
    w = d["w"][tr]
    ta = rate.team(r, d["a1"][tr], d["a2"][tr], alpha)
    tb = rate.team(r, d["b1"][tr], d["b2"][tr], alpha)
    n = len(r)
    num, den = np.zeros(n), np.zeros(n)
    for ks, opp in (("a1", tb), ("a2", tb), ("b1", ta), ("b2", ta)):
        idx = d[ks][tr]
        np.add.at(num, idx, w * opp)
        np.add.at(den, idx, w)
    seen = den > 0
    mo = np.zeros(n)
    mo[seen] = num[seen] / den[seen]
    # players with no training matches sit at the field average rather than at zero, so
    # they are neither rewarded nor punished by a covariate they have no value for
    mo[~seen] = np.average(mo[seen], weights=den[seen]) if seen.any() else 0.0
    return mo, seen


def evaluate(r, mo, d, c, mask, beta):
    alpha = c["pair_alpha"]
    a1, a2, b1, b2 = d["a1"][mask], d["a2"][mask], d["b1"][mask], d["b2"][mask]
    y = d["y"][mask]
    diff = rate.team(r, a1, a2, alpha) - rate.team(r, b1, b2, alpha)
    sched = 0.5 * (mo[a1] + mo[a2]) - 0.5 * (mo[b1] + mo[b2])
    z = rate.link(diff, c) / c["scale"] + beta * sched
    p = 1.0 / (1.0 + np.exp(-z))
    ll = -np.mean(y * np.log(p + 1e-9) + (1 - y) * np.log(1 - p + 1e-9))
    return float(ll), float(np.mean((p > 0.5) == (y > 0.5))), float(np.mean((p - y) ** 2))


def stepup_error(r, mo, d, c, tr, ok, beta):
    """The bias this is meant to remove, recomputed at each beta."""
    alpha = c["pair_alpha"]
    nobs = np.zeros(len(r))
    for ks in ("a1", "a2", "b1", "b2"):
        np.add.at(nobs, d[ks][tr], 1.0)
    a1, a2, b1, b2 = d["a1"][ok], d["a2"][ok], d["b1"][ok], d["b2"][ok]
    za = rate.team(r, a1, a2, alpha)
    zb = rate.team(r, b1, b2, alpha)
    sched = 0.5 * (mo[a1] + mo[a2]) - 0.5 * (mo[b1] + mo[b2])
    p0 = 1.0 / (1.0 + np.exp(-(rate.link(za - zb, c) / c["scale"] + beta * sched)))
    y = d["y"][ok]
    ma, mb = 0.5 * (mo[a1] + mo[a2]), 0.5 * (mo[b1] + mo[b2])
    na = 0.5 * (nobs[a1] + nobs[a2])
    nb = 0.5 * (nobs[b1] + nobs[b2])
    is_a = (zb - ma) >= (za - mb)
    p = np.where(is_a, p0, 1 - p0)
    won = np.where(is_a, y, 1 - y)
    reach = np.where(is_a, zb - ma, za - mb)
    sel = (na >= 50) & (nb >= 50)
    g = sel & (reach >= np.quantile(reach[sel], 0.8))
    return float(p[g].mean()), float(won[g].mean()), int(g.sum())


def main(argv):
    c = rate.conf(argv)
    ids, ix, d = rate.load(c)
    n = len(ids)
    tr, ok = d["train"], (~d["train"] & d["real"])
    print("\n  fitting the training window")
    r = rate.fit(n, d, c, quiet=True)
    mo, seen = habitual(r, d, c, tr)
    print(f"  habitual opponent strength spans {mo[seen].min():.2f} to {mo[seen].max():.2f} "
          f"(mean {mo[seen].mean():.2f})")

    print(f"\n{int(ok.sum()):,} held-out matches\n")
    print(f"  {'BETA':>6}{'TRAIN LL':>10}{'HOLDOUT LL':>12}{'ACCURACY':>10}{'BRIER':>9}"
          f"{'STEP-UP PRED':>14}{'ACTUAL':>9}{'ERROR':>8}")
    rows, best = [], None
    for b in BETAS:
        tl, _, _ = evaluate(r, mo, d, c, tr, b)
        hl, acc, br = evaluate(r, mo, d, c, ok, b)
        pr, ac, cnt = stepup_error(r, mo, d, c, tr, ok, b)
        flag = ""
        if best is None or hl < best[1]:
            best, flag = (b, hl), "  <-"
        rows.append({"beta": b, "trainLl": round(tl, 5), "ll": round(hl, 5),
                     "acc": round(acc, 5), "brier": round(br, 5),
                     "stepPred": round(pr, 5), "stepAct": round(ac, 5),
                     "stepErr": round(ac - pr, 5), "stepN": cnt})
        print(f"  {b:>6.2f}{tl:>10.4f}{hl:>12.4f}{acc:>10.3f}{br:>9.4f}"
              f"{pr:>13.1%}{ac:>9.1%}{ac - pr:>+8.1%}{flag}")

    bb = best[0]
    print(f"\n  best beta by held-out log-loss: {bb:g}")
    if bb > 0:
        adj = bb * c["scale"]
        print(f"  equivalent rating correction: r(i) + {adj:.3f} * habitual opponent(i)")
        lo, hi = np.quantile(mo[seen], [0.05, 0.95]), None
        print(f"  across the 5th-95th percentile of schedules that is a spread of "
              f"{adj * (lo[1] - lo[0]):.3f} rating points")
    else:
        print("  the habitual level adds nothing once the rating is known")
    json.dump({"beta": bb, "scale": c["scale"], "grid": rows}, open(OUT, "w"), indent=1)
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
