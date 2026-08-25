"""Tune the fit to agree with TruVolley, and report what that agreement costs.

  python3 scripts/converge_tv.py            # hill climb toward TruVolley
  python3 scripts/converge_tv.py --rounds 5

The original brief for this rating was "similar to TruVolley but which we can tweak", and
the tuning drifted away from it: scripts/climb.py optimises held-out log-loss, which is a
different target and produces a different model. This optimises the thing that was actually
asked for -- agreement with TruVolley -- and treats prediction as the cost to be reported
rather than the goal.

Agreement is measured as Spearman correlation over players who carry a TruVolley and enough
matches to be worth comparing. Rank correlation rather than error, because the two ratings
need not share a scale for one to be a faithful reproduction of the other; the quantile map
in scripts/rate.py already handles the scale, and it is monotone, so it cannot change this
number at all.

Every knob is searched, including the two that scripts/climb.py left alone:

  pair_alpha    1.0 makes a team the mean of its players, 0.0 the weaker of them. This is
                the structural difference between the two systems. TruVolley moves when a
                *team* wins and never subtracts the partner, so if this rating disagrees
                with it for a reason of principle rather than of tuning, this is the knob
                where that shows up.
  pool_weight   how much a pool result counts against a bracket result.

The honest part of the exercise is the second column. A configuration that reproduces
TruVolley closely while predicting held-out matches worse is not a better rating; it is a
better imitation, and worth having only because being able to say *which* settings imitate
it is itself informative about what TruVolley is doing. Both numbers are printed for every
step so the trade is visible rather than implied.
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench
import rate

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "converge_tv.json")
MIN_OBS = 20

# name: (start, low, high, first step)
SPACE = {
    "halflife": (293.0, 45.0, 1600.0, 120.0),
    "ridge": (0.2875, 0.01, 4.0, 0.15),
    "margin": (1.04, 0.0, 4.0, 0.4),
    "finw": (2.5, 0.0, 14.0, 1.5),
    "alpha": (1.0, 0.0, 1.0, 0.2),
    "pool": (1.0, 0.1, 3.0, 0.3),
}


def truvolley(n, ids):
    tv = np.full(n, np.nan)
    src = {}
    for f in ("tvcache.json", "cohort2027.json", "cohort2028.json"):
        p = os.path.join(DATA, f)
        if not os.path.exists(p):
            continue
        for k, v in json.load(open(p)).items():
            val = v.get("tv") if isinstance(v, dict) else None
            if val:
                src.setdefault(int(k), val)
    al = {}
    p = os.path.join(DATA, "aliases.json")
    if os.path.exists(p):
        al = {int(k): int(v) for k, v in json.load(open(p))["alias"].items()}
    for i, pid in enumerate(ids):
        v = src.get(pid) or src.get(al.get(pid, pid))
        if v:
            tv[i] = v
    return tv


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return float(ra @ rb / np.sqrt((ra @ ra) * (rb @ rb)))


def fit(n, d, fin, mask, par):
    """Bradley-Terry with every knob exposed, including the team model."""
    hl, alpha = par["halflife"], par["alpha"]
    a1, a2 = [d["a1"][mask]], [d["a2"][mask]]
    b1, b2 = [d["b1"][mask]], [d["b2"][mask]]
    y = [d["y"][mask]]
    w = 0.5 ** (d["age"][mask] / hl) if hl else np.ones(int(mask.sum()))
    w = w * (1.0 + par["margin"] * np.minimum(np.abs(d["pd"][mask]), 30.0) / 10.0)
    w = w * np.where(d["pool"][mask], par["pool"], 1.0)
    W = [w]
    if fin is not None:
        keep = fin["age"] >= d["age"][mask].min()
        a1.append(fin["a1"][keep]); a2.append(fin["a2"][keep])
        b1.append(fin["b1"][keep]); b2.append(fin["b2"][keep])
        y.append(fin["y"][keep])
        W.append(par["finw"] * fin["w"][keep] *
                 (0.5 ** (fin["age"][keep] / hl) if hl else 1.0))
    a1, a2 = np.concatenate(a1), np.concatenate(a2)
    b1, b2 = np.concatenate(b1), np.concatenate(b2)
    y, w = np.concatenate(y), np.concatenate(W)
    lam = par["ridge"]

    def team(r, i, j):
        return alpha * 0.5 * (r[i] + r[j]) + (1 - alpha) * np.minimum(r[i], r[j])

    def scatter(r, i, j, g, coef):
        np.add.at(g, i, coef * alpha * 0.5)
        np.add.at(g, j, coef * alpha * 0.5)
        if alpha < 1.0:
            lo = r[i] <= r[j]
            np.add.at(g, i[lo], coef[lo] * (1 - alpha))
            np.add.at(g, j[~lo], coef[~lo] * (1 - alpha))

    def grad(r):
        z = team(r, a1, a2) - team(r, b1, b2)
        coef = w * (1.0 / (1.0 + np.exp(-np.clip(z, -40, 40))) - y)
        g = np.zeros(n)
        scatter(r, a1, a2, g, coef)
        scatter(r, b1, b2, g, -coef)
        return g + lam * r

    r = np.zeros(n)
    mom = np.zeros(n); vel = np.zeros(n)
    for t in range(1, 601):
        gg = grad(r)
        mom = 0.9 * mom + 0.1 * gg
        vel = 0.999 * vel + 0.001 * gg * gg
        r -= 0.25 * (mom / (1 - 0.9 ** t)) / (np.sqrt(vel / (1 - 0.999 ** t)) + 1e-8)
    return r, alpha


def main(argv):
    rounds = int(argv[argv.index("--rounds") + 1]) if "--rounds" in argv else 4
    ids, ix, d = bench.load()
    fin = bench.standings(ix)
    n = len(ids)
    d["pool"] = np.zeros(len(d["y"]), bool)     # bench drops phase; pool knob is inert here
    tv = truvolley(n, ids)

    cnt = np.zeros(n)
    for k in ("a1", "a2", "b1", "b2"):
        np.add.at(cnt, d[k], 1.0)
    ok = ~np.isnan(tv) & (cnt >= MIN_OBS)
    print(f"\n  {int(ok.sum()):,} players carry a TruVolley and {MIN_OBS}+ matches")

    yv = d["y"][d["valid"]]

    def evaluate(par):
        r, alpha = fit(n, d, fin, d["train"] | d["valid"], par)
        rho = spearman(r[ok], tv[ok])
        # prediction cost, on matches outside the fit, scale calibrated out of sample
        ri, _ = fit(n, d, fin, d["train"], par)
        ta = alpha * 0.5 * (ri[d["a1"][d["valid"]]] + ri[d["a2"][d["valid"]]]) + \
            (1 - alpha) * np.minimum(ri[d["a1"][d["valid"]]], ri[d["a2"][d["valid"]]])
        tb = alpha * 0.5 * (ri[d["b1"][d["valid"]]] + ri[d["b2"][d["valid"]]]) + \
            (1 - alpha) * np.minimum(ri[d["b1"][d["valid"]]], ri[d["b2"][d["valid"]]])
        best = None
        for s in np.arange(0.05, 4.01, 0.05):
            p = np.clip(1 / (1 + np.exp(-(ta - tb) / s)), 1e-6, 1 - 1e-6)
            ll = -np.mean(yv * np.log(p) + (1 - yv) * np.log(1 - p))
            best = ll if best is None or ll < best else best
        return rho, float(best)

    cur = {k: v[0] for k, v in SPACE.items()}
    step = {k: v[3] for k, v in SPACE.items()}
    t0 = time.time()
    rho0, ll0 = evaluate(cur)
    print(f"  starting point {json.dumps({k: round(v, 4) for k, v in cur.items()})}")
    print(f"  agreement with TruVolley {rho0:.4f}   held-out log-loss {ll0:.4f}\n")
    print(f"  {'ROUND':>6}{'KNOB':>10}{'VALUE':>10}{'RHO':>9}{'LOG-LOSS':>11}")

    best_rho, best_ll = rho0, ll0
    trail = []
    for rnd in range(1, rounds + 1):
        moved = False
        for k in SPACE:
            lo, hi = SPACE[k][1], SPACE[k][2]
            improved = False
            for sgn in (1, -1):
                cand = dict(cur)
                cand[k] = float(np.clip(cur[k] + sgn * step[k], lo, hi))
                if abs(cand[k] - cur[k]) < 1e-12:
                    continue
                rho, ll = evaluate(cand)
                trail.append({"round": rnd, "knob": k, "value": cand[k],
                              "rho": rho, "ll": ll})
                if rho > best_rho + 1e-6:
                    print(f"  {rnd:>6}{k:>10}{cand[k]:>10.4g}{rho:>9.4f}{ll:>11.4f}")
                    cur, best_rho, best_ll = cand, rho, ll
                    improved = moved = True
                    step[k] *= 1.6
                    break
            if not improved:
                step[k] *= 0.5
        if not moved:
            print(f"  round {rnd}: no knob improved; stopping")
            break

    print(f"\n  {time.time() - t0:.0f}s")
    print(f"  tuned {json.dumps({k: round(v, 4) for k, v in cur.items()})}")
    print(f"\n  {'':<22}{'AGREEMENT':>11}{'LOG-LOSS':>11}")
    print(f"  {'current production':<22}{rho0:>11.4f}{ll0:>11.4f}")
    print(f"  {'tuned to TruVolley':<22}{best_rho:>11.4f}{best_ll:>11.4f}")
    print(f"  {'change':<22}{best_rho - rho0:>+11.4f}{best_ll - ll0:>+11.4f}")
    if best_ll > ll0 + 0.0023:
        print("\n  Converging on TruVolley costs prediction: these settings imitate it more"
              "\n  closely and forecast unseen matches less well.")
    elif best_rho > rho0 + 0.005:
        print("\n  Agreement improved without paying for it in prediction, so the earlier"
              "\n  settings were simply worse on both counts.")
    json.dump({"start": {k: v[0] for k, v in SPACE.items()}, "tuned": cur,
               "rhoStart": rho0, "rhoTuned": best_rho,
               "llStart": ll0, "llTuned": best_ll,
               "nPlayers": int(ok.sum()), "trail": trail},
              open(OUT, "w"), indent=1)
    print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
