"""One player, two Volleyball Life accounts -- find them and merge them.

  python3 scripts/dedupe.py            # report only
  python3 scripts/dedupe.py --write    # write data/aliases.json

Players re-register. A club change, a lost password, a parent signing a kid up a second
time, and the site now holds two profiles with two separate rating histories, each seeing
half the matches. Ashley Ruschill (2029, McKinney TX) is the case that exposed this: id
105245 with 603 matches and id 247847 with 32, listed at 5'5" and 5'4", both real accounts
carrying a real TruVolley, and both landing in the same top sixty -- the same girl ranked
twice, at #44 and #55.

Splitting a career in half hurts the smaller half most. The 32-match account is fit almost
entirely from one partnership, which is exactly the situation the model handles worst, and
the rating it produces is close to meaningless.

Matching on name alone would be reckless in a corpus this size -- there really are two
Sydney Smiths. The test here has to be able to *disprove* a merge, so:

  same normalised name, same graduation year, same state (all three non-empty), and the
  two ids never appear at the same tournament.

The last clause is the one doing the work. Two distinct girls of the same name and class
in the same state are on the same regional circuit and will turn up in one draw sooner or
later, as opponents if not as partners; one person's two accounts cannot, because she
enters under one of them at a time. It is evidence of absence that is actually meaningful
here, and it is stricter than requiring they never play each other -- sharing a tournament
is far more likely than being drawn against each other in it.

The alias map sends every id in a group to the one with the most matches. scripts/merge.py
applies it when it builds the corpus, so the fit sees one player.
"""
import json, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(DATA, "aliases.json")
POPS = ("cohort2027.json", "cohort2028.json", "pop2027.json", "pop2028.json")
ROSTER = os.path.join("vb", "players.jsonl")   # the whole crawl, juniors and adults


def norm(s):
    """Casefold and squeeze: 'Maddy  Wagner' and 'maddy wagner' are one key."""
    return re.sub(r"[^a-z ]", "", re.sub(r"\s+", " ", (s or "").strip().lower()))


def population():
    """Cohort files first -- they carry a graduation year, and the rule needs one.

    The crawl roster has a row for every player on the site but leaves `grad` null for
    adults, who are therefore never merged here: name and state alone is far too weak a
    key once the pool is a hundred thousand people.
    """
    out = {}
    for f in POPS:
        p = os.path.join(DATA, f)
        if os.path.exists(p):
            for k, v in json.load(open(p)).items():
                out.setdefault(int(k), v)
    p = os.path.join(DATA, ROSTER)
    if os.path.exists(p) or os.path.exists(p + ".gz"):
        for v in read_jsonl(p):
            out.setdefault(int(v["id"]), v)
    return out


def main(argv):
    pop = population()
    groups = defaultdict(list)
    for pid, v in pop.items():
        key = (norm(v.get("name")), v.get("grad"), (v.get("state") or "").strip().upper())
        if all(key):
            groups[key].append(pid)
    cand = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
    watch = {p: k for k, v in cand.items() for p in v}
    print(f"{len(pop)} players; {len(cand)} name+class+state collisions covering "
          f"{sum(len(v) for v in cand.values())} ids")

    # which collisions are two real people: they showed up at the same tournament
    seen = defaultdict(lambda: defaultdict(set))   # key -> tournament -> ids present
    played = defaultdict(int)
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        ev = (m.get("src"), m.get("tid"))
        for p in m["a"] + m["b"]:
            played[p] += 1
            if p in watch:
                seen[watch[p]][ev].add(p)
    distinct = {k for k, evs in seen.items() if any(len(s) > 1 for s in evs.values())}
    print(f"  {len(distinct)} are two different people (both ids at one tournament)")

    alias, merged = {}, []
    for k, v in cand.items():
        if k in distinct:
            continue
        keep = max(v, key=lambda p: (played.get(p, 0), p))
        for p in v:
            if p != keep:
                alias[str(p)] = keep
        merged.append((k, keep, [(p, played.get(p, 0)) for p in v]))
    merged.sort(key=lambda t: -sum(n for _, n in t[2]))
    print(f"  {len(merged)} merge into {len(set(alias.values()))} players "
          f"({len(alias)} ids retired)\n")
    print(f"  {'PLAYER':26}{'CLASS':>6}{'ST':>4}   MATCHES BY ACCOUNT")
    for k, keep, mem in merged[:25]:
        s = "  ".join(f"{'*' if p == keep else ' '}{p}:{n}" for p, n in mem)
        print(f"  {k[0][:25]:26}{k[1]:>6}{k[2]:>4}   {s}")
    if len(merged) > 25:
        print(f"  ... and {len(merged) - 25} more")

    if "--write" in argv:
        json.dump({"alias": alias, "groups": len(merged)}, open(OUT, "w"), indent=1)
        print(f"\nwrote {os.path.relpath(OUT)}")
    else:
        print("\n(report only -- pass --write to save data/aliases.json)")


if __name__ == "__main__":
    main(sys.argv[1:])
