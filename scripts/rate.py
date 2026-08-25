"""A tweakable doubles rating, fit from match results.

  python3 scripts/rate.py                          # fit with scripts/rating.json
  python3 scripts/rate.py --halflife 240 --pair 0.5
  python3 scripts/rate.py --compare 2028_younger   # leaderboard against TruVolley

TruVolley gives one number per player computed over every format, and a player's rating
moves when her *team* wins. That conflates her with her partner: play a season with an
8.5 and your number rises whether or not you were the reason. This fits an individual
strength to each player directly from match outcomes, so partner quality is a term in the
model rather than something baked into the result.

  P(A beats B) = sigmoid( (strength(A) - strength(B)) / scale )
  strength(team) = alpha * mean(r1, r2) + (1 - alpha) * min(r1, r2)

`alpha` is the knob worth playing with. At 1.0 a team is the average of its players. At
0.0 it is only as strong as its weaker player, which is closer to how beach actually works
-- the weaker passer gets served every ball. Anything between blends the two.

Everything else is in scripts/rating.json and can be overridden on the command line.
Fitting is maximum likelihood with an L2 pull toward the mean, which is what keeps a
player with four matches from ranking first on a fluke; `ridge` sets how hard that pull is.

The holdout is the point of the whole exercise. Matches inside the last `holdout_days` are
withheld from the fit and scored afterwards, so a change to the knobs can be judged on
whether it predicts unseen results better rather than on whether the top of the table
looks agreeable.
"""
import datetime, json, math, os, sys, time
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CONF = os.path.join(HERE, "rating.json")
CAL_DAYS = 90   # slice reserved for choosing the prediction scale, never fit on

DEFAULTS = {
    "halflife_days": 365,     # a result this old counts half as much as one today
    "window_days": 1095,      # ignore anything older than this
    "scale": 1.0,             # logits per rating point
    "ridge": 2.0,             # L2 pull toward the mean; higher = more shrinkage
    "curve": 0.0,             # how much steeper a big gap is than a linear scale says
    "margin_weight": 0.0,     # how much more a blowout counts than a squeaker
    "pair_alpha": 1.0,        # 1 = team is the mean of its players, 0 = the weaker one
    "unit": "match",          # "match" or "set": sets give a crude margin of victory
    "pool_weight": 1.0,       # pool play relative to bracket
    "finish_weight": 0.0,     # weight on placings where no matches exist
    "iters": 600,
    "lr": 0.25,
    "min_matches": 8,         # reporting threshold, not a fitting one
    "holdout_days": 90,
    "asof": None,             # None = today
}


def conf(argv):
    c = dict(DEFAULTS)
    if os.path.exists(CONF):
        c.update(json.load(open(CONF)))
    alias = {"--halflife": "halflife_days", "--pair": "pair_alpha", "--ridge": "ridge",
             "--curve": "curve", "--margin": "margin_weight",
             "--scale": "scale", "--unit": "unit", "--window": "window_days",
             "--finish": "finish_weight", "--holdout": "holdout_days", "--iters": "iters", "--min": "min_matches"}
    for a, key in alias.items():
        if a in argv:
            v = argv[argv.index(a) + 1]
            c[key] = v if key == "unit" else float(v)
    return c


