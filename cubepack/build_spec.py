"""Turn the photo-identification candidate lists into a packing spec for sat_pack.py."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from polycube import enumerate_polycubes

CAT = {f"T{i}": c for i, c in enumerate(enumerate_polycubes(4))}
CAT.update({f"P{i}": c for i, c in enumerate(enumerate_polycubes(5))})

def build(cand_dir, box, topk=10, out="spec.json", force=None):
    force = force or {}
    pieces = []
    for i in range(1, 14):
        d = json.loads(Path(cand_dir, f"cand_{i:02d}.json").read_text())
        ranked = sorted(d["cands"].items(), key=lambda kv: -kv[1]["score"])
        names = [n for n, _ in ranked][:topk]
        if i in force:
            names = force[i] if isinstance(force[i], list) else [force[i]]
        pieces.append(dict(id=f"{i:02d}-{d['color']}", label="ABCDEFGHIJKLM"[i - 1],
                           colour=d["color"],
                           shapes=[dict(name=n, cells=[list(c) for c in CAT[n]]) for n in names]))
    Path(out).write_text(json.dumps(dict(box=box, pieces=pieces), indent=1))
    return out

if __name__ == "__main__":
    cand_dir = sys.argv[1]; box = [int(v) for v in sys.argv[2].split("x")]
    topk = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    print(build(cand_dir, box, topk, out=sys.argv[4] if len(sys.argv) > 4 else "spec.json"))
