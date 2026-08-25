"""Is the fit converged, or is scripts/uncertainty.py measuring the optimiser?

  python3 scripts/converge.py [--iters 600 1800]

The bootstrap in scripts/uncertainty.py refits from scratch on each resample and reads the
spread of the results as evidence about the data. That reading only holds if every fit has
actually arrived. Adam is deterministic here, so a converged model gives identical answers
on identical input and all the spread comes from the resampling -- but an *unconverged* one
stops wherever the step schedule ran out, which differs from replicate to replicate for
reasons that have nothing to do with the evidence.

The players at risk are exactly the ones under examination. A well-determined rating has
steep curvature and lands quickly; a player whose likelihood is nearly flat drifts for as
long as she is allowed to, which is the same flatness the intervals are trying to detect.
So the check has to be reported separately for the well- and badly-determined, not as one
average that the bulk of the field would dominate.
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rate

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv):
    its = [int(v) for v in argv[argv.index("--iters") + 1:argv.index("--iters") + 3]] \
        if "--iters" in argv else [600, 1800]
    c = rate.conf([])
    ids, ix, d = rate.load(c, quiet=True)
    n = len(ids)
    everything = np.ones(len(d["y"]), bool)
    nm = rate.counts(ids, d)

    runs = {}
    for it in its:
        cc = dict(c, iters=it)
        t0 = time.time()
        runs[it] = rate.fit(n, d, cc, mask=everything, quiet=True)
        print(f"  {it} iterations: {time.time() - t0:.0f}s")

    a, b = runs[its[0]], runs[its[-1]]
    delta = np.abs(a - b)
    print(f"\nmovement between {its[0]} and {its[-1]} iterations, by match count:")
    print(f"  {'PLAYERS':>12}{'MEDIAN':>9}{'90TH':>9}{'99TH':>9}{'MAX':>9}")
    for lo, hi, lab in ((0, 8, "under 8"), (8, 20, "8-19"), (20, 100, "20-99"),
                        (100, 10 ** 9, "100+")):
        g = (nm >= lo) & (nm < hi)
        if g.sum() < 10:
            continue
        print(f"  {lab:>7} {int(g.sum()):>5}{np.median(delta[g]):>9.4f}"
              f"{np.percentile(delta[g], 90):>9.4f}{np.percentile(delta[g], 99):>9.4f}"
              f"{delta[g].max():>9.4f}")
    print("\nA rating that still moves by more than about 0.01 between these two budgets is\n"
          "not converged, and any interval quoted for it is partly an artefact of `iters`.")


if __name__ == "__main__":
    main(sys.argv[1:])
