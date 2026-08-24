"""Crawl every tournament on Volleyball Life into a local database.

  python3 scripts/vbcrawl.py            # phase 1: tournaments, divisions, teams, players
  python3 scripts/vbcrawl.py --from 1 --to 41044

Tournament ids are dense from 1 to about 41,044 and there is no public listing endpoint,
so the index is built by walking the ids. Each /tournament/{id} response carries every
division with its full team list -- player ids, seeds and final finishes -- which is the
whole standings database in one pass. Match-level results come afterwards, in matchfeed.py,
because those need a second request per tournament.

Writes normalised JSONL into data/vb/ rather than raw responses: the raw payloads run to a
gigabyte and almost all of it is registration plumbing.

  tournaments.jsonl   one row per tournament: name, dates, organiser, sanctioning body
  divisions.jsonl     one row per division: gender, age type, format, venue, team count
  teams.jsonl         one row per team: division, seed, finish, player ids
  players.jsonl       one row per player seen: name, grad year, club, city, commitment

Men's and boys' divisions are indexed but their teams are skipped -- the brief is women's
and girls' volleyball, and keeping their rosters would roughly double the corpus. Coed is
kept, because women play in it. Lift the filter in `wanted()` to take everything.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "vb")
LO, HI = 1, 41044
WORKERS = 10
CHUNK = 250


def get(path, tries=4):
    for a in range(tries):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None                   # a gap in the id range, not a failure
            time.sleep(0.6 * (a + 1))
        except Exception:
            time.sleep(0.6 * (a + 1))
    return None


def wanted(gender):
    """Women's, girls' and coed divisions. Men's and boys' are indexed but not rostered."""
    g = (gender or "").lower()
    return bool(g) and "men" not in g.replace("women", "") and "boy" not in g


def distil(t):
    """One tournament response -> (tournament row, division rows, team rows, players)."""
    org = t.get("organization") or {}
    trow = {"id": t["id"], "name": (t.get("name") or "").strip(),
            "start": (t.get("startDate") or "")[:10], "end": (t.get("endDate") or "")[:10],
            "org": (org.get("name") or "").strip() or None,
            "orgId": t.get("organizationId"),
            "sanction": (t.get("sanctioningBody") or {}).get("name")
                        if isinstance(t.get("sanctioningBody"), dict) else t.get("sanctioningBody"),
            "national": bool(t.get("national")), "public": bool(t.get("isPublic"))}
    divs, teams, players = [], [], {}
    for d in t.get("divisions") or []:
        loc = d.get("location") or {}
        gender = (d.get("gender") or {}).get("name")
        drow = {"tid": t["id"], "tdId": d["id"],
                "name": (d.get("division") or {}).get("name") if isinstance(d.get("division"), dict)
                        else d.get("division"),
                "gender": gender, "age": (d.get("ageType") or {}).get("name"),
                "players": d.get("numOfPlayers"), "surface": d.get("surfaceId"),
                "sport": d.get("sportId"), "complete": bool(d.get("complete")),
                "canceled": bool(d.get("canceled")),
                "venue": (loc.get("name") or "").strip() or None, "venueId": loc.get("id"),
                "teams": len(d.get("teams") or [])}
        divs.append(drow)
        if not wanted(gender):
            continue
        for tm in d.get("teams") or []:
            ids = []
            for p in tm.get("players") or []:
                pid = p.get("playerProfileId")
                if not pid:
                    continue
                ids.append(pid)
                if pid not in players:
                    players[pid] = {
                        "id": pid, "name": (p.get("name") or "").strip(),
                        "first": p.get("firstName"), "last": p.get("lastName"),
                        "grad": p.get("gradYear"), "club": p.get("club"),
                        "cityState": p.get("cityState"), "state": p.get("state"),
                        "hs": p.get("highSchool"), "commit": p.get("commitAbbr")}
            if ids:
                teams.append({"tid": t["id"], "tdId": d["id"], "teamId": tm.get("id"),
                              "seed": tm.get("seed"), "finish": tm.get("finish"),
                              "drop": bool(tm.get("drop") or tm.get("isDeleted")
                                           or tm.get("waitlist")),
                              "p": ids})
    return trow, divs, teams, players


def main(argv):
    lo = int(argv[argv.index("--from") + 1]) if "--from" in argv else LO
    hi = int(argv[argv.index("--to") + 1]) if "--to" in argv else HI
    os.makedirs(OUT, exist_ok=True)
    donep = os.path.join(OUT, "done.json")
    done = set(json.load(open(donep))) if os.path.exists(donep) else set()
    seen = set()
    pp = os.path.join(OUT, "players.jsonl")
    if os.path.exists(pp):
        with open(pp) as fh:
            for line in fh:
                seen.add(json.loads(line)["id"])
    todo = [i for i in range(lo, hi + 1) if i not in done]
    print(f"{hi - lo + 1} ids in range, {len(done)} already crawled, {len(todo)} to go; "
          f"{len(seen)} players held", flush=True)

    ft = open(os.path.join(OUT, "tournaments.jsonl"), "a")
    fd = open(os.path.join(OUT, "divisions.jsonl"), "a")
    fm = open(os.path.join(OUT, "teams.jsonl"), "a")
    fp = open(pp, "a")
    t0, n, nd, nt = time.time(), 0, 0, 0
    try:
        for i in range(0, len(todo), CHUNK):
            part = todo[i:i + CHUNK]
            with ThreadPoolExecutor(max_workers=WORKERS) as ex:
                got = list(ex.map(lambda x: (x, get(f"/tournament/{x}")), part))
            for tid, t in got:
                done.add(tid)
                if not t or not t.get("id"):
                    continue
                trow, divs, teams, players = distil(t)
                ft.write(json.dumps(trow) + "\n")
                for d in divs:
                    fd.write(json.dumps(d) + "\n")
                for tm in teams:
                    fm.write(json.dumps(tm) + "\n")
                for pid, p in players.items():
                    if pid not in seen:
                        seen.add(pid)
                        fp.write(json.dumps(p) + "\n")
                nd += len(divs)
                nt += len(teams)
            n += len(part)
            for f in (ft, fd, fm, fp):
                f.flush()
            json.dump(sorted(done), open(donep, "w"))
            per = (time.time() - t0) / max(n, 1)
            print(f"  {n}/{len(todo)} ids · {nd} divisions · {nt} teams · {len(seen)} players"
                  f" · {(len(todo) - n) * per / 60:.0f} min left", flush=True)
    finally:
        for f in (ft, fd, fm, fp):
            f.close()
        json.dump(sorted(done), open(donep, "w"))
    print(f"done: {len(seen)} players, {nt} team entries, {nd} divisions")


if __name__ == "__main__":
    main(sys.argv[1:])
