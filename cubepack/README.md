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

Eight photographs of two layouts, two of them near-overhead. `identify/` holds the supporting
pipeline - colour segmentation, an orthographic renderer whose face labels reproduce the creases
a camera sees, and a scorer over every tetracube and pentacube orientation.

What actually settled the flat pieces was simpler: in a near-overhead view the silhouette is the
piece's footprint, so the **minimum-area bounding rectangle**, measured in cube units (the cube
size comes from the silhouette area), separates the pentomino families outright:

| measured min-rect | shapes |
| --- | --- |
| 4 x 2 | L, N, Y |
| 3 x 3 | F, T, V, W, X, Z |
| 3 x 2 | P, U (and the S tetromino, at 4 cubes) |

The known-good pieces calibrate it: the plus measures 2.89 x 2.74, the U 3.13 x 2.08, the
four-cube S 2.97 x 1.93. Fitting only the *flat* shapes to a near-overhead silhouette then picks
the family member, with a clear margin for most (S tetromino 0.913, P 0.913, W 0.862, F 0.855).

Nine pieces are settled that way. The other four are two-level - a tetromino lying flat with one
cube on top - which the top-down view shows as a footprint plus a parallax-shifted top face.
Their footprints are readable (L-tetromino for 04, S-tetromino for 07 and 12, L-tetromino for
13), but *which* cell carries the top cube is not, so those four carry the residual uncertainty:
the alternatives that also tile the cube are listed below. The packing constraint alone does not
resolve them - many combinations of the fourteen "tetromino + one on top" pentacubes complete a
4x4x4 with the other nine fixed.

Corrections so far: the first pass (one oblique photo) had four wrong - piece 02 is N, not W;
06 is W, not N; 09 is F, not Z; and piece 01 is not L. Piece 01 was then read as the V
pentomino, which the owner corrected: there is no V in the set. The low-angle views (W2:10,
W3:3, V2:2) do show a cube standing proud of its bar, so 01 is two-level like 04, 07, 12 and 13 -
an L-tetromino with a cube on the foot cell. Five L-based candidates all complete a packing, so
the choice there is the photograph's (top-down fit 0.911 for P9, 0.900 for its mirror P16),
not the solver's.

Eight of the thirteen are flat pentominoes; five are two-level.

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
