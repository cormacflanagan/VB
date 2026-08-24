"""Phase 2 of the crawl: match-level results for every tournament vbcrawl.py indexed.

  python3 scripts/matchfeed.py            # resume or start
  python3 scripts/matchfeed.py --since 2019-01-01

Reads data/vb/teams.jsonl for the roster of each women's, girls' or coed doubles division
and asks the match feed for those players at that tournament. Writes data/vb/matches.jsonl.

The feed is priced by the length of the tournament list, not the player list -- one player
across her 69 tournaments costs 42 seconds, 1,181 players against a single tournament costs
9 -- so this asks about one tournament at a time and hands it everybody who played there.

Roughly half of all tournaments carry no match data at all; they publish a finish order and
nothing else. Those are not a failure, and their standings are already in teams.jsonl.
"""
import json, os, sys, time, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
        "Content-Type": "application/json"}
HERE = os.path.dirname(os.path.abspath(__file__))
VB = os.path.join(HERE, "..", "data", "vb")
WORKERS = 8
BATCH = 250


def post(path, body, tries=4):
    data = json.dumps(body).encode()
    for a in range(tries):
        try:
            r = urllib.request.Request(API + path, data=data, headers=HDRS)
            with urllib.request.urlopen(r, timeout=180) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.8 * (a + 1))
    return None


def targets(since):
    """tournament -> the doubles players to ask about, newest tournaments first."""
    doubles = set()
    for line in open(os.path.join(VB, "divisions.jsonl")):
        d = json.loads(line)
        if d.get("players") == 2 and not d.get("canceled"):
            doubles.add(d["tdId"])
    when = {}
    for line in open(os.path.join(VB, "tournaments.jsonl")):
        t = json.loads(line)
        when[t["id"]] = t.get("start") or ""
    by = defaultdict(set)
    for line in open(os.path.join(VB, "teams.jsonl")):
        tm = json.loads(line)
        if tm["tdId"] in doubles and not tm.get("drop"):
            by[tm["tid"]].update(tm["p"])
    out = {t: sorted(p) for t, p in by.items()
           if p and (not since or when.get(t, "") >= since)}
    return out, when


def rows(res, seen):
    out = []
    for blk in (res or {}).get("results", []):
        pid = blk.get("playerId")
        for m in blk.get("matches", []):
            mid = m.get("matchId")
            if mid is None or mid in seen:
                continue
            partners = [q.get("id") for q in (m.get("partners") or []) if q.get("id")]
            opps = [q.get("id") for q in (m.get("opponents") or []) if q.get("id")]
            if len(partners) != 1 or len(opps) != 2:
                continue
            seen.add(mid)
            out.append({"id": mid, "date": (m.get("date") or "")[:10],
                        "a": sorted([pid] + partners), "b": sorted(opps),
                        "aWon": bool(m.get("didWin")),
                        "sets": [[s.get("teamScore") or 0, s.get("opponentScore") or 0]
                                 for s in (m.get("sets") or [])],
                        "tid": blk.get("tournamentId"),
                        "tdId": blk.get("tournamentDivisionId"),
                        "phase": m.get("phase") or m.get("type"),
                        "round": m.get("roundName")})
    return out


def main(argv):
    since = argv[argv.index("--since") + 1] if "--since" in argv else None
    tgt, when = targets(since)
    out = os.path.join(VB, "matches.jsonl")
    donep = os.path.join(VB, "matchdone.json")
    done = set(json.load(open(donep))) if os.path.exists(donep) else set()
    seen = set()
    if os.path.exists(out):
        with open(out) as fh:
            for line in fh:
                seen.add(json.loads(line)["id"])
    # newest first: if this is ever cut short, the recent seasons are the ones that matter
    todo = sorted((t for t in tgt if t not in done), key=lambda t: when.get(t, ""),
                  reverse=True)
    print(f"{len(tgt)} tournaments with doubles rosters, {len(done)} done, "
          f"{len(todo)} to go; {len(seen)} matches held", flush=True)

    def fetch(t):
        players, got = tgt[t], []
        for i in range(0, len(players), BATCH):
            r = post("/playerprofile/feed/matches",
                     {"playerIds": players[i:i + BATCH], "tournamentIds": [t]})
            if r:
                got.append(r)
        return t, got

    t0, n, empty = time.time(), 0, 0
    with open(out, "a") as fh:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for t, res in ex.map(fetch, todo):
                before = len(seen)
                for r in res:
                    for row in rows(r, seen):
                        fh.write(json.dumps(row) + "\n")
                if len(seen) == before:
                    empty += 1
                done.add(t)
                n += 1
                if n % 100 == 0:
                    fh.flush()
                    json.dump(sorted(done), open(donep, "w"))
                    per = (time.time() - t0) / n
                    print(f"  {n}/{len(todo)} · {len(seen)} matches · {empty} with none · "
                          f"{(len(todo) - n) * per / 3600:.1f} h left", flush=True)
    json.dump(sorted(done), open(donep, "w"))
    print(f"done: {len(seen)} matches; {empty} tournaments published no match data")


if __name__ == "__main__":
    main(sys.argv[1:])
