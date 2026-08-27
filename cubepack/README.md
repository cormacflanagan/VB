# cubepack — packing the 13 printed pieces by SAT

A SAT model for "do these polycubes tile this box, and how", plus the machinery used to
read the thirteen pieces off the photograph.

    python3 sat_pack.py pieces_photo_bestguess.json          # solve
    python3 sat_pack.py <spec>.json --all 20                 # up to 20 distinct solutions
    python3 sat_pack.py <spec>.json --dimacs cube.cnf        # write the CNF
    python3 selftest.py                                      # the 12 pentominoes in a 3x4x5 box

## The arithmetic comes first

The photograph shows **13 pieces**. Thirteen pentacubes would be 13 x 5 = **65** unit cubes, and

* 5 x 5 x 3 = **75**, so the pieces cannot fill that box — ten cubes short;
* 65 factors only as 1 x 5 x 13, a one-cube-thick slab, and several of the pieces are not flat,
  so **no box of any shape has volume 65**.

Measuring the pieces in the photo against each other resolves it. Piece 02 (the small flat red
S, top of the picture) is **four** cubes, not five: its two rows are each two cells long, they
sit in a single layer, and the ratios between its long edge, its depth edge and its height are
consistent with one layer of a 2+2 S-tetromino at a camera elevation of ~42 degrees (the same
elevation that the other pieces show).

That makes the set **12 pentacubes + 1 tetracube = 64 cubes = 4 x 4 x 4** — the classic
thirteen-piece cube. So the target is a 4x4x4 cube, not 5x5x3.

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
with pysat's sequential-counter encoding (linear in the literals — pairwise at-most-one would
be quadratic, and a cell here is covered by hundreds of placements). The 4x4x4 instance is
about 28 500 variables and 73 000 clauses and solves in well under a second with CaDiCaL.

Two extras:

* **Symmetry breaking** (on by default) restricts the first piece to placements that are
  lexicographically minimal under the 24 rotations that map the box to itself, so the solver
  does not walk through 24 copies of every solution.
* **Alternative shapes.** A piece may be given several candidate shapes instead of one; the
  variables then range over (shape, placement) pairs and the solver chooses the shape too.
  `--distinct-shapes` additionally forbids two pieces from being assigned the same shape.
  This is what `pieces_photo_candidates.json` uses.

## Reading the pieces off the photograph — and why it is not conclusive

`identify/` holds the pipeline: colour-segment the 13 pieces (`segment.py`), render a candidate
polycube under an orthographic camera with the piece resting on the table (`render.py` — faces
are labelled by plane so the label boundaries are exactly the creases a camera sees), and score
each of the 8 tetracubes and 29 pentacubes in each of their orientations by silhouette IoU x
crease alignment x a three-face brightness model, over yaw, elevation, scale and offset
(`match.py`, `candidates.py`). `cand_NN.json` are the resulting ranked candidate lists.

**One photograph cannot settle it.** A single view hides cubes (a cube tucked behind or under
another is simply invisible), and different pentacubes routinely project to near-identical
silhouettes — for the blue U (piece 12) the best-scoring candidate and the true shape differ by
0.04 in IoU. Nor does the packing constraint pin it down: many different sets of 12 pentacubes
+ 1 tetracube tile a 4x4x4 cube, so "it packs" is not evidence that a reading is right.

What the photograph *does* settle, from direct measurement against the calibrated cube size:

| piece | reading | confidence |
| --- | --- | --- |
| 02 red (small flat S) | S-tetromino, 4 cubes, one layer | high |
| 12 blue | U pentomino, 3x2 minus a corner, one layer | high |
| 10 blue | X pentomino (plus), one layer — bounding box matches a flat 3x3 plus to within 1% | high |
| 07 red | V pentomino: a 3-tall column with a 2-long foot | medium-high |
| the rest | see `pieces_photo_candidates.json` | low — several shapes fit equally well |

`pieces_photo_bestguess.json` is one complete reading consistent with all of the above **and**
with tiling the cube; `solution_4x4x4.txt` is its verified packing. Treat it as provisional.

## Giving the solver the real piece list

Write each piece as its layers, `z=0` first, `#` for a cube:

```
piece 05 green:
  z=0    z=1
  ##.    #..
  .#.    ...
```

Twelve such sketches plus the tetracube, and

    python3 sat_pack.py pieces.json --all 5

returns verified packings in seconds. (Two photographs per piece, from opposite corners, would
also be enough for `identify/` to resolve the hidden cubes automatically.)

## Files

| file | |
| --- | --- |
| `polycube.py` | orientations, placements, enumeration of the 8 tetracubes / 29 pentacubes, ASCII rendering |
| `sat_pack.py` | the SAT model, solver, verifier and pretty printer |
| `build_spec.py` | turns `identify/cand_NN.json` into a packing spec |
| `pieces_photo_bestguess.json` | provisional piece list (one shape per piece) |
| `pieces_photo_candidates.json` | the same pieces with their alternative shapes |
| `solution_4x4x4.txt`, `.json` | the verified packing of the provisional list |
| `identify/` | photo -> candidate shapes pipeline |
| `selftest.py` | 12 pentominoes in a 3x4x5 box |
