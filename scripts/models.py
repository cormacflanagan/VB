"""Prediction algorithms for scripts/bench.py, each fit on a mask and scored on another.

Every entrant has the same signature:

    fn(n_players, d, finishes, fit_mask, eval_mask) -> probability that side A wins

so the harness can swap them without knowing anything about how they work. What separates
them is what they are willing to assume:

  bt              the incumbent. One strength per player, team is the mean, logistic link.
  bt_fast         the same with a 120-day memory instead of 365, since the population
                  optimum and the right answer for a fast-improving junior differ.
  massey          least squares on point margin rather than logistic on the winner. Every
                  match here carries set scores and nothing has used them; a 21-19 and a
                  21-6 are the same row to Bradley-Terry and should not be.
  bt_margin       Bradley-Terry with each match weighted by how decisive it was, which
                  keeps the binary link but lets a blowout count for more than a squeaker.
  elo             online, sequential, one pass. Not a better optimiser of the same
                  objective -- a different model, in which a rating is what you were
                  playing like recently rather than an average over three years.
  glicko          Elo with a per-player step that shrinks as she plays and grows back as
                  she sits out, so newcomers move fast and veterans do not.
  pair            rates the partnership as its own entity, backing off to the players when
                  a pair is unseen. Doubles chemistry is either real and this wins, or it
                  is not and this loses to bt.
  stack           logistic regression over the others' outputs plus TruVolley and a few
                  cheap covariates. Fit on the same mask, so it gets no extra information,
                  only permission to disagree about how to combine what is there.
  ens             a plain average of the strongest few, as a check on whether the stacker's
                  extra machinery earns anything over arithmetic.

Nothing here uses numpy beyond arrays and arithmetic; there is no sklearn in this
environment, so the logistic regressions are hand-rolled with Adam.
"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


# --------------------------------------------------------------------------- helpers
def _teams(r, d, m):
    return (0.5 * (r[d["a1"][m]] + r[d["a2"][m]]),
            0.5 * (r[d["b1"][m]] + r[d["b2"][m]]))


def _sig(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -40, 40)))


def _adam(grad_fn, x0, iters=600, lr=0.25):
    x = x0.copy()
    mom = np.zeros_like(x)
    vel = np.zeros_like(x)
    for t in range(1, iters + 1):
        g = grad_fn(x)
        mom = 0.9 * mom + 0.1 * g
        vel = 0.999 * vel + 0.001 * g * g
        x -= lr * (mom / (1 - 0.9 ** t)) / (np.sqrt(vel / (1 - 0.999 ** t)) + 1e-8)
    return x


def _stack_rows(d, fin, mask, halflife, finw=4.0):
    """Training rows: real matches under `mask`, plus finish pairs from the same period.

    The finish rows have to be cut to the fitting window too. They carry no `train` flag of
    their own, and a standing from an event inside the validation period would tell the
    model who was winning there -- the same leak as training on the holdout, arriving
    through a side door.
    """
    a1, a2 = [d["a1"][mask]], [d["a2"][mask]]
    b1, b2 = [d["b1"][mask]], [d["b2"][mask]]
    y = [d["y"][mask]]
    w = [0.5 ** (d["age"][mask] / halflife) if halflife else np.ones(int(mask.sum()))]
    if fin is not None:
        keep = fin["age"] >= d["age"][mask].min()
        a1.append(fin["a1"][keep]); a2.append(fin["a2"][keep])
        b1.append(fin["b1"][keep]); b2.append(fin["b2"][keep])
        y.append(fin["y"][keep])
        fw = fin["w"][keep] * (0.5 ** (fin["age"][keep] / halflife) if halflife else 1.0)
        w.append(finw * fw)
    return (np.concatenate(a1), np.concatenate(a2), np.concatenate(b1),
            np.concatenate(b2), np.concatenate(y), np.concatenate(w))


def _bt_fit(n, d, fin, mask, halflife=365, ridge=0.25, scale=1.0, wpow=0.0, iters=600,
            finw=4.0):
    """Weighted Bradley-Terry. wpow > 0 scales a match's weight by its point margin."""
    a1, a2, b1, b2, y, w = _stack_rows(d, fin, mask, halflife, finw)
    if wpow:
        pd = np.concatenate([np.abs(d["pd"][mask]), np.zeros(len(y) - int(mask.sum()))])
        w = w * (1.0 + wpow * np.minimum(pd, 30.0) / 10.0)

    def grad(r):
        z = (0.5 * (r[a1] + r[a2]) - 0.5 * (r[b1] + r[b2])) / scale
        coef = w * (_sig(z) - y) / scale
        g = np.zeros(n)
        np.add.at(g, a1, coef * 0.5)
        np.add.at(g, a2, coef * 0.5)
        np.add.at(g, b1, -coef * 0.5)
        np.add.at(g, b2, -coef * 0.5)
        return g + ridge * r

    return _adam(grad, np.zeros(n), iters=iters)


