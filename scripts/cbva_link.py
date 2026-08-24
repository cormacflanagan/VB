"""Resolve CBVA player ids to Volleyball Life ids.

  python3 scripts/cbva_link.py           ->  data/cbva/link.json

CBVA is the one source with no published cross-reference: college publishes `vblId` and
Volleyball Life is native, but CBVA's player ids are its own namespace. So this has to be
inferred, and a name match alone will not do it -- in a pool of 292,000 players, "Emily
Nelson" is several different people.

What makes it tractable is that Volleyball Life carries the same CBVA events as
placings-only divisions, with the same entrants. So the evidence used here is not a name
but a *partnership on a date*: CBVA says these two names played together on 8 August, and
Volleyball Life has a team of two ids whose names are the same pair on the same day. One
such coincidence is already unlikely; the same pairing recurring across several dates, or
a player matching through several different partners, is conclusive.

Each agreement casts a vote. An id is accepted when its best candidate holds a clear
majority and at least MIN_VOTES agreements, which leaves the genuinely ambiguous
unresolved rather than guessing. The unresolved are reported, not hidden.
"""
import json, os, re, sys, unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
# A single agreement is already strong: it needs *both* partners' names to match the same
# Volleyball Life team on the same day, and that team to be the only one on that date with
# that pair of names. Requiring two agreements turned out to reject 4,108 players who had
# exactly one candidate and no contest at all, against 26 who were genuinely contested --
# so the bar is one uncontested agreement, and contested ids are left unresolved.
MIN_VOTES = 1
MAJORITY = 0.75        # share of a player's votes the winner must hold


def norm(name):
    """Fold to a comparable form: accents stripped, punctuation dropped, case ignored."""
    if not name:
        return ""
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z ]", " ", s.lower())
    return " ".join(s.split())


def vb_teams_by_date():
    """(date, frozenset of two normalised names) -> the id pairs seen there."""
    when = {t["id"]: (t.get("start") or "")[:10]
            for t in read_jsonl(os.path.join(DATA, "vb", "tournaments.jsonl"))}
    name = {}
    for p in read_jsonl(os.path.join(DATA, "vb", "players.jsonl")):
        n = norm(p.get("name") or f"{p.get('first') or ''} {p.get('last') or ''}")
        if n:
            name[p["id"]] = n
    idx = defaultdict(list)
    kept = 0
    for tm in read_jsonl(os.path.join(DATA, "vb", "teams.jsonl")):
        d = when.get(tm["tid"])
        ids = tm.get("p") or []
        if not d or len(ids) != 2:
            continue
        a, b = name.get(ids[0]), name.get(ids[1])
        if not a or not b or a == b:
            continue
        idx[(d, frozenset((a, b)))].append(tuple(ids))
        kept += 1
    print(f"indexed {kept} Volleyball Life teams across {len(idx)} date/name-pair keys")
    return idx, name


def cbva_teams():
    """CBVA teams as (date, two ids, two normalised names)."""
    name = {}
    for p in (json.loads(l) for l in open(os.path.join(DATA, "cbva", "players.jsonl"))):
        n = norm(p.get("name") or f"{p.get('first') or ''} {p.get('last') or ''}")
        if n:
            name[p["id"]] = n
    date = {}
    for d in (json.loads(l) for l in open(os.path.join(DATA, "cbva", "divisions.jsonl"))):
        date[d["tdId"]] = d.get("date") or ""
    out = []
    for tm in (json.loads(l) for l in open(os.path.join(DATA, "cbva", "teams.jsonl"))):
        ids = tm.get("p") or []
        if len(ids) != 2:
            continue
        a, b = name.get(ids[0]), name.get(ids[1])
        d = date.get(tm["tdId"], "")
        if a and b and a != b and d:
            out.append((d, tuple(ids), (a, b)))
    print(f"{len(out)} CBVA teams with two named players and a date, "
          f"{len(name)} CBVA players known")
    return out, name


def by_date(vbname):
    """date -> the Volleyball Life ids playing that day, keyed by normalised name."""
    when = {t["id"]: (t.get("start") or "")[:10]
            for t in read_jsonl(os.path.join(DATA, "vb", "tournaments.jsonl"))}
    out = defaultdict(lambda: defaultdict(set))
    for tm in read_jsonl(os.path.join(DATA, "vb", "teams.jsonl")):
        d = when.get(tm["tid"])
        if not d:
            continue
        for pid in tm.get("p") or []:
            n = vbname.get(pid)
            if n:
                out[d][n].add(pid)
    return out


def main():
    idx, vbname = vb_teams_by_date()
    teams, cbname = cbva_teams()

    votes = defaultdict(Counter)
    matched = 0
    for date, cids, (na, nb) in teams:
        hits = idx.get((date, frozenset((na, nb))))
        if not hits or len(hits) > 1:
            continue                 # no agreement, or the same pairing twice that day
        matched += 1
        vids = hits[0]
        # order the two sides the same way before pairing them off
        for cid in cids:
            for vid in vids:
                if cbname.get(cid) == vbname.get(vid):
                    votes[cid][vid] += 1

    link, ambiguous = {}, {}
    for cid, c in votes.items():
        vid, n = c.most_common(1)[0]
        total = sum(c.values())
        if n >= MIN_VOTES and n / total >= MAJORITY:
            link[cid] = {"vblId": vid, "votes": n, "of": total}
        else:
            ambiguous[cid] = {"best": vid, "votes": n, "of": total,
                              "candidates": len(c)}

    # Second pass, for players no partnership ever pinned down. Their name only has to
    # be unique among the ids playing that day, which is a far narrower claim than being
    # unique in a pool of 292,000 -- and it recovers the one-event player, who is exactly
    # who turns up in a local adult draw and whose absence kills a whole match.
    dates = defaultdict(set)
    for date, cids, _ in teams:
        for cid in cids:
            dates[cid].add(date)
    onday = by_date(vbname)
    taken = {v["vblId"] for v in link.values()}
    second = 0
    for cid, days in dates.items():
        if cid in link or cid in ambiguous:
            continue
        n = cbname.get(cid)
        hits = Counter()
        for d in days:
            for vid in onday.get(d, {}).get(n, ()):
                if vid not in taken:
                    hits[vid] += 1
        if len(hits) == 1:
            vid, k = hits.most_common(1)[0]
            link[cid] = {"vblId": vid, "votes": k, "of": k, "pass": 2}
            taken.add(vid)
            second += 1
    print(f"second pass linked {second} more by unique name on a shared date")

    seen = set()
    for tm in (json.loads(l) for l in open(os.path.join(DATA, "cbva", "matches.jsonl"))):
        seen.update(tm["a"] + tm["b"])
    resolved_in_play = len(seen & set(link))

    json.dump({"link": {str(k): v for k, v in link.items()},
               "ambiguous": {str(k): v for k, v in ambiguous.items()},
               "minVotes": MIN_VOTES, "majority": MAJORITY},
              open(os.path.join(DATA, "cbva", "link.json"), "w"), indent=1)

    print(f"\n{matched} of {len(teams)} CBVA teams found exactly one Volleyball Life team "
          f"with the same two names on the same day")
    print(f"resolved {len(link)} of {len(cbname)} CBVA players "
          f"({100 * len(link) // max(len(cbname), 1)}%)")
    print(f"  {len(ambiguous)} had votes but no clear winner")
    print(f"  {len(seen)} players appear in a CBVA match; "
          f"{resolved_in_play} of them resolved "
          f"({100 * resolved_in_play // max(len(seen), 1)}%)")


if __name__ == "__main__":
    main()
