"""Crawl CBVA's own API for the matches Volleyball Life does not carry.

  python3 scripts/cbva_api.py --index     # phase A: tournaments and divisions
  python3 scripts/cbva_api.py             # phase B: teams, pool games, playoff games

Volleyball Life records CBVA events as a finish order and nothing else, which is why a
player whose adult volleyball is a CBVA beach -- most of Northern California's -- had no
match record at all. CBVA publishes the games itself. The site is a React app talking to
a tRPC endpoint, and the four procedures it uses are public:

  tournaments.search      paginated listing, divisions inline with gender and team size
  tournaments.getTeams    entrants with seed, finish and player profiles
  tournaments.getPools    pool play, every match with set scores
  tournaments.getPlayoffs the bracket, same shape plus seeds and round

Player ids here are CBVA's own and do not match Volleyball Life's; scripts/cbva_link.py
resolves them by name afterwards. Ids are kept raw and namespaced rather than translated
in flight, so a bad name match can be corrected without re-crawling.
"""
import json, os, ssl, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://cbva.com/api/trpc"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "cbva")
WORKERS = 4
PAGE = 100
SINCE = "2022-01-01"   # the rating window is three years; older seasons cannot move it


def ctx():
    """Outbound HTTPS goes through an agent proxy whose CA must be trusted explicitly."""
    for p in (os.environ.get("SSL_CERT_FILE"), os.environ.get("REQUESTS_CA_BUNDLE"),
              "/root/.ccr/ca-bundle.crt"):
        if p and os.path.exists(p):
            return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()


CTX = ctx()


def trpc(proc, payload, tries=4):
    q = urllib.parse.urlencode({"input": json.dumps({"json": payload})})
    for a in range(tries):
        try:
            r = urllib.request.Request(f"{BASE}/{proc}?{q}",
                                       headers={"User-Agent": "Mozilla/5.0",
                                                "Accept": "application/json"})
            with urllib.request.urlopen(r, timeout=90, context=CTX) as resp:
                d = json.loads(resp.read().decode())
            out = d["result"]["data"]
            return out.get("json", out) if isinstance(out, dict) else out
        except Exception:
            time.sleep(0.7 * (a + 1))
    return None


def index():
    """Every tournament CBVA lists, with its divisions. Descriptions are dropped: they are
    Lexical documents of registration boilerplate and dwarf everything else."""
    os.makedirs(OUT, exist_ok=True)
    ft = open(os.path.join(OUT, "tournaments.jsonl"), "w")
    fd = open(os.path.join(OUT, "divisions.jsonl"), "w")
    page, nt, nd = 1, 0, 0
    while True:
        r = trpc("tournaments.search",
                 {"page": page, "pageSize": PAGE, "name": None, "divisions": [],
                  "venues": [], "genders": [], "past": True,
                  "startDate": "2005-01-01", "endDate": "2030-12-31"})
        if not r or not r.get("data"):
            break
        for t in r["data"]:
            ven = t.get("venue") or {}
            ft.write(json.dumps({
                "id": t["id"], "name": t.get("name"), "date": t.get("date"),
                "venueId": t.get("venueId"), "venue": ven.get("name"),
                "city": ven.get("city"), "state": ven.get("state"),
                "demo": bool(t.get("demo")), "visible": bool(t.get("visible"))}) + "\n")
            nt += 1
            for d in t.get("tournamentDivisions") or []:
                div = d.get("division") or {}
                fd.write(json.dumps({
                    "tid": t["id"], "date": t.get("date"), "tdId": d["id"],
                    "name": d.get("name"), "gender": d.get("gender"),
                    "size": d.get("teamSize"), "level": div.get("name"),
                    "maxAge": div.get("maxAge"), "status": d.get("status"),
                    "venue": ven.get("name")}) + "\n")
                nd += 1
        info = r.get("pageInfo") or {}
        print(f"  page {page}/{info.get('totalPages')}: {nt} tournaments, {nd} divisions",
              flush=True)
        if page >= (info.get("totalPages") or 0):
            break
        page += 1
    ft.close()
    fd.close()
    print(f"index: {nt} tournaments, {nd} divisions")


def sets_of(m):
    return [[s.get("teamAScore") or 0, s.get("teamBScore") or 0]
            for s in (m.get("sets") or [])]