def load(c, quiet=False):
    """Match rows and, optionally, standings rows -> arrays keyed by a shared index.

    The index is the union of both sources: a player whose only record is a CBVA-style
    event with no match data still needs a slot, or the standings that mention her are
    silently discarded and the blind spot survives the fix.
    """
    say = (lambda *a, **k: None) if quiet else print
    # the merged corpus if it is there, else the original single-source file
    path = os.path.join(DATA, "all_matches.jsonl")
    if not (os.path.exists(path) or os.path.exists(path + ".gz")):
        path = os.path.join(DATA, "matches.jsonl")
    # date.fromisoformat, not time.strptime: scripts/calendar.py shadows the stdlib
    # calendar module on this path and strptime imports it
    asof = c["asof"] or datetime.date.today().isoformat()
    t_asof = datetime.date.fromisoformat(asof).toordinal()

    def age_of(day):
        try:
            return t_asof - datetime.date.fromisoformat(day).toordinal()
        except ValueError:
            return None

    al = aliases()
    rows, old, future = [], 0, 0
    if True:
        for m in read_jsonl(path):
            if len(m["a"]) != 2 or len(m["b"]) != 2 or not m["date"]:
                continue
            if al:
                m["a"] = [al.get(p, p) for p in m["a"]]
                m["b"] = [al.get(p, p) for p in m["b"]]
                if set(m["a"]) & set(m["b"]) or len(set(m["a"])) < 2:
                    continue      # a merge that turns a match into one against herself
            age = age_of(m["date"])
            if age is None:
                continue
            if age < 0:
                future += 1              # the feed carries a few rows dated years ahead
                continue
            if c["window_days"] and age > c["window_days"]:
                old += 1
                continue
            rows.append((m, age))
    say(f"{len(rows)} matches inside the window "
        f"({old} older than {c['window_days']} days, {future} dated in the future)")

    placings = standings(c, age_of)
    if not rows and not placings:
        sys.exit("nothing inside the window -- widen --window")

    ids = sorted({p for m, _ in rows for p in m["a"] + m["b"]}
                 | {p for hi, lo, *_ in placings for p in hi + lo})
    ix = {p: i for i, p in enumerate(ids)}

    A1, A2, B1, B2, Y, W, AGE, CL = [], [], [], [], [], [], [], []
    for m, age in rows:
        decay = 0.5 ** (age / c["halflife_days"]) if c["halflife_days"] else 1.0
        base = decay * (c["pool_weight"] if (m.get("phase") or "").lower() == "pool" else 1.0)
        # Every match in this corpus carries set scores and nothing used them until now:
        # a 21-19 and a 21-6 were the same row. A decisive win is stronger evidence, so it
        # is given proportionally more weight. Capped, because a forfeit or a retirement
        # produces a margin that says nothing about who is better. Applied here rather than
        # below because `obs` copies `base` as it is built.
        mw = c.get("margin_weight") or 0.0
        if mw:
            pd = abs(sum((st[0] - st[1]) for st in (m["sets"] or []) if len(st) == 2))
            base = base * (1.0 + mw * min(pd, 30.0) / 10.0)
        # a set-level unit turns a 2-1 into two wins and a loss, which is the cheapest
        # honest way to let margin of victory matter at all
        obs = []
        if c["unit"] == "set" and m["sets"]:
            for st in m["sets"]:
                if st[0] != st[1]:
                    obs.append((1.0 if st[0] > st[1] else 0.0, base))
        if not obs:
            obs = [(1.0 if m["aWon"] else 0.0, base)]
        for y, w in obs:
            A1.append(ix[m["a"][0]]); A2.append(ix[m["a"][1]])
            B1.append(ix[m["b"][0]]); B2.append(ix[m["b"][1]])
            Y.append(y); W.append(w); AGE.append(age)
            # namespaced: the three feeds mint division ids independently, and CBVA's
            # are strings like "7919:1", so a bare tdId is neither unique nor an int
            CL.append(f'{m.get("src", "?")}:{m.get("tdId", "")}:{m.get("tid", "")}')
    nmatch = len(Y)

    for hi, lo, w, age, cl in placings:
        A1.append(ix[hi[0]]); A2.append(ix[hi[1]])
        B1.append(ix[lo[0]]); B2.append(ix[lo[1]])
        Y.append(1.0); W.append(w); AGE.append(age); CL.append(cl)
    if placings:
        say(f"  + {len(placings)} pairwise observations from standings at events with no "
            f"match data (finish_weight {c['finish_weight']})")

    d = dict(a1=np.array(A1), a2=np.array(A2), b1=np.array(B1), b2=np.array(B2),
             y=np.array(Y, float), w=np.array(W, float), age=np.array(AGE, float),
             # the tournament-division each observation came from. Six pool results out of
             # one draw are not six independent facts, so anything resampling this corpus
             # has to resample whole divisions -- see scripts/uncertainty.py
             cluster=np.array(CL))
    d["train"] = d["age"] > c["holdout_days"]
    # the holdout is scored on real matches only: a placing is weaker evidence and
    # including it would grade the model against its own softer target
    d["real"] = np.arange(len(d["y"])) < nmatch
    say(f"  {len(d['y'])} observations ({c['unit']} level), {len(ids)} players; "
        f"{int(d['train'].sum())} train / {int((~d['train'] & d['real']).sum())} holdout")
    return ids, ix, d


def aliases():
    """Second accounts -> the account that keeps the career. See scripts/dedupe.py.

    Applied at load rather than baked into the corpus, so the merged files stay a faithful
    record of what the three sites actually published and the mapping is one file that can
    be inspected, edited or deleted without recrawling anything.
    """
    p = os.path.join(DATA, "aliases.json")
    if not os.path.exists(p):
        return {}
    return {int(k): int(v) for k, v in json.load(open(p))["alias"].items()}


