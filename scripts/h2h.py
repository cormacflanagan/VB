"""Match-level head-to-head record between the players in a group.

Finishes only say who placed higher in the same field. This pulls the actual matches
from POST /playerprofile/feed/matches, so a head-to-head is a match the two players
contested on opposite sides of the net.

A match arrives once per player queried, so it is de-duplicated on matchId; the two
sides are reconstructed from the querying player plus her partners versus her
opponents. Pairs who played *together* are recorded separately as partnerships, not
as head-to-heads.
"""
import json, sys, time, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
        "Content-Type": "application/json"}


def post(path, body):
    data = json.dumps(body).encode()
    for a in range(4):
        try:
            r = urllib.request.Request(API + path, data=data, headers=HDRS)
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            time.sleep(0.6 * (a + 1))
    return None


def main(group):
    site = json.load(open(f"{group}_site.json"))
    clean = json.load(open(f"{group}_clean.json"))
    ids = {p["id"]: p["name"] for p in site["players"]}
    tids = {p["name"]: sorted({e["tid"] for e in clean["entries"][p["name"]]})
            for p in site["players"]}

    def fetch(p):
        res = post("/playerprofile/feed/matches",
                   {"playerIds": [p["id"]], "tournamentIds": tids[p["name"]]})
        return p, res

    matches = {}          # matchId -> (sideA set, sideB set, aWon, meta)
    got = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for p, res in ex.map(fetch, site["players"]):
            for blk in (res or {}).get("results", []):
                for m in blk.get("matches", []):
                    partners = m.get("partners") or []
                    opps = m.get("opponents") or []
                    if len(partners) != 1 or len(opps) != 2:
                        continue          # doubles only, same rule as the rest
                    mine = {p["id"]} | {q["id"] for q in partners if q.get("id")}
                    theirs = {q["id"] for q in opps if q.get("id")}
                    if not theirs:
                        continue
                    mid = m.get("matchId")
                    if mid in matches:
                        continue
                    sets = [(s["teamScore"], s["opponentScore"]) for s in (m.get("sets") or [])
                            if s["teamScore"] or s["opponentScore"]]
                    matches[mid] = {
                        "a": sorted(mine), "b": sorted(theirs), "aWon": bool(m.get("didWin")),
                        "sets": sets, "date": (m.get("date") or "")[:10],
                        "event": blk.get("tournament"), "division": blk.get("division"),
                        "tid": blk.get("tournamentId"), "tdId": blk.get("tournamentDivisionId"),
                        "phase": m.get("phase") or m.get("type"),
                        "round": m.get("roundName"),
                    }
            got += 1
    print(f"  {got} players queried, {len(matches)} distinct doubles matches")

    h2h = defaultdict(lambda: {"w": 0, "l": 0, "games": []})
    partnered = defaultdict(int)
    for mid, m in matches.items():
        A = [i for i in m["a"] if i in ids]
        B = [i for i in m["b"] if i in ids]
        for side in (m["a"], m["b"]):
            grp = [i for i in side if i in ids]
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    partnered[tuple(sorted((grp[i], grp[j])))] += 1
        for x in A:
            for y in B:
                k = (x, y)
                rec = h2h[k]
                if m["aWon"]:
                    rec["w"] += 1
                else:
                    rec["l"] += 1
                rec["games"].append({
                    "date": m["date"], "event": m["event"], "division": m["division"],
                    "tid": m["tid"], "tdId": m["tdId"], "phase": m["phase"],
                    "round": m["round"], "won": m["aWon"], "sets": m["sets"],
                    "with": [ids.get(i, i) for i in m["a"] if i != x],
                    "against": [ids.get(i, i) for i in m["b"] if i != y],
                })

    # fold the two directions into one record per unordered pair
    pairs = {}
    for (x, y), rec in h2h.items():
        k = tuple(sorted((x, y)))
        if k in pairs:
            continue
        fwd = h2h.get((k[0], k[1]), {"w": 0, "l": 0, "games": []})
        rev = h2h.get((k[1], k[0]), {"w": 0, "l": 0, "games": []})
        wins0 = fwd["w"] + rev["l"]
        wins1 = fwd["l"] + rev["w"]
        # rev games were recorded from the other player's side: flip result and scores
        games = fwd["games"] + [
            dict(g, won=not g["won"], sets=[(b, a) for a, b in g["sets"]])
            for g in rev["games"]]
        seen, uniq = set(), []
        for g in sorted(games, key=lambda z: z["date"]):
            sig = (g["date"], g["tdId"], tuple(tuple(s) for s in g["sets"]))
            if sig in seen:
                continue
            seen.add(sig)
            uniq.append(g)
        pairs[k] = {"a": ids[k[0]], "b": ids[k[1]], "aId": k[0], "bId": k[1],
                    "aWins": wins0, "bWins": wins1, "games": uniq}

    out = {"group": group, "players": {str(i): n for i, n in ids.items()},
           "matches": len(matches),
           "pairs": sorted(pairs.values(), key=lambda p: -(p["aWins"] + p["bWins"])),
           "partnered": [{"a": ids[k[0]], "b": ids[k[1]], "matches": v}
                         for k, v in sorted(partnered.items(), key=lambda kv: -kv[1])]}
    json.dump(out, open(f"{group}_h2h.json", "w"), indent=1)
    tot = sum(p["aWins"] + p["bWins"] for p in out["pairs"])
    print(f"  {len(out['pairs'])} head-to-head pairings, {tot} matches between group members")
    return out


if __name__ == "__main__":
    for g in (sys.argv[1:] or ["2028"]):
        print(f"=== {g}")
        main(g)
