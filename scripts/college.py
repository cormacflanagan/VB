"""Crawl NCAA/JuCo college beach duals from the collegebeachvb.com backend.

  python3 scripts/college.py           # duals, matches and rosters
  python3 scripts/college.py --years 2020 2026

College beach is the level above the juniors this repo tracks, and it is where the girls
in it are heading -- Haisley to Santa Clara, Thais Treumann to TCU. Without it the rating
graph stops at the point players leave junior volleyball, so a committed senior's last
season is her whole record and everything after is invisible.

collegebeachvb.com is a Vue app over the same Volleyball Life API the rest of this repo
uses, under a /cbvb prefix. Four calls give the lot:

  college/list                     258 programmes with ids
  cbvb/team_scores?teamId=&year=   every dual that team played that season
  cbvb/latest_scores_detail?id=    the dual itself: five pairs, set scores, who won
  cbvb/roster?id=&year=            the roster, carrying playerProfileId

That last field is the useful one. College player ids are their own namespace, but the
roster maps each to a Volleyball Life playerProfileId, so college results join the junior
corpus on a published key rather than on a name match.

Note the API is served by IIS and answers HTTP/2 requests from curl with a bare 404 while
serving the same URL over HTTP/1.1 from urllib. Everything here uses urllib.
"""
import json, os, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "college")
YEARS = (2013, 2026)
WORKERS = 6


def get(path, tries=4, **q):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(q) if q else "")
    for a in range(tries):
        try:
            r = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            time.sleep(0.6 * (a + 1))
        except Exception:
            time.sleep(0.6 * (a + 1))
    return None


def duals(colleges, years):
    """Every competition id any programme played, with the season it belongs to."""
    jobs = [(c["id"], y) for c in colleges for y in years]
    found = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for (cid, y), rows in zip(jobs, ex.map(
                lambda j: get("cbvb/team_scores", teamId=j[0], year=j[1], last="false"),
                jobs)):
            for d in rows or []:
                if d.get("deleted"):
                    continue
                found.setdefault(d["fk_competition_id"], {"year": y, "row": d})
    return found


def rosters(colleges, years, fh):
    """collegeId x season -> roster rows, each carrying a Volleyball Life id."""
    jobs = [(c["id"], y) for c in colleges for y in years]
    n = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for (cid, y), r in zip(jobs, ex.map(
                lambda j: get("cbvb/roster", id=j[0], year=j[1]), jobs)):
            for p in (r or {}).get("roster", []) or []:
                fh.write(json.dumps({
                    "collegeId": cid, "year": y, "cbvbId": p.get("cbvbId"),
                    "vblId": p.get("playerProfileId"), "name": p.get("name"),
                    "recordId": p.get("recordId"), "cls": p.get("classYear") or p.get("year"),
                    "height": p.get("height"), "hometown": p.get("hometown")}) + "\n")
                n += 1
    return n


def flatten(cid, det):
    """One dual -> one row per pair match, in the same shape as the other corpora."""
    out = []
    date = (det.get("date") or "")[:10]
    for m in det.get("matches") or []:
        sides = m.get("teams") or []
        if len(sides) != 2:
            continue
        a, b = sides
        pa = [p["id"] for p in (a.get("players") or []) if p.get("id")]
        pb = [p["id"] for p in (b.get("players") or []) if p.get("id")]
        if len(pa) != 2 or len(pb) != 2:
            continue
        sa, sb = a.get("scores") or [], b.get("scores") or []
        if a.get("winner") is None and b.get("winner") is None:
            continue                      # scheduled but not played
        out.append({"id": f"c{m['id']}", "date": date, "a": sorted(pa), "b": sorted(pb),
                    "aWon": bool(a.get("winner")),
                    "sets": [[x, y] for x, y in zip(sa, sb)],
                    "tid": cid, "tdId": f"{cid}:{m.get('pair')}",
                    "pair": m.get("pair"), "phase": "Dual",
                    "div": det.get("division_group"), "loc": det.get("location"),
                    "teams": [a.get("id"), b.get("id")]})
    return out


def main(argv):
    y0, y1 = (int(argv[argv.index("--years") + 1]), int(argv[argv.index("--years") + 2])) \
        if "--years" in argv else YEARS
    years = list(range(y0, y1 + 1))
    os.makedirs(OUT, exist_ok=True)

    colleges = get("college/list") or []
    json.dump(colleges, open(os.path.join(OUT, "colleges.json"), "w"), indent=1)
    print(f"{len(colleges)} programmes, seasons {y0}-{y1}", flush=True)

    with open(os.path.join(OUT, "rosters.jsonl"), "w") as fh:
        n = rosters(colleges, years, fh)
    print(f"rosters: {n} player-seasons", flush=True)

    found = duals(colleges, years)
    print(f"{len(found)} distinct duals", flush=True)
    json.dump({str(k): v["row"] for k, v in found.items()},
              open(os.path.join(OUT, "duals.json"), "w"))

    donep = os.path.join(OUT, "done.json")
    done = set(json.load(open(donep))) if os.path.exists(donep) else set()
    todo = [c for c in sorted(found) if c not in done]
    print(f"{len(done)} duals already detailed, {len(todo)} to go", flush=True)

    t0, n, nm = time.time(), 0, 0
    with open(os.path.join(OUT, "matches.jsonl"), "a") as fh:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for cid, det in zip(todo, ex.map(
                    lambda c: get("cbvb/latest_scores_detail", id=c), todo)):
                for row in flatten(cid, det or {}):
                    fh.write(json.dumps(row) + "\n")
                    nm += 1
                done.add(cid)
                n += 1
                if n % 200 == 0:
                    fh.flush()
                    json.dump(sorted(done), open(donep, "w"))
                    per = (time.time() - t0) / n
                    print(f"  {n}/{len(todo)} duals · {nm} pair matches · "
                          f"{(len(todo) - n) * per / 60:.0f} min left", flush=True)
    json.dump(sorted(done), open(donep, "w"))
    print(f"done: {nm} pair matches from {len(done)} duals")


if __name__ == "__main__":
    main(sys.argv[1:])
