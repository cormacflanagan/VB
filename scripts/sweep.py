"""Sweep the rating knobs and score each setting on held-out matches.

  python3 scripts/sweep.py            # one knob at a time, then alpha x half-life
  python3 scripts/sweep.py --quick

A rating can always be made to look better by staring at the top of the table until it
agrees with you. The only honest test is whether it predicts results it has not seen, so
every setting here is fit on matches older than `holdout_days` and scored on the ones
inside it. Lower log-loss is better; accuracy is easier to read but blunter, because
getting a 60/40 match right counts the same as a 99/1.

Each fit takes a few seconds, so the grid is run in full rather than sampled.
"""
import itertools, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

GRID = {
    "pair_alpha": [0.0, 0.25, 0.5, 0.75, 1.0],
    "halflife_days": [90, 180, 365, 730, 100000],     # last one is effectively "no decay"
    "ridge": [0.25, 0.5, 1.0, 2.0, 4.0, 8.0],
    "window_days": [365, 730, 1095, 1825],
    "scale": [0.5, 1.0, 2.0],
    "unit": ["match", "set"],
    "pool_weight": [0.5, 1.0],
}


def run(c, cache={}):
    """Fit on the training window and score the holdout. Reloads only when the data
    selection actually changes -- window and unit are the only knobs that touch it."""
    key = (c["window_days"], c["unit"], c["halflife_days"], c["pool_weight"], c["asof"])
    if key not in cache:
        cache.clear()                       # one dataset at a time; these are large
        cache[key] = rate.load(c, quiet=True)
    ids, ix, d = cache[key]
    if not (~d["train"]).sum():
        return None
    r = rate.fit(len(ids), d, c, quiet=True)
    ll, acc, brier = rate.score(r, d, c, ~d["train"])
    return {"ll": ll, "acc": acc, "brier": brier, "n": int((~d["train"]).sum())}


def show(label, results, base):
    print(f"\n{label}")
    print(f"  {'SETTING':>12}{'LOG-LOSS':>11}{'vs BASE':>9}{'ACC':>8}{'BRIER':>8}")
    for v, s in results:
        if not s:
            continue
        mark = "  <-- best" if s is min((x for _, x in results if x),
                                       key=lambda x: x["ll"]) else ""
        print(f"  {str(v):>12}{s['ll']:>11.4f}{s['ll'] - base:>+9.4f}"
              f"{s['acc']:>8.3f}{s['brier']:>8.4f}{mark}")


def main(argv):
    c = rate.conf(argv)
    quick = "--quick" in argv
    base = run(dict(c))
    print(f"baseline {json.dumps({k: c[k] for k in GRID})}")
    print(f"  holdout log-loss {base['ll']:.4f}  accuracy {base['acc']:.3f}  "
          f"({base['n']} observations)")

    best = dict(c)
    for knob, values in GRID.items():
        if quick and knob in ("scale", "pool_weight", "window_days"):
            continue
        rows = []
        for v in values:
            trial = dict(best)
            trial[knob] = v
            rows.append((v, run(trial)))
        show(knob, rows, base["ll"])
        good = min((x for _, x in rows if x), key=lambda x: x["ll"])
        best[knob] = next(v for v, x in rows if x is good)

    print(f"\nbest one-at-a-time: {json.dumps({k: best[k] for k in GRID})}")
    b = run(dict(best))
    print(f"  holdout log-loss {b['ll']:.4f} ({b['ll'] - base['ll']:+.4f})  "
          f"accuracy {b['acc']:.3f}")

    # the two knobs that interact: a shorter memory needs a different partner model,
    # because it has fewer matches per player to separate her from her team-mate
    print("\npair_alpha x halflife_days (holdout log-loss)")
    hl = GRID["halflife_days"]
    print("       " + "".join(f"{h:>10}" for h in hl))
    for a in GRID["pair_alpha"]:
        line = f"  {a:>4} "
        for h in hl:
            t = dict(best, pair_alpha=a, halflife_days=h)
            s = run(t)
            line += f"{s['ll']:>10.4f}" if s else f"{'-':>10}"
        print(line, flush=True)

    json.dump({k: best[k] for k in GRID}, open("/tmp/sweep_best.json", "w"), indent=1)
    print("\nwrote /tmp/sweep_best.json")


if __name__ == "__main__":
    main(sys.argv[1:])
