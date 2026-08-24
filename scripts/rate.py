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

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CONF = os.path.join(HERE, "rating.json")

DEFAULTS = {
    "halflife_days": 365,     # a result this old counts half as much as one today
    "window_days": 1095,      # ignore anything older than this
    "scale": 1.0,             # logits per rating point
    "ridge": 2.0,             # L2 pull toward the mean; higher = more shrinkage
    "pair_alpha": 1.0,        # 1 = team is the mean of its players, 0 = the weaker one
    "unit": "match",          # "match" or "set": sets give a crude margin of victory
    "pool_weight": 1.0,       # pool play relative to bracket
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
             "--scale": "scale", "--unit": "unit", "--window": "window_days",
             "--holdout": "holdout_days", "--iters": "iters", "--min": "min_matches"}
    for a, key in alias.items():
        if a in argv:
            v = argv[argv.index(a) + 1]
            c[key] = v if key == "unit" else float(v)
    return c


def load(c):
    """Match rows -> arrays. Returns (index, a1,a2,b1,b2, y, w, train_mask)."""
    path = os.path.join(DATA, "matches.jsonl")
    # date.fromisoformat rather than time.strptime: scripts/calendar.py shadows the
    # stdlib calendar module on this path, and strptime imports it
    asof = c["asof"] or datetime.date.today().isoformat()
    t_asof = datetime.date.fromisoformat(asof).toordinal()
    rows, old, future = [], 0, 0
    with open(path) as fh:
        for line in fh:
            m = json.loads(line)
            if len(m["a"]) != 2 or len(m["b"]) != 2 or not m["date"]:
                continue
            try:
                age = t_asof - datetime.date.fromisoformat(m["date"]).toordinal()
            except ValueError:
                continue
            if age < 0:
                future += 1          # the feed carries a few rows dated years ahead
                continue
            if c["window_days"] and age > c["window_days"]:
                old += 1
                continue
            rows.append((m, age))
    print(f"{len(rows)} matches inside the window "
          f"({old} older than {c['window_days']} days, {future} dated in the future)")
    if not rows:
        sys.exit("no matches in the window -- widen --window or wait for the dump")

    ids = sorted({p for m, _ in rows for p in m["a"] + m["b"]})
    ix = {p: i for i, p in enumerate(ids)}
    A1, A2, B1, B2, Y, W, AGE = [], [], [], [], [], [], []
    for m, age in rows:
        decay = 0.5 ** (age / c["halflife_days"]) if c["halflife_days"] else 1.0
        base = decay * (c["pool_weight"] if (m.get("phase") or "").lower() == "pool" else 1.0)
        # a set-level unit turns a 2-1 into two wins and a loss, which is the cheapest
        # honest way to let margin of victory matter at all
        obs = []
        if c["unit"] == "set" and m["sets"]:
            for s in m["sets"]:
                if s[0] == s[1]:
                    continue
                obs.append((1.0 if s[0] > s[1] else 0.0, base))
        if not obs:
            obs = [(1.0 if m["aWon"] else 0.0, base)]
        for y, w in obs:
            A1.append(ix[m["a"][0]]); A2.append(ix[m["a"][1]])
            B1.append(ix[m["b"][0]]); B2.append(ix[m["b"][1]])
            Y.append(y); W.append(w); AGE.append(age)
    d = dict(a1=np.array(A1), a2=np.array(A2), b1=np.array(B1), b2=np.array(B2),
             y=np.array(Y, float), w=np.array(W, float), age=np.array(AGE, float))
    d["train"] = d["age"] > c["holdout_days"]
    print(f"  {len(d['y'])} observations ({c['unit']} level), {len(ids)} players; "
          f"{int(d['train'].sum())} train / {int((~d['train']).sum())} holdout")
    return ids, ix, d


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


