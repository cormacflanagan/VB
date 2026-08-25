"""A common harness for comparing prediction algorithms on the same matches.

  python3 scripts/bench.py                 # every model
  python3 scripts/bench.py bt elo massey   # a subset

Every knob in this repository so far has been tuned against a single held-out window, and
the model itself has never been compared against an alternative -- only against different
settings of itself. Those are different questions, and the second one is unanswerable
without a harness that can run several algorithms over identical matches.

The split is by date and three-way, which matters more than it sounds:

    train   everything older than VALID_DAYS
    valid   between TEST_DAYS and VALID_DAYS ago   -- where knobs are chosen
    test    the most recent TEST_DAYS              -- scored once, at the end

A two-way split cannot tell a genuinely better model from one whose knobs were fitted to
the noise in the holdout. With roughly forty thousand validation matches the standard error
of log-loss is about 0.003, so any two settings inside about 0.006 of each other are tied
however confidently the grid prints them -- and a search that makes fifty comparisons at
that resolution will find a spurious winner unless something is kept back. Models are fit
on train, chosen on valid, then refit on train+valid and scored once on test.

Point margin is the signal nothing here has used. Every match in the corpus carries set
scores, and a 21-19 and a 21-6 are the same row to a Bradley-Terry model. Two of the
entrants below exist to find out what that is worth.

Add a model by writing a function that takes the training arrays and returns a predictor,
then registering it in MODELS. Everything else -- splits, scoring, unseen players -- is
handled here so the comparison stays honest.
"""
import datetime, json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "bench.json")

WINDOW_DAYS = 1095
VALID_DAYS = 150
TEST_DAYS = 60


def load(quiet=False):
    """The corpus as flat arrays: players, date, outcome, point margin, division."""
    say = (lambda *a, **k: None) if quiet else print
    al = {}
    p = os.path.join(DATA, "aliases.json")
    if os.path.exists(p):
        al = {int(k): int(v) for k, v in json.load(open(p))["alias"].items()}
    today = datetime.date.today().toordinal()

    A, B, Y, AGE, PD, CL = [], [], [], [], [], []
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        if len(m["a"]) != 2 or len(m["b"]) != 2 or not m["date"]:
            continue
        try:
            age = today - datetime.date.fromisoformat(m["date"]).toordinal()
        except ValueError:
            continue
        if age < 0 or age > WINDOW_DAYS:
            continue
        a = [al.get(x, x) for x in m["a"]]
        b = [al.get(x, x) for x in m["b"]]
        if set(a) & set(b) or len(set(a)) < 2 or len(set(b)) < 2:
            continue
        pd = 0
        for st in (m.get("sets") or []):
            if len(st) == 2:
                pd += st[0] - st[1]
        A.append(a)
        B.append(b)
        Y.append(1.0 if m["aWon"] else 0.0)
        AGE.append(age)
        PD.append(pd)
        CL.append(f'{m.get("src", "?")}:{m.get("tdId", "")}:{m.get("tid", "")}')

    ids = sorted({p for t in A for p in t} | {p for t in B for p in t})
    ix = {p: i for i, p in enumerate(ids)}
    d = dict(
        a1=np.array([ix[t[0]] for t in A]), a2=np.array([ix[t[1]] for t in A]),
        b1=np.array([ix[t[0]] for t in B]), b2=np.array([ix[t[1]] for t in B]),
        y=np.array(Y), age=np.array(AGE, float), pd=np.array(PD, float),
        cluster=np.array(CL))
    order = np.argsort(-d["age"])          # oldest first, for the online models
    for k in ("a1", "a2", "b1", "b2", "y", "age", "pd", "cluster"):
        d[k] = d[k][order]
    d["train"] = d["age"] > VALID_DAYS
    d["valid"] = (d["age"] <= VALID_DAYS) & (d["age"] > TEST_DAYS)
    d["test"] = d["age"] <= TEST_DAYS
    say(f"{len(d['y']):,} matches in a {WINDOW_DAYS}-day window, {len(ids):,} players")
    say(f"  train {int(d['train'].sum()):,}   valid {int(d['valid'].sum()):,}   "
        f"test {int(d['test'].sum()):,}")
    say(f"  log-loss standard error on valid is about "
        f"{0.6 / np.sqrt(max(d['valid'].sum(), 1)):.4f}; treat anything closer as a tie")
    return ids, ix, d


