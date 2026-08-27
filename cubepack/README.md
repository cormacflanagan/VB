# cubepack — packing the 13 printed pieces by SAT

A SAT model for "do these polycubes tile this box, and how", the piece list read off the
photographs, and a verified packing.

    python3 sat_pack.py pieces.json                  # solve (< 1 s)
    python3 sat_pack.py pieces.json --all 20         # 20 distinct solutions
    python3 sat_pack.py pieces.json --dimacs cube.cnf
    python3 report.py > SOLUTION.md                  # readable piece list + packing
    python3 selftest.py                              # 12 pentominoes in a 3x4x5 box

## The box is 4x4x4, not 5x5x3

Thirteen pentacubes would be 13 x 5 = **65** unit cubes:

* 5 x 5 x 3 = **75** — ten cubes short;
* 65 factors only as 1 x 5 x 13, a one-cube-thick slab, and several of these pieces are not
  flat, so **no box of any shape has volume 65**.

The small flat red S is **four** cubes, not five — two rows of two in a single layer. Measured
against the other pieces in the photographs, its long edge, depth edge and height are in the
ratio of one layer of a 2+2 S-tetromino at the camera elevation the rest of the picture shows,
and the near-overhead view shows both of its rows spanning exactly two cells.

So the set is **12 pentacubes + 1 tetracube = 64 = 4 x 4 x 4** — the classic thirteen-piece
cube. `SOLUTION.md` has a packing; the set has at least 40 distinct solutions.

## The SAT encoding

For each piece `p` and each way it can be dropped into the box (one of its <= 24 orientations,
translated anywhere it fits) there is one Boolean variable

    x[p, k]  ==  "piece p sits at placement k"

and the packing is exactly two families of cardinality constraints:

| constraint | meaning |
| --- | --- |
| `sum_k x[p,k] = 1` for every piece | each piece is used exactly once |
| `sum x[p,k] = 1` over the placements covering a cell, for every cell | each cell is filled exactly once |

Together they say the chosen placements partition the box: an exact cover. Both are encoded
with pysat's sequential-counter encoding, which is linear in the literals — pairwise
at-most-one would be quadratic, and a cell here is covered by hundreds of placements. The
4x4x4 instance is ~24 000 variables and ~61 000 clauses and solves in well under a second with
CaDiCaL. Every solution is verified for overlap and coverage before it is printed.

Two extras:

* **Symmetry breaking** (default on) restricts the first piece to placements that are
  lexicographically minimal under the 24 rotations mapping the box to itself.
* **Alternative shapes.** A piece may carry several candidate shapes instead of one; the
  variables then range over (shape, placement) pairs, so the solver chooses the shape too.
  `--distinct-shapes` forbids two pieces from being assigned the same shape. This is how the
  last piece below was pinned down.

## How the pieces were read

Four photographs of the same layout: one near-overhead (footprints readable directly) and
three oblique (heights readable). `identify/` holds the supporting pipeline — colour
segmentation, an orthographic renderer whose face labels reproduce the creases a camera sees,
and a scorer over every tetracube and pentacube orientation. **Its ranking is not reliable on
its own** (the true shape was often second or third, and the three views' rankings disagreed),
so it was used only to shortlist; the readings below come from measuring the pieces against
each other in the photographs.

Eleven pieces were read that way, at the confidences recorded in `pieces.json`. Four are
certain — the plus (X), the U, the four-cube S, the L. The last piece was then **forced**: with
the other twelve fixed, exactly one non-planar pentacube completes a 4x4x4 packing, and it
matches the photographs. That is the one identification the solver made rather than the eye.

Residual risk: the medium-confidence readings (W, N, Z, V, and the two two-level pieces) are
shapes whose silhouettes are easy to confuse. If one is wrong, correct its `cells` in
`pieces.json` and re-run — the solve takes under a second.

## Files

| file | |
| --- | --- |
| `polycube.py` | orientations, placements, enumeration of the 8 tetracubes / 29 pentacubes, ASCII rendering |
| `sat_pack.py` | the SAT model, solver, verifier and pretty printer |
| `pieces.json` | the 13 pieces, with a description and confidence for each |
| `solution_4x4x4.txt`, `.json`, `SOLUTION.md` | a verified packing |
| `report.py` | renders pieces + solution as Markdown |
| `build_spec.py` | turns `identify/cand_NN.json` into a packing spec with alternatives |
| `identify/` | photo -> candidate shapes pipeline |
| `selftest.py` | 12 pentominoes in a 3x4x5 box |