def standings(c, age_of):
    """Final placings as pairwise observations, for the events with no match data.

    Forty-four percent of tournaments here publish only a finish order -- CBVA's whole
    calendar among them. Ignoring those makes a player who wins local adult draws look
    weak for a reason that has nothing to do with her.

    A division of n teams gives every non-tied pair, each weighted finish_weight/(n-1) so
    one standing carries about the same total evidence as one match rather than n times
    it. Shared finishes -- the blocks of 5th and 9th that beach draws produce -- say
    nothing about who was better and are skipped.
    """
    path = os.path.join(DATA, "all_finishes.jsonl")
    if not (os.path.exists(path) or os.path.exists(path + ".gz")):
        path = os.path.join(DATA, "finishes.jsonl")
    if not c.get("finish_weight") or not (os.path.exists(path)
                                          or os.path.exists(path + ".gz")):
        return []
    al = aliases()
    out = []
    if True:
        for r in read_jsonl(path):
            if not r["date"]:
                continue
            age = age_of(r["date"])
            if age is None or age < 0 or (c["window_days"] and age > c["window_days"]):
                continue
            teams = r["teams"]
            if al:
                teams = [[pl, [al.get(p, p) for p in tm]] for pl, tm in teams]
            if len(teams) < 3:
                continue
            decay = 0.5 ** (age / c["halflife_days"]) if c["halflife_days"] else 1.0
            w = c["finish_weight"] * decay / (len(teams) - 1)
            for i in range(len(teams)):
                for j in range(i + 1, len(teams)):
                    if teams[i][0] == teams[j][0]:
                        continue
                    out.append((teams[i][1], teams[j][1], w, age,
                                f'fin:{r.get("tdId", "")}:{r.get("tid", "")}'))
    return out


def link(diff, c):
    """Rating gap -> logit, allowing the scale to steepen as the gap widens.

    A plain Bradley-Terry model puts the logit proportional to the rating difference, which
    assumes one point of rating buys the same edge everywhere on the scale. Held-out
    matches say it does not. Teams playing far above their usual level lose considerably
    more often than a linear scale predicts -- the error runs from -0.3% where the step up
    is small to -6.2% in the top quintile of step-ups, monotonically, over eighteen
    thousand matches (scripts/extrapolation.py).

    That flatness does not merely mispredict; it distorts the fit. If the model needs a
    bigger gap than reality to explain an 88% win rate, then anyone whose whole record is a
    high win rate over weaker opposition gets the bigger gap -- her rating inflates to
    cover for the link. The inflation lands exactly on players never tested near their own
    level, which is what made a 100-14 record against a mean opponent of 5.56 come out
    twelfth in a national cohort.

    So: diff * (1 + curve*|diff|). Quadratic in the tail, and deliberately still linear at
    the origin -- a power law would flatten the gradient to zero for evenly matched teams,
    discarding the most informative matches in the corpus to fix the least informative
    ones. curve = 0 is the plain model.
    """
    k = c.get("curve") or 0.0
    return diff if not k else diff * (1.0 + k * np.abs(diff))


def dlink(diff, c):
    """d link / d diff, for the chain rule in fit()."""
    k = c.get("curve") or 0.0
    return 1.0 if not k else 1.0 + 2.0 * k * np.abs(diff)


def team(r, i, j, alpha):
    ri, rj = r[i], r[j]
    return alpha * 0.5 * (ri + rj) + (1 - alpha) * np.minimum(ri, rj)


def team_grad(r, i, j, alpha, g, coef):
    """Scatter dTeam/dr back onto the two players."""
    np.add.at(g, i, coef * alpha * 0.5)
    np.add.at(g, j, coef * alpha * 0.5)
    if alpha < 1.0:
        lo_i = r[i] <= r[j]
        np.add.at(g, i[lo_i], coef[lo_i] * (1 - alpha))
        np.add.at(g, j[~lo_i], coef[~lo_i] * (1 - alpha))


