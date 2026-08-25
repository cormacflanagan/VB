"""What does TruVolley reward that this fit does not? Regress the disagreement.

  python3 scripts/disagree.py [player-id-or-name]

Both ratings live on the same scale after the quantile map, so the difference between them
is directly interpretable: positive means TruVolley rates a player above this fit. Averaged
over the cohort that difference is zero by construction. The question is what predicts it
for an individual.

Rather than assert the usual explanation -- TruVolley moves when your *team* wins, so a
strong partner lifts you -- this fits the difference against measurable properties of a
player's record and reports which ones actually carry it. Each feature is standardised, so
a coefficient is the shift in rating points associated with being one standard deviation
high on that feature, holding the rest fixed.

Passing a player prints where she sits on every feature and multiplies it out, so the gap
between her two numbers is accounted for term by term instead of hand-waved.
"""
import json, os, sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
MIN_N = 40
STRONG = 7.5

FEATURES = [
    ("partner", "mean partner rating"),
    ("bestptnr", "best partner rating"),
    ("opp", "mean opponent rating"),
    ("winpct", "win percentage"),
    ("matches", "matches played"),
    ("strongshare", "share of matches vs 7.5+"),
    ("recency", "mean match date, days ago"),
    ("events", "tournaments entered"),
]


def population():
    pop = {int(k): v for k, v in json.load(open(os.path.join(DATA, "cohort2027.json"))).items()}
    al = json.load(open(os.path.join(DATA, "aliases.json")))["alias"]
    for p in al:
        pop.pop(int(p), None)
    return pop, {int(k): int(v) for k, v in al.items()}


def gather(rt, al, want):
    acc = {p: {"w": 0, "l": 0, "opp": 0.0, "ptn": 0.0, "best": 0.0, "n": 0, "np": 0,
               "strong": 0, "days": 0.0, "ev": set()} for p in want}
    import datetime
    today = datetime.date.today().toordinal()
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        a = [al.get(p, p) for p in m["a"]]
        b = [al.get(p, p) for p in m["b"]]
        try:
            age = today - datetime.date.fromisoformat(m["date"]).toordinal()
        except (ValueError, TypeError):
            continue
        if age < 0 or age > 1095:
            continue
        for side, other, won in ((a, b, m["aWon"]), (b, a, not m["aWon"])):
            hit = [p for p in side if p in acc]
            if not hit:
                continue
            rs = [rt[str(o)]["r"] for o in other if str(o) in rt]
            if not rs:
                continue
            s = sum(rs) / len(rs)
            for p in hit:
                e = acc[p]
                e["w" if won else "l"] += 1
                e["opp"] += s
                e["n"] += 1
                e["days"] += age
                e["ev"].add((m.get("src"), m.get("tid")))
                if s >= STRONG:
                    e["strong"] += 1
                for q in side:
                    if q != p and str(q) in rt:
                        e["ptn"] += rt[str(q)]["r"]
                        e["np"] += 1
                        e["best"] = max(e["best"], rt[str(q)]["r"])
    return acc


def features(e):
    n = max(e["n"], 1)
    return {"partner": e["ptn"] / max(e["np"], 1), "bestptnr": e["best"],
            "opp": e["opp"] / n, "winpct": e["w"] / max(e["w"] + e["l"], 1),
            "matches": n, "strongshare": e["strong"] / n,
            "recency": e["days"] / n, "events": len(e["ev"])}


def main(argv):
    rt = json.load(open(os.path.join(DATA, "rating_se.json")))["ratings"]
    pop, al = population()
    want = {p for p, v in pop.items()
            if str(p) in rt and rt[str(p)]["n"] >= MIN_N and v.get("tv")}
    print(f"{len(want):,} cohort players with both ratings and {MIN_N}+ observations")
    acc = gather(rt, al, want)

    ids = [p for p in sorted(want) if acc[p]["n"] >= 20]
    F = np.array([[features(acc[p])[k] for k, _ in FEATURES] for p in ids], float)
    tv = np.array([pop[p]["tv"] for p in ids])
    mine = np.array([rt[str(p)]["r"] for p in ids])
    delta = tv - mine

    mu, sd = F.mean(0), F.std(0)
    sd[sd == 0] = 1
    Z = (F - mu) / sd
    X = np.hstack([np.ones((len(Z), 1)), Z])
    beta, *_ = np.linalg.lstsq(X, delta, rcond=None)
    pred = X @ beta
    r2 = 1 - np.var(delta - pred) / np.var(delta)

    print(f"\nTruVolley minus this fit, over {len(ids):,} players: mean {delta.mean():+.3f}, "
          f"sd {delta.std():.3f}")
    print(f"explained by the features below: R^2 = {r2:.2f}\n")
    print(f"  {'FEATURE':>26}{'COEFF':>9}{'MEAN':>10}{'SD':>9}")
    order = np.argsort(-np.abs(beta[1:]))
    for i in order:
        k, lab = FEATURES[i]
        print(f"  {lab:>26}{beta[i + 1]:>+9.3f}{mu[i]:>10.2f}{sd[i]:>9.2f}")
    print(f"  {'intercept':>26}{beta[0]:>+9.3f}")
    print("\n  A positive coefficient means TruVolley rates a player above this fit when she"
          "\n  is high on that feature. Read them together: they are not independent.")

    if len(argv):
        q = argv[0]
        pid = int(q) if q.isdigit() else next(
            (p for p, v in pop.items() if q.lower() in (v.get("name") or "").lower()), None)
        if pid is None or pid not in acc:
            sys.exit(f"no cohort player matching {q!r} with enough matches")
        v, e = pop[pid], acc[pid]
        f = features(e)
        row = np.array([f[k] for k, _ in FEATURES])
        z = (row - mu) / sd
        print(f"\n{v['name']}  ({v.get('grad')}, {v.get('state')})")
        print(f"  TruVolley {v['tv']:.3f}   this fit {rt[str(pid)]['r']:.3f}   "
              f"difference {v['tv'] - rt[str(pid)]['r']:+.3f}")
        print(f"\n  {'FEATURE':>26}{'HER VALUE':>11}{'VS FIELD':>10}{'CONTRIBUTION':>14}")
        contrib = []
        for i, (k, lab) in enumerate(FEATURES):
            c = beta[i + 1] * z[i]
            contrib.append((abs(c), lab, row[i], z[i], c))
        for _, lab, val, zz, c in sorted(contrib, reverse=True):
            print(f"  {lab:>26}{val:>11.2f}{zz:>+10.2f}{c:>+14.3f}")
        print(f"  {'':>26}{'':>11}{'':>10}{'-' * 12:>14}")
        print(f"  {'predicted difference':>26}{'':>11}{'':>10}"
              f"{beta[0] + z @ beta[1:]:>+14.3f}")
        print(f"  {'actual difference':>26}{'':>11}{'':>10}"
              f"{v['tv'] - rt[str(pid)]['r']:>+14.3f}")


if __name__ == "__main__":
    main(sys.argv[1:])
