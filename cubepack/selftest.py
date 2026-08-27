#!/usr/bin/env python3
"""Smoke test: the twelve pentominoes tile a 3x4x5 box (a classic packing)."""
import json, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from polycube import enumerate_polycubes

flat = [p for p in enumerate_polycubes(5) if min(max(c[i] for c in p) for i in range(3)) == 0]
assert len(flat) == 12, len(flat)
spec = dict(box=[3, 4, 5], pieces=[dict(id=f"p{i}", label="FILNPTUVWXYZ"[i],
                                        cells=[list(c) for c in s]) for i, s in enumerate(flat)])
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
    json.dump(spec, fh)
    path = fh.name
out = subprocess.run([sys.executable, str(Path(__file__).with_name("sat_pack.py")), path],
                     capture_output=True, text=True)
print(out.stdout[-600:], out.stderr[-400:])
assert "1 solution(s) found and verified" in out.stdout, "pentomino packing failed"
print("selftest OK")
