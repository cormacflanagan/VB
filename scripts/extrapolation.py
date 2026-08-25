"""Does a rating built against soft opposition survive contact with hard opposition?

  python3 scripts/extrapolation.py

scripts/shrink.py asked whether loosely-determined ratings are too high and got a clear
answer in the opposite direction: the side with the larger standard error wins about 15
points more often than predicted, and deducting standard errors makes held-out prediction
strictly worse. Taken at face value that says thin evidence produces ratings that are too
*low*.

Face value is wrong here, because standard error is dominated by match count. A player with
a handful of results is pulled toward the ridge's target by the prior, and if that target
sits below the strength of a typical *match participant* -- which it does, since the player
pool is full of one-tournament entrants while the matches are played by regulars -- then
every newcomer is underrated and the bucket analysis picks that up. It is a real defect. It
is not the one under investigation.

The complaint that prompted this was about a different shape: a player with a long record,
not a short one, whose opposition never approached her own rating. 114 matches, a mean
opponent of 5.56, a ceiling of 7.5, and a rating of 8.7 -- a number no result of hers
directly tested. Match count cannot separate her from a well-tested player, and neither can
a standard error that match count dominates.

So this asks the question directly, and in three ways that do not share the confound:

  1. Split by *effective* observations -- sum of w*p(1-p), the information a logistic model
     actually extracts -- holding raw match count fixed. Two players with 200 matches each,
     one against even opposition and one against overmatched fields, differ several-fold
     here and not at all in the count.

  2. Split by reach: how far above her usual opposition a team is playing in the held-out
     match. A rating that is extrapolated rather than observed should fail exactly when it
     is finally asked to predict a level the player has not met.

  3. Restrict to the specific shape complained about -- long record, low effective
     information, high partner concentration -- and score only those players' held-out
     matches against strong opposition, which is the handful of results that would settle
     it either way.

The standard errors come from the training-window bootstrap scripts/shrink.py already ran
and saved, so nothing here refits or peeks at the holdout.
"""
import json, os, sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "extrapolation.json")
STRONG_Q = 0.90       # "strong opposition" for part 3, as a quantile of match participants


def table(name, rows, unit=""):
    print(f"\n  {name}")
    print(f"  {'':>16}{'MATCHES':>9}{'PREDICTED':>11}{'ACTUAL':>9}{'ERROR':>8}")
    for lab, n, pr, ac in rows:
        if n < 200:
            continue
        print(f"  {lab:>16}{n:>9,}{pr:>10.1%}{ac:>9.1%}{ac - pr:>+8.1%}")


def bucketize(vals, side_pred, side_won, edges, fmt):
    out = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        g = (vals >= lo) & (vals <= hi if i == len(edges) - 2 else vals < hi)
        if g.sum() < 200:
            continue
        out.append((fmt(lo, hi), int(g.sum()), float(side_pred[g].mean()),
                    float(side_won[g].mean())))
    return out


