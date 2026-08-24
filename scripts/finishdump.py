"""Download final standings for the tournaments that publish no match data.

  python3 scripts/finishdump.py     ->  data/finishes.jsonl

Forty-four percent of the tournaments in this corpus record only who finished where --
CBVA's Santa Cruz calendar among them, which is most of the adult volleyball a Northern
California junior can actually drive to. A rating fit on matches alone is blind to all of
it, so a player whose best recent results are CBVA Women's Open wins looks worse than she
is for the arithmetic reason that those wins are not in the data.

The tournament record carries every division's teams with a finish and player ids, which
is enough: a team that finished above another beat it, in the only sense the event
reports. scripts/rate.py turns those orderings into weighted pairwise observations.

Only tournaments absent from matches.jsonl are fetched. Where real matches exist they are
better evidence and the standings would double-count them.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
WORKERS = 8


def get(path, tries=4):
    for a in range(tries):
        try:
            r = urllib.request.Request(API + path, headers=HDRS)
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.6 * (a + 1))
    return None


def rows(tid, t):
    """One row per division: its teams, in finish order, as (finish, [player ids])."""
    out = []
    for d in (t or {}).get("divisions", []):
        if (d.get("numOfPlayers") or 0) != 2:
            continue                       # doubles only, as everywhere else
        teams = []
        for tm in d.get("teams") or []:
            if tm.get("isDeleted") or tm.get("drop") or tm.get("waitlist"):
                continue
            fin = tm.get("finish")
            ids = [p.get("playerProfileId") for p in (tm.get("players") or [])
                   if p.get("playerProfileId")]
            if fin and len(ids) == 2:
                teams.append([fin, sorted(ids)])
        if len(teams) >= 3:                # a two-team division says nothing a match cannot
            out.append({"tid": tid, "tdId": d["id"], "div": d.get("division") or "",
                        "date": (t.get("startDate") or "")[:10],
                        "name": (t.get("name") or "").strip(),
                        "teams": sorted(teams)})
    return out


def main():
    sched = {int(k): v for k, v in json.load(open(f"{DATA}/seedschedule.json")).items()}
    every = {t for v in sched.values() for t in v}
    withm = set()
    with open(f"{DATA}/matches.jsonl") as fh:
        for line in fh:
            withm.add(json.loads(line)["tid"])
    out = f"{DATA}/finishes.jsonl"
    done = set()
    if os.path.exists(out):
        with open(out) as fh:
            for line in fh:
                done.add(json.loads(line)["tid"])
    todo = sorted(every - withm - done)
    print(f"{len(every)} tournaments, {len(withm)} have matches, "
          f"{len(done)} already fetched, {len(todo)} to go", flush=True)

    t0, n, divs = time.time(), 0, 0
    with open(out, "a") as fh:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for tid, t in zip(todo, ex.map(lambda i: get(f"/tournament/{i}"), todo)):
                for row in rows(tid, t):
                    fh.write(json.dumps(row) + "\n")
                    divs += 1
                n += 1
                if n % 200 == 0:
                    fh.flush()
                    per = (time.time() - t0) / n
                    print(f"  {n}/{len(todo)}, {divs} divisions, "
                          f"{(len(todo) - n) * per / 60:.0f} min left", flush=True)
    print(f"done: {divs} doubles divisions with standings")


if __name__ == "__main__":
    main()