CAL_DAYS = 90


def _calibrate(diff, y):
    """Best single divisor turning a rating gap into a probability.

    Must be handed predictions the ratings were not fit on. On the fitting data the gaps
    are exaggerated by exactly however much the model overfit, so this picks too small a
    divisor and the model goes out into the world overconfident -- and it does so in
    proportion to how hard the model memorises, which silently favours the online models
    over the batch ones in any comparison that gets this wrong.
    """
    best = (None, 1.0)
    for s in np.arange(0.05, 4.01, 0.05):
        p = np.clip(_sig(diff / s), 1e-6, 1 - 1e-6)
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        if best[0] is None or ll < best[0]:
            best = (ll, s)
    return best[1]


def _cal_split(d, fit):
    """Split a fitting mask into an inner fit and a held-out slice for the divisor."""
    edge = d["age"][fit].min() + CAL_DAYS
    return fit & (d["age"] > edge), fit & (d["age"] <= edge)


def _predict(r, d, mask, s):
    ta, tb = _teams(r, d, mask)
    return _sig((ta - tb) / s)


# --------------------------------------------------------------------------- models
def bt(n, d, fin, fit, ev, halflife=365, ridge=0.25, wpow=0.0, finw=4.0):
    inner, cal = _cal_split(d, fit)
    ri = _bt_fit(n, d, fin, inner, halflife=halflife, ridge=ridge, wpow=wpow, finw=finw)
    ca, cb = _teams(ri, d, cal)
    s = _calibrate(ca - cb, d["y"][cal])
    r = _bt_fit(n, d, fin, fit, halflife=halflife, ridge=ridge, wpow=wpow, finw=finw)
    return _predict(r, d, ev, s)


def bt_fast(n, d, fin, fit, ev):
    return bt(n, d, fin, fit, ev, halflife=120)


def bt_margin(n, d, fin, fit, ev):
    return bt(n, d, fin, fit, ev, wpow=1.0)


def _massey_fit(n, d, fin, mask, halflife=365, ridge=0.5):
    """Least squares on point margin: the rating gap should equal the expected margin."""
    a1, a2, b1, b2, y, w = _stack_rows(d, fin, mask, halflife)
    nreal = int(mask.sum())
    target = np.concatenate([np.clip(d["pd"][mask], -40, 40),
                             np.full(len(y) - nreal, 6.0)])
    w = np.concatenate([w[:nreal], 0.25 * w[nreal:]])

    def grad(r):
        pred = 0.5 * (r[a1] + r[a2]) - 0.5 * (r[b1] + r[b2])
        coef = 2.0 * w * (pred - target)
        g = np.zeros(n)
        np.add.at(g, a1, coef * 0.5)
        np.add.at(g, a2, coef * 0.5)
        np.add.at(g, b1, -coef * 0.5)
        np.add.at(g, b2, -coef * 0.5)
        return g / len(y) * 100.0 + ridge * r

    return _adam(grad, np.zeros(n), iters=600, lr=0.5)


def massey(n, d, fin, fit, ev, halflife=365, ridge=0.5):
    """Fit against the actual score rather than the winner.

    That uses information the logistic model discards outright. The finish rows carry no
    margin and are given a nominal one, weighted down, so they still order teams without
    inventing a score for a match that was never played.
    """
    inner, cal = _cal_split(d, fit)
    ri = _massey_fit(n, d, fin, inner, halflife, ridge)
    ca, cb = _teams(ri, d, cal)
    s = _calibrate(ca - cb, d["y"][cal])
    r = _massey_fit(n, d, fin, fit, halflife, ridge)
    return _predict(r, d, ev, s)