def fit(n, d, c, mask=None):
    m = d["train"] if mask is None else mask
    a1, a2, b1, b2 = d["a1"][m], d["a2"][m], d["b1"][m], d["b2"][m]
    y, w = d["y"][m], d["w"][m]
    alpha, s, lam = c["pair_alpha"], c["scale"], c["ridge"]
    r = np.zeros(n)
    mom = np.zeros(n)
    vel = np.zeros(n)
    lr, b1m, b2m, eps = c["lr"], 0.9, 0.999, 1e-8
    for t in range(1, int(c["iters"]) + 1):
        z = (team(r, a1, a2, alpha) - team(r, b1, b2, alpha)) / s
        p = 1.0 / (1.0 + np.exp(-z))
        coef = w * (p - y) / s                       # dLoss/dz
        g = np.zeros(n)
        team_grad(r, a1, a2, alpha, g, coef)
        team_grad(r, b1, b2, alpha, g, -coef)
        g += lam * r
        mom = b1m * mom + (1 - b1m) * g
        vel = b2m * vel + (1 - b2m) * g * g
        r -= lr * (mom / (1 - b1m ** t)) / (np.sqrt(vel / (1 - b2m ** t)) + eps)
        if t % 200 == 0:
            ll = -np.sum(w * (y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)))
            print(f"    iter {t:>4}  weighted log-loss {ll / w.sum():.4f}", flush=True)
    return r


def score(r, d, c, mask):
    a1, a2, b1, b2 = d["a1"][mask], d["a2"][mask], d["b1"][mask], d["b2"][mask]
    y = d["y"][mask]
    z = (team(r, a1, a2, c["pair_alpha"]) - team(r, b1, b2, c["pair_alpha"])) / c["scale"]
    p = 1.0 / (1.0 + np.exp(-z))
    ll = -np.mean(y * np.log(p + 1e-9) + (1 - y) * np.log(1 - p + 1e-9))
    acc = np.mean((p > 0.5) == (y > 0.5))
    brier = np.mean((p - y) ** 2)
    return ll, acc, brier


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
                                  "pair_alpha", "unit", "holdout_days")}))
    ids, ix, d = load(c)
    n = len(ids)

    print("  fitting on the training window")
    r_tr = fit(n, d, c)
    if (~d["train"]).sum():
        ll, acc, brier = score(r_tr, d, c, ~d["train"])
        base = score(np.zeros(n), d, c, ~d["train"])
        print(f"\nholdout ({int((~d['train']).sum())} obs): log-loss {ll:.4f}  "
              f"accuracy {acc:.3f}  Brier {brier:.4f}"
              f"   [coin-flip baseline {base[0]:.4f} / {base[1]:.3f}]")

    print("\n  refitting on everything")
    r = fit(n, d, c, mask=np.ones(len(d["y"]), bool))
    nm = counts(ids, d)

    # put it on TruVolley's scale so the two are readable side by side: a least-squares
    # line through the players who have both, which changes the ranking not at all
    meta = names()
    have = [(r[i], meta[p][2]) for i, p in enumerate(ids)
            if p in meta and meta[p][2] and nm[i] >= c["min_matches"]]
    if len(have) > 30:
        X = np.array([h[0] for h in have]); Ytv = np.array([h[1] for h in have])
        slope = np.cov(X, Ytv, bias=True)[0, 1] / X.var()
        icept = Ytv.mean() - slope * X.mean()
        corr = np.corrcoef(X, Ytv)[0, 1]
        print(f"\nmapped onto the TruVolley scale: x{slope:.3f} {icept:+.3f}  "
              f"(r = {corr:.3f} across {len(have)} players)")
    else:
        slope, icept, corr = 1.0, 0.0, float("nan")

    out = {str(p): {"r": round(float(r[i] * slope + icept), 3),
                    "raw": round(float(r[i]), 4), "n": int(nm[i])}
           for i, p in enumerate(ids)}
    json.dump({"config": c, "map": {"slope": slope, "intercept": icept, "r": corr},
               "ratings": out}, open(os.path.join(DATA, "rating.json"), "w"), indent=1)
    print(f"wrote data/rating.json ({len(out)} players)")

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