def standings(ix, quiet=False):
    """Finish-order pairs, as extra training evidence only. Never scored."""
    path = os.path.join(DATA, "all_finishes.jsonl")
    if not (os.path.exists(path) or os.path.exists(path + ".gz")):
        return None
    al = {}
    p = os.path.join(DATA, "aliases.json")
    if os.path.exists(p):
        al = {int(k): int(v) for k, v in json.load(open(p))["alias"].items()}
    today = datetime.date.today().toordinal()
    A1, A2, B1, B2, W, AGE = [], [], [], [], [], []
    for r in read_jsonl(path):
        if not r.get("date"):
            continue
        try:
            age = today - datetime.date.fromisoformat(r["date"]).toordinal()
        except ValueError:
            continue
        if age < 0 or age > WINDOW_DAYS:
            continue
        teams = [[pl, [al.get(x, x) for x in tm]] for pl, tm in r["teams"]]
        teams = [t for t in teams if len(set(t[1])) == 2 and all(x in ix for x in t[1])]
        if len(teams) < 3:
            continue
        w = 1.0 / (len(teams) - 1)
        for i in range(len(teams)):
            for j in range(i + 1, len(teams)):
                if teams[i][0] == teams[j][0]:
                    continue
                A1.append(ix[teams[i][1][0]]); A2.append(ix[teams[i][1][1]])
                B1.append(ix[teams[j][1][0]]); B2.append(ix[teams[j][1][1]])
                W.append(w); AGE.append(age)
    if not A1:
        return None
    if not quiet:
        print(f"  + {len(A1):,} pairwise rows from finish orders (training evidence only)")
    return dict(a1=np.array(A1), a2=np.array(A2), b1=np.array(B1), b2=np.array(B2),
                w=np.array(W), age=np.array(AGE, float),
                y=np.ones(len(A1)), pd=np.zeros(len(A1)))


def score(p, y):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return dict(ll=float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
                acc=float(np.mean((p > 0.5) == (y > 0.5))),
                brier=float(np.mean((p - y) ** 2)))


def decay(age, halflife):
    return 0.5 ** (age / halflife) if halflife else np.ones_like(age)


def report(name, v, t, secs):
    print(f"  {name:<26}{v['ll']:>9.4f}{v['acc']:>8.3f}"
          f"{t['ll']:>10.4f}{t['acc']:>8.3f}{t['brier']:>9.4f}{secs:>7.0f}s")


def main(argv):
    from models import MODELS
    pick = [a for a in argv if not a.startswith("-")]
    ids, ix, d = load()
    fin = standings(ix)
    n = len(ids)

    rows = {}
    print(f"\n  {'MODEL':<26}{'VALID LL':>9}{'ACC':>8}{'TEST LL':>10}{'ACC':>8}"
          f"{'BRIER':>9}{'TIME':>8}")
    for name, fn in MODELS.items():
        if pick and name not in pick:
            continue
        t0 = time.time()
        try:
            # chosen on valid, then refit including valid and scored once on test
            pv = fn(n, d, fin, d["train"], d["valid"])
            pt = fn(n, d, fin, d["train"] | d["valid"], d["test"])
        except Exception as e:                       # a broken entrant must not stop the run
            print(f"  {name:<26}failed: {type(e).__name__}: {e}")
            continue
        v = score(pv, d["y"][d["valid"]])
        t = score(pt, d["y"][d["test"]])
        rows[name] = {"valid": v, "test": t, "secs": round(time.time() - t0, 1)}
        report(name, v, t, time.time() - t0)

    if rows:
        best = min(rows.items(), key=lambda kv: kv[1]["test"]["ll"])
        print(f"\n  best on test: {best[0]} at {best[1]['test']['ll']:.4f}")
        json.dump({"validDays": VALID_DAYS, "testDays": TEST_DAYS,
                   "nValid": int(d["valid"].sum()), "nTest": int(d["test"].sum()),
                   "models": rows}, open(OUT, "w"), indent=1)
        print(f"wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