def _online(n, d, fit, ev, k0=0.10, scale=1.0, glicko=False, k_floor=0.02, n0=25.0,
            revert=0.0):
    """One sequential pass in date order. Ratings at evaluation time are what they are.

    An online model needs no separate calibration slice: at the moment it predicts match i
    it has only seen matches before i, so its own pass is already out of sample. Sweeping
    up those running predictions gives an honest divisor for free, and is the same
    protocol the batch models pay an extra fit for.
    """
    r = np.zeros(n)
    seen = np.zeros(n)
    idx = np.flatnonzero(fit)
    a1, a2, b1, b2, y = d["a1"], d["a2"], d["b1"], d["b2"], d["y"]
    run_diff, run_y = [], []
    for i in idx:
        p1, p2, q1, q2 = a1[i], a2[i], b1[i], b2[i]
        ta = 0.5 * (r[p1] + r[p2])
        tb = 0.5 * (r[q1] + r[q2])
        e = 1.0 / (1.0 + np.exp(-np.clip((ta - tb) / scale, -40, 40)))
        err = y[i] - e
        if seen[p1] and seen[p2] and seen[q1] and seen[q2]:
            run_diff.append(ta - tb)      # a genuine forecast: made before the result
            run_y.append(y[i])
        for p, sgn in ((p1, 1), (p2, 1), (q1, -1), (q2, -1)):
            k = k0
            if glicko:
                k = max(k_floor, k0 * n0 / (n0 + seen[p]))
            r[p] += sgn * k * err
            if revert:
                r[p] *= (1.0 - revert)
            seen[p] += 1
    if len(run_y) > 2000:
        s = _calibrate(np.array(run_diff), np.array(run_y))
    else:
        ta, tb = _teams(r, d, fit)
        s = _calibrate(ta - tb, d["y"][fit])
    return _predict(r, d, ev, s)


def elo(n, d, fin, fit, ev):
    return _online(n, d, fit, ev, k0=0.10, glicko=False)


def glicko(n, d, fin, fit, ev):
    return _online(n, d, fit, ev, k0=0.60, glicko=True, n0=25.0, k_floor=0.03)


def pair(n, d, fin, fit, ev, halflife=365, ridge=0.5, minpair=6):
    """Rate the partnership, fall back to the players' own ratings when it is unseen."""
    key_fit = np.stack([np.minimum(d["a1"], d["a2"]), np.maximum(d["a1"], d["a2"])], 1)
    key_b = np.stack([np.minimum(d["b1"], d["b2"]), np.maximum(d["b1"], d["b2"])], 1)
    allk = np.concatenate([key_fit[fit], key_b[fit]])
    uniq, inv, cnt = np.unique(allk, axis=0, return_inverse=True, return_counts=True)
    lut = {(int(u[0]), int(u[1])): i for i, u in enumerate(uniq)}
    npair = len(uniq)

    base = _bt_fit(n, d, fin, fit, halflife=halflife)
    ia = np.array([lut.get((int(x), int(y)), -1) for x, y in key_fit[fit]])
    ib = np.array([lut.get((int(x), int(y)), -1) for x, y in key_b[fit]])
    ok = (ia >= 0) & (ib >= 0)
    y = d["y"][fit][ok]
    w = (0.5 ** (d["age"][fit][ok] / halflife)) if halflife else np.ones(ok.sum())
    ia, ib = ia[ok], ib[ok]
    prior = np.zeros(npair)
    for (x, yy), i in lut.items():
        prior[i] = 0.5 * (base[x] + base[yy])

    def grad(v):
        z = (v[ia] + prior[ia]) - (v[ib] + prior[ib])
        coef = w * (_sig(z) - y)
        g = np.zeros(npair)
        np.add.at(g, ia, coef)
        np.add.at(g, ib, -coef)
        return g + ridge * v

    off = _adam(grad, np.zeros(npair), iters=400, lr=0.2)
    thin = cnt < minpair                       # a pair seen twice has no chemistry to learn
    off[thin[:npair]] = 0.0

    def team_val(k1, k2, m):
        kk = np.stack([np.minimum(k1[m], k2[m]), np.maximum(k1[m], k2[m])], 1)
        base_v = 0.5 * (base[k1[m]] + base[k2[m]])
        add = np.array([off[lut[(int(x), int(yy))]] if (int(x), int(yy)) in lut else 0.0
                        for x, yy in kk])
        return base_v + add

    _, cal = _cal_split(d, fit)
    ca, cb = team_val(d["a1"], d["a2"], cal), team_val(d["b1"], d["b2"], cal)
    s = _calibrate(ca - cb, d["y"][cal])
    ea, eb = team_val(d["a1"], d["a2"], ev), team_val(d["b1"], d["b2"], ev)
    return _sig((ea - eb) / s)


