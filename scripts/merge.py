"""Merge the three corpora into one match file keyed by Volleyball Life id.

  python3 scripts/merge.py   ->  data/all_matches.jsonl.gz, data/all_finishes.jsonl.gz

Each source numbers its players differently, so nothing can be pooled until they are all
speaking the same ids:

  Volleyball Life  native, no translation
  college          cbvb/player-detail publishes `vblId` for 99% of them
  CBVA             inferred by scripts/cbva_link.py from partnerships on a date

A match is kept only when all four players resolve. Dropping a match because one opponent
is unresolved is the right trade: a rating fit on a team with a phantom player learns
nothing about either side, and the alternative -- inventing a node per unresolved id --
would silently split one player into several.

Standings go through the same translation, because half of all tournaments publish a
finish order and no matches at all.
"""
import gzip, json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def cbva_map():
    p = os.path.join(DATA, "cbva", "link.json")
    if not os.path.exists(p):
        return {}
    return {int(k): v["vblId"] for k, v in json.load(open(p))["link"].items()}


def college_map():
    out = {}
    for r in read_jsonl(os.path.join(DATA, "college", "players.jsonl")):
        if r.get("vblId"):
            out[r["cbvbId"]] = r["vblId"]
    for r in read_jsonl(os.path.join(DATA, "college", "rosters.jsonl")):
        if r.get("vblId") and r.get("cbvbId") not in out:
            out[r["cbvbId"]] = r["vblId"]
    return out


def translate(rows, mp, source, out, stat):
    """Rewrite both sides into Volleyball Life ids, dropping any match with a gap."""
    for m in rows:
        a = [mp.get(x) if mp else x for x in m["a"]]
        b = [mp.get(x) if mp else x for x in m["b"]]
        stat[source + " seen"] += 1
        if None in a or None in b:
            stat[source + " dropped: unresolved player"] += 1
            continue
        if len(set(a) | set(b)) != 4:
            stat[source + " dropped: repeated player"] += 1
            continue
        out.write(json.dumps({
            "id": f"{source}:{m['id']}", "date": m["date"],
            "a": sorted(a), "b": sorted(b), "aWon": bool(m["aWon"]),
            "sets": m.get("sets") or [], "src": source,
            "tid": m.get("tid"), "tdId": m.get("tdId"),
            "phase": m.get("phase")}) + "\n")
        stat[source + " kept"] += 1


def main():
    stat = Counter()
    cb, co = cbva_map(), college_map()
    print(f"id maps: {len(cb)} CBVA, {len(co)} college", flush=True)

    mpath = os.path.join(DATA, "all_matches.jsonl.gz")
    with gzip.open(mpath, "wt") as out:
        translate(read_jsonl(os.path.join(DATA, "vb", "matches.jsonl")), None, "vb",
                  out, stat)
        translate(read_jsonl(os.path.join(DATA, "cbva", "matches.jsonl")), cb, "cbva",
                  out, stat)
        translate(read_jsonl(os.path.join(DATA, "college", "matches.jsonl")), co,
                  "college", out, stat)

    # standings: one row per division, teams in finish order, for the events with no
    # match data. rate.py expands these into weighted pairwise comparisons.
    fpath = os.path.join(DATA, "all_finishes.jsonl.gz")
    withm = set()
    for m in read_jsonl(mpath):
        if m["src"] == "vb" and m.get("tdId"):
            withm.add(m["tdId"])
    when = {t["id"]: (t.get("start") or "")[:10]
            for t in read_jsonl(os.path.join(DATA, "vb", "tournaments.jsonl"))}
    doubles = {d["tdId"]: d for d in read_jsonl(os.path.join(DATA, "vb", "divisions.jsonl"))
               if d.get("players") == 2 and not d.get("canceled")}
    bydiv = {}
    for tm in read_jsonl(os.path.join(DATA, "vb", "teams.jsonl")):
        td = tm["tdId"]
        if td in withm or td not in doubles or tm.get("drop") or not tm.get("finish"):
            continue
        if len(tm.get("p") or []) != 2:
            continue
        bydiv.setdefault(td, []).append([tm["finish"], sorted(tm["p"])])
    n = 0
    with gzip.open(fpath, "wt") as out:
        for td, teams in bydiv.items():
            if len(teams) < 3:
                continue
            d = doubles[td]
            out.write(json.dumps({"tid": d["tid"], "tdId": td,
                                  "date": when.get(d["tid"], ""),
                                  "div": d.get("name"),
                                  "teams": sorted(teams)}) + "\n")
            n += 1
    stat["finish-only divisions"] = n

    for k in sorted(stat):
        print(f"  {k:38s} {stat[k]:>9,}")
    print(f"\nwrote {mpath} and {fpath}")


if __name__ == "__main__":
    main()
