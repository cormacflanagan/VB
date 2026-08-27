"""Polycube geometry: orientations, placements, canonical forms, pretty printing."""
from __future__ import annotations

Cell = tuple[int, int, int]
Shape = tuple[Cell, ...]


def _rotations():
    """The 24 orientation-preserving rotations of the cubic lattice, as functions."""
    def rx(p): x, y, z = p; return (x, -z, y)
    def ry(p): x, y, z = p; return (z, y, -x)
    def rz(p): x, y, z = p; return (-y, x, z)

    from collections import deque
    seen, out, queue = set(), [], deque([[]])
    while queue:
        seq = queue.popleft()

        def apply(p, seq=seq):
            for f in seq:
                p = f(p)
            return p

        key = tuple(apply(e) for e in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
        if key in seen:
            continue
        seen.add(key)

        def make(seq=list(seq)):
            def g(p):
                for f in seq:
                    p = f(p)
                return p
            return g

        out.append(make())
        if len(seq) < 6:
            for f in (rx, ry, rz):
                queue.append(seq + [f])
    assert len(out) == 24
    return out


ROTATIONS = _rotations()


def normalise(cells) -> Shape:
    """Translate so the shape touches the origin in every axis; sort for a stable key."""
    mx = min(c[0] for c in cells)
    my = min(c[1] for c in cells)
    mz = min(c[2] for c in cells)
    return tuple(sorted((x - mx, y - my, z - mz) for x, y, z in cells))


def orientations(cells) -> list[Shape]:
    """All distinct rotations of a polycube (fewer than 24 when it is symmetric)."""
    return sorted({normalise([r(c) for c in cells]) for r in ROTATIONS})


def canonical(cells) -> Shape:
    return min(orientations(cells))


def mirror(cells) -> Shape:
    return normalise([(-x, y, z) for x, y, z in cells])


def placements(cells, dims) -> list[frozenset[Cell]]:
    """Every way the polycube fits inside the box, as sets of occupied cells."""
    X, Y, Z = dims
    out, seen = [], set()
    for ori in orientations(cells):
        bx = max(c[0] for c in ori) + 1
        by = max(c[1] for c in ori) + 1
        bz = max(c[2] for c in ori) + 1
        for ox in range(X - bx + 1):
            for oy in range(Y - by + 1):
                for oz in range(Z - bz + 1):
                    cs = frozenset((x + ox, y + oy, z + oz) for x, y, z in ori)
                    if cs not in seen:
                        seen.add(cs)
                        out.append(cs)
    return out


def enumerate_polycubes(n: int) -> list[Shape]:
    """One representative of every polycube of size n, up to rotation."""
    cur = {normalise([(0, 0, 0)])}
    for _ in range(n - 1):
        nxt = set()
        for s in cur:
            for (x, y, z) in s:
                for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                    c = (x + d[0], y + d[1], z + d[2])
                    if c not in s:
                        nxt.add(canonical(list(s) + [c]))
        cur = nxt
    return sorted(cur)


def flattest(cells) -> Shape:
    """The orientation with the fewest layers - the one that reads best as ASCII."""
    return min(orientations(cells), key=lambda o: (max(c[2] for c in o), o))


def render(cells, indent="  ") -> str:
    """Layer-by-layer ASCII picture, z = 0 first, x across, y down."""
    cells = flattest(cells)
    X = max(c[0] for c in cells) + 1
    Y = max(c[1] for c in cells) + 1
    Z = max(c[2] for c in cells) + 1
    layers = []
    for z in range(Z):
        grid = [["." for _ in range(X)] for _ in range(Y)]
        for (x, y, zz) in cells:
            if zz == z:
                grid[y][x] = "#"
        layers.append(["".join(row) for row in grid])
    head = indent + "   ".join(f"z={z}".ljust(X) for z in range(Z))
    body = [indent + "   ".join(layers[z][y] for z in range(Z)) for y in range(Y)]
    return "\n".join([head] + body)