def fit(n, d, c, mask=None, quiet=False):
    m = d["train"] if mask is None else mask
    a1, a2, b1, b2 = d["a1"][m], d["a2"][m], d["b1"][m], d["b2"][m]
    y, w = d["y"][m], d["w"][m]
    alpha, s, lam = c["pair_alpha"], c["scale"], c["ridge"]
    r = np.zeros(n)
    mom = np.zeros(n)
    vel = np.zeros(n)
    lr, b1m, b2m, eps = c["lr"], 0.9, 0.999, 1e-8
    for t in range(1, int(c["iters"]) + 1):
        diff = team(r, a1, a2, alpha) - team(r, b1, b2, alpha)
        z = link(diff, c) / s
        p = 1.0 / (1.0 + np.exp(-z))
        coef = w * (p - y) * dlink(diff, c) / s      # dLoss/dz . dz/ddiff
        g = np.zeros(n)
        team_grad(r, a1, a2, alpha, g, coef)
        team_grad(r, b1, b2, alpha, g, -coef)
        g += lam * r
        mom = b1m * mom + (1 - b1m) * g
        vel = b2m * vel + (1 - b2m) * g * g
        r -= lr * (mom / (1 - b1m ** t)) / (np.sqrt(vel / (1 - b2m ** t)) + eps)
        if t % 200 == 0 and not quiet:
            ll = -np.sum(w * (y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)))
            print(f"    iter {t:>4}  weighted log-loss {ll / w.sum():.4f}", flush=True)
    return r


def calibrate(r, d, c, mask):
    """The divisor turning a fitted rating gap into a probability.

    Kept separate from the `scale` used during fitting, because the two do different jobs
    and the right value for one is not the right value for the other. Ridge shrinkage
    compresses every rating toward the mean, so a model fit under a heavy ridge produces
    small gaps that a fixed divisor reads as near-coin-flips -- correct ordering, badly
    under-confident probabilities. Fitting the divisor afterwards restores the confidence
    without touching the ratings or their order.

    The mask handed in must be data the ratings were NOT fit on. Calibrating on the fitting
    data does active harm: in-sample rating gaps are exaggerated by exactly the amount the
    model overfit, so the search reads them as well separated and picks a small divisor,
    which then produces overconfident predictions on everything else. Measured here, that
    mistake cost 0.04 of log-loss -- worse than leaving the divisor at 1.0 and not
    calibrating at all, and worse for a heavily-fit model than a lightly-fit one, which
    would quietly rig any comparison between them.
    """
    a1, a2, b1, b2 = d["a1"][mask], d["a2"][mask], d["b1"][mask], d["b2"][mask]
    y = d["y"][mask]
    diff = link(team(r, a1, a2, c["pair_alpha"]) - team(r, b1, b2, c["pair_alpha"]), c)
    best = (None, c["scale"])
    for s in np.arange(0.05, 4.01, 0.025):
        p = np.clip(1.0 / (1.0 + np.exp(-diff / s)), 1e-9, 1 - 1e-9)
        ll = -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
        if best[0] is None or ll < best[0]:
            best = (ll, float(s))
    return best[1]


def score(r, d, c, mask, scale=None):
    a1, a2, b1, b2 = d["a1"][mask], d["a2"][mask], d["b1"][mask], d["b2"][mask]
    y = d["y"][mask]
    diff = team(r, a1, a2, c["pair_alpha"]) - team(r, b1, b2, c["pair_alpha"])
    p = 1.0 / (1.0 + np.exp(-link(diff, c) / (scale or c["scale"])))
    ll = -np.mean(y * np.log(p + 1e-9) + (1 - y) * np.log(1 - p + 1e-9))
    acc = np.mean((p > 0.5) == (y > 0.5))
    brier = np.mean((p - y) ** 2)
    return ll, acc, brier