def division(td, roster):
    """One division -> (team rows, match rows). Returns None if it has nothing played."""
    teams = trpc("tournaments.getTeams", {"tournamentDivisionId": td["tdId"]}) or []
    who, trows = {}, []
    for t in teams:
        ids = [p.get("playerProfileId") for p in ((t.get("team") or {}).get("players") or [])
               if p.get("playerProfileId")]
        if not ids:
            continue
        who[t["id"]] = sorted(ids)
        trows.append({"tid": td["tid"], "tdId": td["tdId"], "entryId": t["id"],
                      "seed": t.get("seed"), "finish": t.get("finish"),
                      "withdrawn": bool(t.get("withdrawnAt")),
                      "forfeited": bool(t.get("forfeited")), "p": sorted(ids)})
        for p in ((t.get("team") or {}).get("players") or []):
            pr = p.get("profile") or {}
            if pr.get("id"):
                roster[pr["id"]] = {
                    "id": pr["id"], "first": pr.get("firstName"),
                    "last": pr.get("lastName"), "pref": pr.get("preferredName"),
                    "name": " ".join(x for x in (pr.get("firstName"), pr.get("lastName")) if x)}

    mrows = []

    def add(m, phase, extra=None):
        a, b = who.get(m.get("teamAId")), who.get(m.get("teamBId"))
        # Gate on the winner, not on `status`. CBVA left the status of everything before
        # 2026 as "scheduled" even where the match was played, carries a winnerId and has
        # completed sets; filtering on status silently discarded every earlier season.
        if not a or not b or not m.get("winnerId"):
            return
        # "Pool" and "Playoff" share a first letter, and pool and playoff match ids are
        # separate sequences that overlap, so phase[0] collided 4,310 rows onto 3,000-odd
        # ids. Namespace them explicitly.
        tag = "cbp" if phase == "Pool" else "cbk"
        row = {"id": f"{tag}{m['id']}", "date": td["date"],
               "a": a, "b": b, "aWon": m["winnerId"] == m.get("teamAId"),
               "sets": sets_of(m), "tid": td["tid"], "tdId": td["tdId"],
               "phase": phase, "forfeit": bool(m.get("forfeitTeamId")),
               "status": m.get("status")}
        row.update(extra or {})
        mrows.append(row)

    for pool in (trpc("tournaments.getPools", {"tournamentDivisionId": td["tdId"]}) or []):
        for m in pool.get("matches") or []:
            add(m, "Pool", {"pool": pool.get("name")})
    for m in (trpc("tournaments.getPlayoffs", {"tournamentDivisionId": td["tdId"]}) or []):
        add(m, "Playoff", {"round": m.get("round"),
                           "seeds": [m.get("teamASeed"), m.get("teamBSeed")]})
    return trows, mrows


def main(argv):
    if "--index" in argv:
        return index()
    today = time.strftime("%Y-%m-%d")
    # The rating only looks back `window_days` (three years), so seasons before SINCE
    # cannot move a current number. The full archive reaches 2005 and is four times the
    # size; pass --since 2005-01-01 to take it when there is time to spend.
    since = argv[argv.index("--since") + 1] if "--since" in argv else SINCE
    divs = []
    for line in open(os.path.join(OUT, "divisions.jsonl")):
        d = json.loads(line)
        # doubles, women's or coed, already played, inside the horizon that matters
        if d.get("size") == 2 and (d.get("gender") or "") in ("female", "coed") \
                and since <= (d.get("date") or "") <= today:
            divs.append(d)
    donep = os.path.join(OUT, "done.json")
    done = set(json.load(open(donep))) if os.path.exists(donep) else set()
    todo = [d for d in divs if d["tdId"] not in done]
    todo.sort(key=lambda d: d["date"] or "", reverse=True)
    print(f"{len(divs)} women's/coed doubles divisions already played, "
          f"{len(done)} done, {len(todo)} to go", flush=True)

    # matches.jsonl is appended and the checkpoint is written every hundred divisions, so
    # a run killed mid-batch re-does up to a hundred divisions and appends them twice.
    # Holding the ids already on disk keeps a resume from duplicating them.
    written = set()
    mp = os.path.join(OUT, "matches.jsonl")
    if os.path.exists(mp):
        with open(mp) as fh:
            for line in fh:
                written.add(json.loads(line)["id"])

    roster = {}
    rp = os.path.join(OUT, "players.jsonl")
    if os.path.exists(rp):
        for line in open(rp):
            p = json.loads(line)
            roster[p["id"]] = p
    known = set(roster)

    ft = open(os.path.join(OUT, "teams.jsonl"), "a")
    fm = open(os.path.join(OUT, "matches.jsonl"), "a")
    fp = open(rp, "a")
    t0, n, nm = time.time(), 0, 0
    try:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for td, res in zip(todo, ex.map(lambda d: division(d, roster), todo)):
                trows, mrows = res
                for r in trows:
                    ft.write(json.dumps(r) + "\n")
                fresh = [r for r in mrows if r["id"] not in written]
                for r in fresh:
                    written.add(r["id"])
                    fm.write(json.dumps(r) + "\n")
                nm += len(fresh)
                done.add(td["tdId"])
                n += 1
                if n % 100 == 0:
                    for pid in set(roster) - known:
                        fp.write(json.dumps(roster[pid]) + "\n")
                    known = set(roster)
                    for f in (ft, fm, fp):
                        f.flush()
                    json.dump(sorted(done), open(donep, "w"))
                    per = (time.time() - t0) / n
                    print(f"  {n}/{len(todo)} divisions · {nm} matches · {len(roster)} "
                          f"players · {(len(todo) - n) * per / 60:.0f} min left", flush=True)
    finally:
        for pid in set(roster) - known:
            fp.write(json.dumps(roster[pid]) + "\n")
        for f in (ft, fm, fp):
            f.close()
        json.dump(sorted(done), open(donep, "w"))
    print(f"done: {nm} matches, {len(roster)} CBVA players")


if __name__ == "__main__":
    main(sys.argv[1:])