def _covariates(n, d, fit, ev):
    """Cheap per-player facts a rating throws away: experience and time since last seen."""
    cnt = np.zeros(n)
    last = np.full(n, 9999.0)
    for k in ("a1", "a2", "b1", "b2"):
        np.add.at(cnt, d[k][fit], 1.0)
        np.minimum.at(last, d[k][fit], d["age"][fit])

    def cols(m):
        ca = cnt[d["a1"][m]] + cnt[d["a2"][m]]
        cb = cnt[d["b1"][m]] + cnt[d["b2"][m]]
        la = np.minimum(last[d["a1"][m]], last[d["a2"][m]])
        lb = np.minimum(last[d["b1"][m]], last[d["b2"][m]])
        return np.stack([
            np.log1p(ca) - np.log1p(cb),
            np.clip(la, 0, 1200) / 365.0 - np.clip(lb, 0, 1200) / 365.0,
        ], 1)

    return cols(fit), cols(ev)


BASE_FOR_STACK = ("bt", "bt_fast", "massey", "elo", "glicko")


def _base_logits(n, d, fin, fit, ev):
    """Each base model's logit on both the fitting rows and the evaluation rows.

    The base models are fit on `fit` and then asked about `fit` as well, which flatters
    them there -- so the stacker's weights are learned partly on in-sample predictions.
    That biases it toward the models that memorise best, and is the honest reason to also
    report `ens`, a fixed average that cannot be gamed this way.
    """
    out_fit, out_ev = [], []
    for name in BASE_FOR_STACK:
        fn = MODELS[name]
        pf = fn(n, d, fin, fit, fit)
        pe = fn(n, d, fin, fit, ev)
        out_fit.append(np.log(np.clip(pf, 1e-6, 1 - 1e-6) /
                              np.clip(1 - pf, 1e-6, 1 - 1e-6)))
        out_ev.append(np.log(np.clip(pe, 1e-6, 1 - 1e-6) /
                             np.clip(1 - pe, 1e-6, 1 - 1e-6)))
    return np.stack(out_fit, 1), np.stack(out_ev, 1)


def stack(n, d, fin, fit, ev):
    Xf, Xe = _base_logits(n, d, fin, fit, ev)
    cf, ce = _covariates(n, d, fit, ev)
    Xf = np.hstack([np.ones((len(Xf), 1)), Xf, cf])
    Xe = np.hstack([np.ones((len(Xe), 1)), Xe, ce])
    y = d["y"][fit]
    lam = 1e-3 * len(y)

    def grad(b):
        p = _sig(Xf @ b)
        return Xf.T @ (p - y) + lam * np.concatenate([[0.0], b[1:]])

    b = _adam(grad, np.zeros(Xf.shape[1]), iters=900, lr=0.05)
    return _sig(Xe @ b)


def ens(n, d, fin, fit, ev):
    ps = [MODELS[k](n, d, fin, fit, ev) for k in ("bt", "massey", "glicko")]
    lg = [np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1 - 1e-6)) for p in ps]
    return _sig(np.mean(lg, axis=0))


MODELS = {
    "bt": bt,
    "bt_fast": bt_fast,
    "bt_margin": bt_margin,
    "massey": massey,
    "elo": elo,
    "glicko": glicko,
    "pair": pair,
    "stack": stack,
    "ens": ens,
}