def versus_truvolley(ids, ix, d, r, c, r_all=None, scale=None):
    """Score this rating against TruVolley on the same held-out matches.

    Restricted to matches where all four players carry a TruVolley, so the two are judged
    on identical rows. TruVolley publishes no scale in logits, so it is given its best
    one: a search for the divisor minimising its own log-loss, which can only flatter it.
    """
    meta = names()
    tv = np.full(len(ids), np.nan)
    for i, p in enumerate(ids):
        v = (meta.get(p) or (None, None, None))[2]
        if v:
            tv[i] = v
    ok = ~d["train"] & d["real"]
    for k in ("a1", "a2", "b1", "b2"):
        ok = ok & ~np.isnan(tv[d[k]])
    if ok.sum() < 200:
        return
    y = d["y"][ok]
    diff = (team(tv, d["a1"][ok], d["a2"][ok], 1.0)
            - team(tv, d["b1"][ok], d["b2"][ok], 1.0))
    # TruVolley gets the same curved link and its best setting of both knobs, so the
    # comparison is not won by giving this fit a functional form the other side lacks
    best = None
    for k_tv in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4):
        eff = diff * (1.0 + k_tv * np.abs(diff))
        for s_tv in np.arange(0.1, 3.01, 0.02):
            q = 1.0 / (1.0 + np.exp(-eff / s_tv))
            ll = -np.mean(y * np.log(q + 1e-9) + (1 - y) * np.log(1 - q + 1e-9))
            if best is None or ll < best[0]:
                best = (ll, s_tv, np.mean((q > 0.5) == (y > 0.5)),
                        np.mean((q - y) ** 2), k_tv)
    mine = score(r, d, c, ok, scale=scale)
    seen = score(r_all, d, c, ok, scale=scale) if r_all is not None else None
    print("")
    print(f"head to head on {int(ok.sum())} held-out matches where both rate all four:")
    print(f"  {'':10}{'LOG-LOSS':>10}{'ACCURACY':>10}{'BRIER':>9}")
    print(f"  {'TruVolley':10}{best[0]:>10.4f}{best[2]:>10.3f}{best[3]:>9.4f}"
          f"   (at its own best scale {best[1]:.2f}, curve {best[4]:g})")
    print(f"  {'this fit':10}{mine[0]:>10.4f}{mine[1]:>10.3f}{mine[2]:>9.4f}")
    print(f"  {'gain':10}{best[0] - mine[0]:>+10.4f}{mine[1] - best[2]:>+10.3f}"
          f"{best[3] - mine[2]:>+9.4f}")
    print("  TruVolley is quoted as of today, so it has already absorbed these matches;")
    print("  the fit above has not seen them. The row below removes that advantage by")
    print("  letting this fit see them too, which is a fairness patch, not a forecast.")
    if seen:
        print(f"  {'both seen':10}{seen[0]:>10.4f}{seen[1]:>10.3f}{seen[2]:>9.4f}"
              f"   ({best[0] - seen[0]:+.4f} vs TruVolley)")


def counts(ids, d):
    n = np.zeros(len(ids))
    for k in ("a1", "a2", "b1", "b2"):
        np.add.at(n, d[k], 1)
    return n


def names():
    out = {}
    for f in ("cohort2027.json", "pop2027.json", "pop2028.json"):
        p = os.path.join(DATA, f)
        if os.path.exists(p):
            for k, v in json.load(open(p)).items():
                out[int(k)] = (v["name"], v.get("grad"), v.get("tv"))
    return out


