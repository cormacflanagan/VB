#!/usr/bin/env python3
"""Pack a set of polycubes into a box, as a SAT (exact-cover) problem.

Encoding
--------
For every piece p and every way that piece can be dropped into the box
(orientation + translation) there is one Boolean variable

    x[p, k]  ==  "piece p sits at placement k"

and the packing is then exactly two families of cardinality constraints:

    (A) every piece is used exactly once      sum_k x[p, k] = 1     for each p
    (B) every cell is covered exactly once    sum  x[p, k] = 1      for each cell
                                            (p,k) covering the cell

(A) makes the assignment a placement per piece, (B) makes the placements a
partition of the box - together they are an exact cover.  Both are encoded with
pysat's sequential-counter encoding, which is linear in the number of literals
(pairwise at-most-one would be quadratic and this problem has thousands of
placements per cell).

A piece may be given several *candidate shapes* rather than one.  Then the
variables range over (shape, placement) pairs, and (A) makes the solver choose
the shape as well - which is how an uncertain piece list can be resolved
against the constraint that the pieces must tile the box.

Optionally the symmetries of the box are broken by restricting the first
piece to placements that are lexicographically minimal in their orbit.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from polycube import normalise, orientations, placements, render, ROTATIONS  # noqa: E402


# --------------------------------------------------------------------------- model

def box_symmetries(dims):
    """Rotations of the lattice that map the box onto itself, as cell maps."""
    X, Y, Z = dims
    out = []
    for r in ROTATIONS:
        corners = [r((x, y, z)) for x in (0, X) for y in (0, Y) for z in (0, Z)]
        mx = min(c[0] for c in corners); my = min(c[1] for c in corners); mz = min(c[2] for c in corners)
        ex = max(c[0] for c in corners) - mx
        ey = max(c[1] for c in corners) - my
        ez = max(c[2] for c in corners) - mz
        if (ex, ey, ez) != (X, Y, Z):
            continue

        def f(cell, r=r, mx=mx, my=my, mz=mz):
            x, y, z = r(cell)
            return (x - mx, y - my, z - mz)

        out.append(f)
    return out


def canonical_placement(cells, syms):
    return min(tuple(sorted(g(c) for c in cells)) for g in syms)


class Model:
    def __init__(self, dims, pieces, break_symmetry=True, distinct_shapes=False):
        self.dims = tuple(dims)
        self.pieces = pieces
        self.cells = [(x, y, z) for x in range(dims[0]) for y in range(dims[1]) for z in range(dims[2])]
        self.break_symmetry = break_symmetry
        self.distinct_shapes = distinct_shapes
        self.options = []          # per piece: list of (shape_name, shape_cells, placement)
        self._build_options()

    def _build_options(self):
        syms = box_symmetries(self.dims) if self.break_symmetry else None
        for i, piece in enumerate(self.pieces):
            opts = []
            for shape in piece["shapes"]:
                cells = [tuple(c) for c in shape["cells"]]
                for pl in placements(cells, self.dims):
                    if i == 0 and syms:
                        key = tuple(sorted(pl))
                        if key != canonical_placement(pl, syms):
                            continue
                    opts.append((shape["name"], cells, pl))
            if not opts:
                raise SystemExit(f"piece {piece['id']} has no legal placement in {self.dims}")
            self.options.append(opts)

    # ----------------------------------------------------------------- CNF
    def cnf(self):
        from pysat.card import CardEnc, EncType
        from pysat.formula import CNF, IDPool

        pool = IDPool()
        cnf = CNF()
        var = {}
        for p, opts in enumerate(self.options):
            for k in range(len(opts)):
                var[p, k] = pool.id(("x", p, k))

        def exactly_one(lits):
            cnf.append(list(lits))                                   # at least one
            if len(lits) > 1:
                enc = EncType.pairwise if len(lits) <= 8 else EncType.seqcounter
                cnf.extend(CardEnc.atmost(lits=list(lits), bound=1, vpool=pool, encoding=enc).clauses)

        for p, opts in enumerate(self.options):                      # (A) one placement per piece
            exactly_one([var[p, k] for k in range(len(opts))])

        by_cell = {c: [] for c in self.cells}                        # (B) one piece per cell
        for p, opts in enumerate(self.options):
            for k, (_, _, pl) in enumerate(opts):
                for c in pl:
                    by_cell[c].append(var[p, k])
        for c in self.cells:
            if not by_cell[c]:
                raise SystemExit(f"cell {c} cannot be covered by any piece")
            exactly_one(by_cell[c])

        if self.distinct_shapes:                                     # no shape used twice
            names = sorted({n for opts in self.options for (n, _, _) in opts})
            for name in names:
                per_piece = []
                for p, opts in enumerate(self.options):
                    lits = [var[p, k] for k, (n, _, _) in enumerate(opts) if n == name]
                    if lits:
                        u = pool.id(("uses", p, name))
                        for l in lits:
                            cnf.append([-l, u])
                        per_piece.append(u)
                if len(per_piece) > 1:
                    cnf.extend(CardEnc.atmost(lits=per_piece, bound=1, vpool=pool,
                                              encoding=EncType.pairwise).clauses)
        self.pool, self.var = pool, var
        return cnf

    # --------------------------------------------------------------- solving
    def solve(self, limit=1, solver_name="cadical153", verbose=True):
        from pysat.solvers import Solver

        cnf = self.cnf()
        nvars = max(abs(l) for cl in cnf.clauses for l in cl)
        if verbose:
            total = sum(len(o) for o in self.options)
            print(f"box {self.dims[0]}x{self.dims[1]}x{self.dims[2]} = {len(self.cells)} cells, "
                  f"{len(self.pieces)} pieces, {total} placement variables")
            print(f"CNF: {nvars} variables, {len(cnf.clauses)} clauses")
        sols = []
        with Solver(name=solver_name, bootstrap_with=cnf.clauses) as s:
            while len(sols) < limit and s.solve():
                model = set(l for l in s.get_model() if l > 0)
                chosen = []
                for p, opts in enumerate(self.options):
                    for k, opt in enumerate(opts):
                        if self.var[p, k] in model:
                            chosen.append((p, k, opt))
                            break
                sols.append(chosen)
                s.add_clause([-self.var[p, k] for p, k, _ in chosen])
        return sols

    # --------------------------------------------------------------- output
    def verify(self, chosen):
        seen = {}
        for p, _, (_, _, pl) in chosen:
            for c in pl:
                assert c not in seen, f"overlap at {c}"
                assert all(0 <= c[i] < self.dims[i] for i in range(3)), f"outside the box: {c}"
                seen[c] = p
        assert len(chosen) == len(self.pieces), "not every piece placed"
        assert len(seen) == len(self.cells), f"{len(self.cells) - len(seen)} cells left empty"
        return seen

    def show(self, chosen):
        seen = self.verify(chosen)
        label = {}
        for i, piece in enumerate(self.pieces):
            label[i] = piece.get("label") or piece["id"][:1].upper()
        X, Y, Z = self.dims
        lines = []
        head = "   ".join(f"z={z}".ljust(X) for z in range(Z))
        lines.append("  " + head)
        for y in range(Y):
            lines.append("  " + "   ".join("".join(label[seen[(x, y, z)]] for x in range(X)) for z in range(Z)))
        return "\n".join(lines)


# --------------------------------------------------------------------------- cli

def load(path):
    spec = json.loads(Path(path).read_text())
    pieces = []
    for p in spec["pieces"]:
        shapes = p["shapes"] if "shapes" in p else [{"name": p["id"], "cells": p["cells"]}]
        shapes = [{"name": s["name"], "cells": [tuple(c) for c in s["cells"]]} for s in shapes]
        pieces.append(dict(p, shapes=shapes))
    return spec["box"], pieces


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="JSON file with the box dimensions and the pieces")
    ap.add_argument("--box", help="override the box, e.g. 4x4x4")
    ap.add_argument("--all", type=int, default=1, metavar="N", help="find up to N solutions (default 1)")
    ap.add_argument("--dimacs", metavar="FILE", help="also write the CNF in DIMACS form")
    ap.add_argument("--no-symmetry-breaking", action="store_true")
    ap.add_argument("--distinct-shapes", action="store_true",
                    help="forbid two pieces from being assigned the same shape")
    ap.add_argument("--json-out", metavar="FILE", help="write the solution as JSON")
    args = ap.parse_args()

    box, pieces = load(args.spec)
    if args.box:
        box = [int(v) for v in args.box.lower().split("x")]
    volume = sum(len(p["shapes"][0]["cells"]) for p in pieces)
    sizes = sorted({len(s["cells"]) for p in pieces for s in p["shapes"]})
    print(f"{len(pieces)} pieces, cell counts {sizes}, first-shape volume {volume}, "
          f"box volume {box[0] * box[1] * box[2]}")

    m = Model(box, pieces, break_symmetry=not args.no_symmetry_breaking,
              distinct_shapes=args.distinct_shapes)
    if args.dimacs:
        m.cnf().to_file(args.dimacs)
        print(f"wrote {args.dimacs}")
    sols = m.solve(limit=args.all)
    if not sols:
        print("UNSATISFIABLE - these pieces cannot tile this box")
        return 1
    for i, chosen in enumerate(sols, 1):
        print(f"\nsolution {i}:")
        print(m.show(chosen))
        for p, _, (name, _, pl) in chosen:
            shape = "" if name == pieces[p]["id"] else name
            print(f"   {pieces[p]['label']} {pieces[p]['id']:<12} {shape:<5} {sorted(pl)}")
    if args.json_out:
        out = [[dict(piece=pieces[p]["id"], shape=name, cells=sorted(pl))
                for p, _, (name, _, pl) in chosen] for chosen in sols]
        Path(args.json_out).write_text(json.dumps(out, indent=1))
        print(f"wrote {args.json_out}")
    print(f"\n{len(sols)} solution(s) found and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
