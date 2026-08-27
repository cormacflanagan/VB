#!/usr/bin/env python3
"""Human-readable report: the piece list and a packing, layer by layer."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from polycube import render, normalise

spec = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else "pieces.json").read_text())
sol = json.loads(Path(sys.argv[2] if len(sys.argv) > 2 else "solution_4x4x4.json").read_text())[0]
X, Y, Z = spec["box"]
lab = {p["id"]: p["label"] for p in spec["pieces"]}
grid = {}
for entry in sol:
    for c in entry["cells"]:
        grid[tuple(c)] = lab[entry["piece"]]

out = []
out.append(f"# The 13 pieces in a {X}x{Y}x{Z} cube\n")
out.append("## Pieces\n")
for p in spec["pieces"]:
    n = len(p["cells"])
    out.append(f"**{p['label']} - {p['id']}** ({n} cubes) - {p['description']}  ")
    out.append(f"confidence of the reading: {p['confidence']}\n")
    out.append("```")
    out.append(render(p["cells"], indent=""))
    out.append("```\n")

out.append(f"## Packing\n\nEach grid is one layer of the cube, z = 0 (bottom) first; x runs across, y down.\n")
out.append("```")
out.append("    " + "     ".join(f"z={z}".ljust(X) for z in range(Z)))
for y in range(Y):
    out.append("    " + "     ".join("".join(grid[(x, y, z)] for x in range(X)) for z in range(Z)))
out.append("```\n")
out.append("## Cell coordinates\n")
out.append("| piece | cubes (x, y, z) |")
out.append("| --- | --- |")
for entry in sol:
    cells = ", ".join(f"({c[0]},{c[1]},{c[2]})" for c in entry["cells"])
    out.append(f"| {lab[entry['piece']]} {entry['piece']} | {cells} |")
print("\n".join(out))