def main(argv):
    c = conf(argv)
    print("config:", json.dumps({k: c[k] for k in
                                 ("halflife_days", "window_days", "scale", "ridge",
                                  "curve", "pair_alpha", "unit", "holdout_days")}))
    dest = os.path.join(DATA, argv[argv.index("--out") + 1]) if "--out" in argv \
        else os.path.join(DATA, "rating.json")
    ids, ix, d = load(c)
    n = len(ids)

    print("  fitting on the training window")
    r_tr = fit(n, d, c)
    # A nested split for the prediction scale: fit again on everything older than the
    # calibration slice, then choose the divisor on the slice itself, which that inner fit
    # has never seen. Costs one extra fit and is the difference between a calibration and
    # a second helping of the training error.
    cal_edge = c["holdout_days"] + CAL_DAYS
    inner = d["age"] > cal_edge
    cal = d["train"] & d["real"] & (d["age"] <= cal_edge)
    if cal.sum() > 2000 and inner.sum() > 10000:
        r_in = fit(n, d, c, mask=inner, quiet=True)
        ps = calibrate(r_in, d, c, cal)
        print(f"    prediction scale {ps:.3f} from {int(cal.sum()):,} held-out matches "
              f"(fitting scale {c['scale']})")
    else:
        ps = c["scale"]
        print(f"    prediction scale {ps:.3f} (too little data to calibrate)")
    if (~d["train"] & d["real"]).sum():
        ll, acc, brier = score(r_tr, d, c, ~d["train"] & d["real"], scale=ps)
        base = score(np.zeros(n), d, c, ~d["train"] & d["real"], scale=ps)
        print(f"\nholdout ({int((~d['train'] & d['real']).sum())} obs): log-loss {ll:.4f}  "
              f"accuracy {acc:.3f}  Brier {brier:.4f}"
              f"   [coin-flip baseline {base[0]:.4f} / {base[1]:.3f}]")

    print("\n  refitting on everything")
    r = fit(n, d, c, mask=np.ones(len(d["y"]), bool))
    versus_truvolley(ids, ix, d, r_tr, c, r_all=r, scale=ps)
    nm = counts(ids, d)

    # Put it on TruVolley's scale. A least-squares line was wrong here: fitted with
    # r = 0.77 it regresses toward the mean, so the gap ran -0.42 at TruVolley 5.5 and
    # -0.70 at 8.2 -- strong opponents flattened toward the middle, which understated
    # every strength-of-schedule number computed from it. A quantile map instead: the
    # nth percentile of this rating becomes the nth percentile of TruVolley. It is
    # monotone, so it reorders nobody, and band edges then mean the same on both scales.
    meta = names()
    ref = [(r[i], meta[p][2]) for i, p in enumerate(ids)
           if p in meta and meta[p][2] and nm[i] >= c["min_matches"]]
    if len(ref) > 200:
        X = np.sort(np.array([a for a, _ in ref]))
        Y = np.sort(np.array([b for _, b in ref]))
        q = np.linspace(0, 1, 201)
        kx = np.quantile(X, q)
        ky = np.quantile(Y, q)
        # extend past the reference range with the slope of the outermost decile, so the
        # very top is not clipped flat -- the exact failure being corrected
        lo_s = (ky[20] - ky[0]) / max(kx[20] - kx[0], 1e-9)
        hi_s = (ky[-1] - ky[-21]) / max(kx[-1] - kx[-21], 1e-9)

        def to_tv(v):
            v = np.asarray(v, float)
            out = np.interp(v, kx, ky)
            out = np.where(v < kx[0], ky[0] + (v - kx[0]) * lo_s, out)
            out = np.where(v > kx[-1], ky[-1] + (v - kx[-1]) * hi_s, out)
            return out

        corr = np.corrcoef([a for a, _ in ref], [b for _, b in ref])[0, 1]
        mapped = to_tv(r)
        print(f"\nmapped onto the TruVolley scale by quantile ({len(ref)} players, "
              f"rank correlation r = {corr:.3f})")
        chk = to_tv(np.array([a for a, _ in ref]))
        tvs = np.array([b for _, b in ref])
        for lo, hi in ((7.5, 8.0), (8.0, 8.5), (8.5, 9.5)):
            g = (tvs >= lo) & (tvs < hi)
            if g.sum() > 20:
                print(f"  TruVolley {lo}-{hi}: mean {tvs[g].mean():.2f} -> "
                      f"{chk[g].mean():.2f} (gap {chk[g].mean() - tvs[g].mean():+.2f})")
    else:
        mapped, corr = r, float("nan")
        kx = ky = np.array([])

    out = {str(p): {"r": round(float(mapped[i]), 3),
                    "raw": round(float(r[i]), 4), "n": int(nm[i])}
           for i, p in enumerate(ids)}
    json.dump({"config": c, "map": {"kind": "quantile", "r": corr,
                                    "x": [round(float(v), 4) for v in kx],
                                    "y": [round(float(v), 4) for v in ky]},
               "ratings": out}, open(dest, "w"), indent=1)
    print(f"wrote {os.path.relpath(dest)} ({len(out)} players)")

    grp = argv[argv.index("--compare") + 1] if "--compare" in argv else None
    if grp:
        leaderboard(grp, out, meta, c)


def leaderboard(grp, out, meta, c):
    roster = json.load(open(os.path.join(HERE, f"roster_{grp}.json")))
    rows = []
    for name, pid, _ in roster["roster"]:
        e = out.get(str(pid))
        tv = (meta.get(pid) or (None, None, None))[2]
        if e:
            rows.append((e["r"], name, tv, e["n"], e["r"] - (tv or 0)))
    rows.sort(reverse=True)
    tvrank = {nm: i for i, (nm, _) in enumerate(
        sorted(((r[1], r[2] or 0) for r in rows), key=lambda t: -t[1]), 1)}
    print(f"\n{roster['label']}  ({len(rows)} of {len(roster['roster'])} rated)")
    print(f"  {'#':>3} {'PLAYER':26}{'NEW':>7}{'TV':>7}{'DIFF':>7}{'TVRK':>6}{'MOVE':>6}{'N':>6}")
    for i, (rv, nm, tv, cnt, diff) in enumerate(rows, 1):
        mv = tvrank[nm] - i
        print(f"  {i:>3} {nm[:25]:26}{rv:>7.3f}{(tv or 0):>7.3f}{diff:>+7.3f}"
              f"{tvrank[nm]:>6}{mv:>+6}{cnt:>6}")


if __name__ == "__main__":
    main(sys.argv[1:])
