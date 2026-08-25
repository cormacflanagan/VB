"""Does hill climbing beat the hand-tuned settings, or just beat the tuning set?

  python3 scripts/climb.py bt          # tune Bradley-Terry
  python3 scripts/climb.py glicko      # tune the online model
  python3 scripts/climb.py bt --rounds 4

Coordinate hill climbing with an adaptive step: take each knob in turn, try a step up and a
step down, keep an improvement and grow that knob's step, otherwise halve it. Repeat until
nothing moves. It is better suited to this problem than the grid search in scripts/sweep.py
-- grids waste evaluations on obviously bad corners, cannot see between their own
gridlines, and cost exponentially more per knob added, while a coordinate search costs
linearly and lands on interior optima.

The reason to be careful is that hill climbing is very good at its actual job, which is
finding the highest point on the *validation* surface -- noise included. With roughly
sixty-seven thousand validation matches the standard error of log-loss is about 0.0023, and
a search making N comparisons at that resolution can be expected to pick up a spurious
improvement of about se * sqrt(2 * ln N) by chance alone: with N = 60, near 0.007. That is
the same size as the real differences between the models in scripts/bench.py, so a search
that reports only its validation score is reporting mostly its own optimism.

So every run here reports three numbers: the validation score it optimised, the test score
it was never allowed to see, and the size of the selection effect implied by how many
evaluations it spent. A tuned model that improves on validation and not on test has found
noise, and this prints that verdict rather than the improvement.
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench
import models

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
OUT = os.path.join(DATA, "climb.json")

# name: (start, low, high, first step, integer?)
SPACES = {
    "bt": {
        "halflife": (365.0, 45.0, 1500.0, 120.0, False),
        "ridge": (0.25, 0.01, 4.0, 0.15, False),
        "wpow": (0.0, 0.0, 3.0, 0.4, False),
        "finw": (4.0, 0.0, 12.0, 1.5, False),
    },
    "glicko": {
        "k0": (0.60, 0.05, 3.0, 0.25, False),
        "scale": (1.0, 0.2, 4.0, 0.4, False),
        "n0": (25.0, 2.0, 200.0, 15.0, False),
        "k_floor": (0.03, 0.0, 0.4, 0.03, False),
        "revert": (0.0, 0.0, 0.02, 0.002, False),
    },
    "elo": {
        "k0": (0.10, 0.01, 1.0, 0.06, False),
        "scale": (1.0, 0.2, 4.0, 0.4, False),
        "revert": (0.0, 0.0, 0.02, 0.002, False),
    },
}


def build(name, n, d, fin, fit, ev, **kw):
    if name == "bt":
        return models.bt(n, d, fin, fit, ev, **kw)
    if name in ("elo", "glicko"):
        return models._online(n, d, fit, ev, glicko=(name == "glicko"), **kw)
    raise SystemExit(f"no search space for {name!r}")


def main(argv):
    if not argv:
        sys.exit("usage: climb.py <model> [--rounds N]")
    name = argv[0]
    rounds = int(argv[argv.index("--rounds") + 1]) if "--rounds" in argv else 3
    if name not in SPACES:
        sys.exit(f"tunable models: {', '.join(SPACES)}")
    space = SPACES[name]

    ids, ix, d = bench.load()
    fin = bench.standings(ix)
    n = len(ids)
    yv, yt = d["y"][d["valid"]], d["y"][d["test"]]
    nv = len(yv)

    evals = [0]

    def on_valid(par):
        evals[0] += 1
        p = build(name, n, d, fin, d["train"], d["valid"], **par)
        return bench.score(p, yv)["ll"]

    def on_test(par):
        p = build(name, n, d, fin, d["train"] | d["valid"], d["test"], **par)
        return bench.score(p, yt)

    cur = {k: v[0] for k, v in space.items()}
    step = {k: v[3] for k, v in space.items()}
    t0 = time.time()
    base_v = on_valid(cur)
    base_t = on_test(cur)
    print(f"\n  starting point {json.dumps(cur)}")
    print(f"  valid {base_v:.4f}   test {base_t['ll']:.4f}\n")

    best_v = base_v
    trail = []
    for rnd in range(1, rounds + 1):
        moved = False
        for k in space:
            lo, hi = space[k][1], space[k][2]
            improved = False
            for sgn in (1, -1):
                cand = dict(cur)
                cand[k] = float(np.clip(cur[k] + sgn * step[k], lo, hi))
                if abs(cand[k] - cur[k]) < 1e-12:
                    continue
                v = on_valid(cand)
                trail.append({"round": rnd, "knob": k, "value": cand[k], "valid": v})
                if v < best_v - 1e-9:
                    print(f"  round {rnd}  {k:>9} -> {cand[k]:<9.4g} valid {v:.4f}"
                          f"  ({v - best_v:+.4f})")
                    cur, best_v, improved, moved = cand, v, True, True
                    step[k] *= 1.6
                    break
            if not improved:
                step[k] *= 0.5
        if not moved:
            print(f"  round {rnd}: no knob improved; stopping")
            break

    final_t = on_test(cur)
    # best-of-N selection effect: how much a search this long expects to gain from noise
    se = 0.6 / np.sqrt(nv)
    bias = se * np.sqrt(2 * np.log(max(evals[0], 2)))
    print(f"\n  {evals[0]} evaluations in {time.time() - t0:.0f}s")
    print(f"  tuned {json.dumps({k: round(v, 4) for k, v in cur.items()})}")
    print(f"\n  {'':<12}{'VALID':>9}{'TEST':>9}{'TEST ACC':>10}{'BRIER':>9}")
    print(f"  {'start':<12}{base_v:>9.4f}{base_t['ll']:>9.4f}{base_t['acc']:>10.3f}"
          f"{base_t['brier']:>9.4f}")
    print(f"  {'tuned':<12}{best_v:>9.4f}{final_t['ll']:>9.4f}{final_t['acc']:>10.3f}"
          f"{final_t['brier']:>9.4f}")
    print(f"  {'change':<12}{best_v - base_v:>+9.4f}{final_t['ll'] - base_t['ll']:>+9.4f}")
    print(f"\n  validation standard error {se:.4f}; a {evals[0]}-evaluation search expects "
          f"about {bias:.4f}\n  of apparent gain from noise alone.")
    gain_v, gain_t = base_v - best_v, base_t["ll"] - final_t["ll"]
    if gain_t > se:
        verdict = "real: the tuned settings also improve the untouched test window"
    elif gain_v > bias and gain_t <= se:
        verdict = ("overfitting: validation improved by more than noise explains, and the "
                   "test window did not follow")
    else:
        verdict = "nothing found: the starting point was already at the optimum"
    print(f"  verdict -- {verdict}")

    json.dump({"model": name, "start": {k: v[0] for k, v in space.items()}, "tuned": cur,
               "evals": evals[0], "se": se, "selectionBias": bias,
               "validStart": base_v, "validTuned": best_v,
               "testStart": base_t, "testTuned": final_t,
               "verdict": verdict, "trail": trail},
              open(OUT.replace(".json", f"_{name}.json"), "w"), indent=1)
    print(f"wrote {os.path.relpath(OUT.replace('.json', f'_{name}.json'))}")


if __name__ == "__main__":
    main(sys.argv[1:])