def main(argv):
    c = rate.conf(argv)
    ids, ix, d = rate.load(c)
    n = len(ids)
    print("\n  refitting the training window")
    r = rate.fit(n, d, c, quiet=True)

    z = np.load(os.path.join(DATA, "se_train.npz"))
    if list(z["ids"]) != list(ids):
        sys.exit("se_train.npz was built from a different player index -- rerun shrink.py")
    se = z["se"]

    tr = d["train"]
    a1, a2, b1, b2 = d["a1"], d["a2"], d["b1"], d["b2"]
    alpha, s = c["pair_alpha"], c["scale"]

    # per-player training-window summaries
    zt = (rate.team(r, a1[tr], a2[tr], alpha) - rate.team(r, b1[tr], b2[tr], alpha)) / s
    pt = 1.0 / (1.0 + np.exp(-zt))
    w = d["w"][tr]
    nobs = np.zeros(n)
    eff = np.zeros(n)
    oppsum = np.zeros(n)
    oppw = np.zeros(n)
    ta = rate.team(r, a1[tr], a2[tr], alpha)
    tb = rate.team(r, b1[tr], b2[tr], alpha)
    for ks, opp in (("a1", tb), ("a2", tb), ("b1", ta), ("b2", ta)):
        idx = d[ks][tr]
        np.add.at(nobs, idx, 1.0)
        np.add.at(eff, idx, w * pt * (1 - pt))
        np.add.at(oppsum, idx, w * opp)
        np.add.at(oppw, idx, w)
    meanopp = np.where(oppw > 0, oppsum / np.maximum(oppw, 1e-9), 0.0)
    ratio = np.where(nobs > 0, eff / np.maximum(nobs, 1), 0.0)

    ok = ~tr & d["real"]
    y = d["y"][ok]
    za = rate.team(r, a1[ok], a2[ok], alpha)
    zb = rate.team(r, b1[ok], b2[ok], alpha)
    p0 = 1.0 / (1.0 + np.exp(-(za - zb) / s))
    res = {}

    # ---- 1. effective observations, holding match count fixed --------------------
    na = 0.5 * (nobs[a1[ok]] + nobs[a2[ok]])
    nb = 0.5 * (nobs[b1[ok]] + nobs[b2[ok]])
    ra = 0.5 * (ratio[a1[ok]] + ratio[a2[ok]])
    rb = 0.5 * (ratio[b1[ok]] + ratio[b2[ok]])
    busy = (na >= 50) & (nb >= 50)
    print(f"\n{int(ok.sum()):,} held-out matches; {int(busy.sum()):,} where both sides "
          f"average 50+ training matches")
    # orient toward the side whose results were the more lopsided (lower information rate)
    soft_is_a = ra <= rb
    p_soft = np.where(soft_is_a, p0, 1 - p0)
    won_soft = np.where(soft_is_a, y, 1 - y)
    gap = np.abs(ra - rb)
    g2 = gap[busy]
    edges = np.quantile(g2, [0, 0.25, 0.5, 0.75, 1.0])
    rows = bucketize(g2, p_soft[busy], won_soft[busy], edges,
                     lambda lo, hi: f"{lo:.3f}-{hi:.3f}")
    table("the side with the more lopsided record, both sides 50+ matches:", rows)
    res["byInformation"] = [{"label": a, "n": b, "pred": cc, "act": dd}
                            for a, b, cc, dd in rows]

    # ---- 2. reach: playing above the level you usually meet ----------------------
    ma = 0.5 * (meanopp[a1[ok]] + meanopp[a2[ok]])
    mb = 0.5 * (meanopp[b1[ok]] + meanopp[b2[ok]])
    reach_a = zb - ma          # how far above A's usual opposition this opponent is
    reach_b = za - mb
    stretch_is_a = reach_a >= reach_b
    p_str = np.where(stretch_is_a, p0, 1 - p0)
    won_str = np.where(stretch_is_a, y, 1 - y)
    rr = np.where(stretch_is_a, reach_a, reach_b)
    sel = busy & (na >= 50) & (nb >= 50)
    edges = np.quantile(rr[sel], [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    rows = bucketize(rr[sel], p_str[sel], won_str[sel], edges,
                     lambda lo, hi: f"{lo:+.2f}-{hi:+.2f}")
    table("the side reaching furthest above its usual opposition:", rows)
    res["byReach"] = [{"label": a, "n": b, "pred": cc, "act": dd}
                      for a, b, cc, dd in rows]

    # ---- 3. the specific shape complained about ---------------------------------
    part = np.array(partner_share(ids, ix, d, tr))
    strong = np.quantile(r[np.array([i for i in range(n) if nobs[i] >= 20])], STRONG_Q)
    thin = (nobs >= 50) & (ratio <= np.quantile(ratio[nobs >= 50], 0.25)) & (part >= 0.5)
    print(f"\n  {int(thin.sum()):,} players with 50+ matches, bottom-quartile information "
          f"rate and 50%+ of matches with one partner")
    print(f"  'strong opposition' = team rating above {strong:.2f} raw "
          f"({STRONG_Q:.0%} of players with 20+ matches)")
    rows = []
    for lab, mask in (("all opposition", np.ones(int(ok.sum()), bool)),
                      ("vs strong only", None)):
        ina = thin[a1[ok]] | thin[a2[ok]]
        inb = thin[b1[ok]] | thin[b2[ok]]
        pick_a = ina & ~inb
        pick_b = inb & ~ina
        sel2 = pick_a | pick_b
        opp = np.where(pick_a, zb, za)
        if lab == "vs strong only":
            sel2 = sel2 & (opp >= strong)
        if sel2.sum() < 50:
            continue
        pp = np.where(pick_a, p0, 1 - p0)[sel2]
        yy = np.where(pick_a, y, 1 - y)[sel2]
        rows.append((lab, int(sel2.sum()), float(pp.mean()), float(yy.mean())))
    table("held-out matches for exactly that group:", rows)
    res["thinShape"] = [{"label": a, "n": b, "pred": cc, "act": dd}
                        for a, b, cc, dd in rows]
    res["thinPlayers"] = int(thin.sum())

    json.dump(res, open(OUT, "w"), indent=1)
    print(f"\nwrote {os.path.relpath(OUT)}")


def partner_share(ids, ix, d, tr):
    """Share of a player's training matches spent with her most frequent partner."""
    pairs = defaultdict(lambda: defaultdict(int))
    tot = defaultdict(int)
    for k1, k2 in (("a1", "a2"), ("b1", "b2")):
        i, j = d[k1][tr], d[k2][tr]
        for x, yy in zip(i, j):
            pairs[x][yy] += 1
            pairs[yy][x] += 1
            tot[x] += 1
            tot[yy] += 1
    return [max(pairs[i].values()) / tot[i] if tot.get(i) else 0.0
            for i in range(len(ids))]


if __name__ == "__main__":
    main(sys.argv[1:])
