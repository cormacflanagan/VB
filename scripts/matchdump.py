"""Download match-level results for the 2027/2028/2029 classes.

  python3 scripts/matchdump.py            # resume or start
  python3 scripts/matchdump.py --floor 5  # widen the seed

Writes data/matches.jsonl -- one match per line, deduplicated on matchId -- which is the
input to scripts/rate.py.

The match feed is POST /playerprofile/feed/matches and takes both a player list and a
tournament list. Its cost is driven almost entirely by the *tournament* list: one player
across her 69 tournaments takes 42 seconds, while 1,181 players across a single tournament
takes 9. So this walks tournaments, not players, asking each one only about the seed
players who actually entered it.

Seeding is on rating rather than on the whole three classes. Every match involving at
least one seed player is captured with both sides intact, so opponents outside the seed
still enter the graph and still get rated -- the floor decides whose *schedule* is
crawled, not who is ranked. Below about 6.0 a player's matches are almost entirely
against others in the same range, which adds rows without connecting anything.
"""
import json, os, sys, time, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
GET = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
POST = dict(GET, **{"Content-Type": "application/json"})
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CLASSES = (2027, 2028, 2029)
FLOOR = 6.0
WORKERS = 6
BATCH = 250          # players per request; a huge list slows the query down


def req(path, body=None, tries=4, timeout=180):
    data = json.dumps(body).encode() if body is not None else None
    for a in range(tries):
        try:
            r = urllib.request.Request(API + path, data=data,
                                       headers=POST if body is not None else GET)
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(1.0 * (a + 1))
    return None


def seed(floor):
    pop = json.load(open(os.path.join(DATA, "cohort2027.json")))
    return sorted(int(k) for k, v in pop.items()
                  if v["grad"] in CLASSES and (v.get("tv") or 0) >= floor)


def schedules(ids):
    """player -> tournament ids, cached: this is the slow half and rarely changes."""
    path = os.path.join(DATA, "seedschedule.json")
    out = {}
    if os.path.exists(path):
        out = {int(k): v for k, v in json.load(open(path)).items()}
    todo = [i for i in ids if i not in out]
    print(f"schedules: {len(out)} cached, {len(todo)} to fetch", flush=True)
    for i in range(0, len(todo), 300):
        part = todo[i:i + 300]
        with ThreadPoolExecutor(max_workers=10) as ex:
            for pid, pr in zip(part, ex.map(lambda p: req(f"/playerprofile/{p}"), part)):
                out[pid] = sorted({t["id"] for t in (pr or {}).get("tournaments", [])})
        json.dump({str(k): v for k, v in out.items()}, open(path, "w"))
        print(f"  {min(i + 300, len(todo))}/{len(todo)}", flush=True)
    return out


def rows(res, seen):
    """Flatten one feed response into match rows, skipping anything not doubles."""
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
                continue                      # doubles only, as everywhere else in the repo
            seen.add(mid)
            sets = [[s.get("teamScore") or 0, s.get("opponentScore") or 0]
                    for s in (m.get("sets") or [])]
            out.append({"id": mid, "date": (m.get("date") or "")[:10],
                        "a": sorted([pid] + partners), "b": sorted(opps),
                        "aWon": bool(m.get("didWin")), "sets": sets,
                        "tid": blk.get("tournamentId"), "tdId": blk.get("tournamentDivisionId"),
                        "event": blk.get("tournament"), "div": blk.get("division"),
                        "phase": m.get("phase") or m.get("type"), "round": m.get("roundName")})
    return out


def main(argv):
    floor = float(argv[argv.index("--floor") + 1]) if "--floor" in argv else FLOOR
    ids = seed(floor)
    print(f"seed: {len(ids)} players in {CLASSES} rated {floor}+")
    sched = schedules(ids)

    entered = defaultdict(list)               # tournament -> seed players who were there
    for pid, tids in sched.items():
        for t in tids:
            entered[t].append(pid)
    print(f"{len(entered)} distinct tournaments, "
          f"{sum(len(v) for v in entered.values())} player-tournament pairs")

    out = os.path.join(DATA, "matches.jsonl")
    donep = os.path.join(DATA, "matchesdone.json")
    done = set(json.load(open(donep))) if os.path.exists(donep) else set()
    seen = set()
    if os.path.exists(out):
        with open(out) as fh:
            for line in fh:
                seen.add(json.loads(line)["id"])
    todo = [t for t in sorted(entered) if t not in done]
    print(f"{len(done)} tournaments done, {len(seen)} matches held, {len(todo)} to go",
          flush=True)

    def fetch(t):
        players = entered[t]
        got = []
        for i in range(0, len(players), BATCH):
            r = req("/playerprofile/feed/matches",
                    {"playerIds": players[i:i + BATCH], "tournamentIds": [t]})
            if r:
                got.append(r)
        return t, got

    t0, n = time.time(), 0
    with open(out, "a") as fh:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for t, res in ex.map(fetch, todo):
                for r in res:
                    for row in rows(r, seen):
                        fh.write(json.dumps(row) + "\n")
                done.add(t)
                n += 1
                if n % 50 == 0:
                    fh.flush()
                    json.dump(sorted(done), open(donep, "w"))
                    per = (time.time() - t0) / n
                    print(f"  {n}/{len(todo)} tournaments, {len(seen)} matches, "
                          f"{per:.1f}s each, {(len(todo) - n) * per / 60:.0f} min left",
                          flush=True)
    json.dump(sorted(done), open(donep, "w"))
    print(f"done: {len(seen)} distinct doubles matches from {len(done)} tournaments")


if __name__ == "__main__":
    main(sys.argv[1:])
