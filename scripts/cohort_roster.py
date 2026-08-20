"""Draw the top N of an age-eligible cohort: python3 cohort_roster.py 2028 60

Reads the closed cohort from close_cohort.py and writes a roster file in the same shape
`rosters.py` auto-registers, so the rest of the pipeline treats it like any other group.
The key carries a `_younger` suffix, which is what tells the renderer this is an
age-eligible field rather than a graduating class.
"""
import json, os, sys
from collections import Counter

DATA = os.path.join(os.path.dirname(__file__) or ".", "..", "data")
HERE = os.path.dirname(__file__) or "."


def main(year, n=60):
    pop = json.load(open(f"{DATA}/cohort{year}.json"))
    rated = sorted((p for p in pop.values() if p["tv"]), key=lambda p: -p["tv"])
    top = rated[:n]
    key = f"{year}_younger"
    out = {
        "label": f"{year} and younger — top {n}",
        "roster": [[p["name"], p["id"], p.get("state") or ""] for p in top],
        "meta": {str(p["id"]): {k: p.get(k) for k in
                                ("height", "club", "city", "state", "tv", "grad")}
                 for p in top},
        "population": len(pop), "rated": len(rated),
        "cut": {"nTop": top[-1]["tv"],
                "next": rated[n]["tv"] if len(rated) > n else None,
                "nextName": rated[n]["name"] if len(rated) > n else None},
        "classes": dict(sorted(Counter(p["grad"] for p in top).items())),
    }
    json.dump(out, open(f"{HERE}/roster_{key}.json", "w"), indent=1)
    print(f"roster_{key}.json: top {n} of {len(rated)} rated in a cohort of {len(pop)}")
    print("  by graduating year:", out["classes"])
    print(f"  cut at {top[-1]['tv']:.3f} ({top[-1]['name']}); "
          f"next is {out['cut']['nextName']} at {out['cut']['next']}")
    younger = [p for p in top if p["grad"] > year]
    print(f"  {len(younger)} of the {n} are younger than {year}:")
    for p in younger:
        print(f"    #{top.index(p)+1:<3} {p['tv']:.3f}  {p['name']} ({p['grad']})")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2028,
         int(sys.argv[2]) if len(sys.argv) > 2 else 60)
