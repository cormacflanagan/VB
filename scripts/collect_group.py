"""Fetch Volleyball Life results for one NTDP roster and shape them into a matrix.

  python3 collect_group.py 17U

Writes <group>_clean.json (raw retrieved records) and <group>_site.json (render input).
Each (event, division) pair is treated as a separate competition.
"""
import json, os, sys, time, urllib.request, re
from collections import defaultdict
from rosters import GROUPS, WINDOW

API = "https://api-v8.volleyballlife.com"
HDRS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
COACH = ("coach", "coaches", "spectator", "parent")
THRESH = 3
# Doubles only. A pairs entry carries exactly one partner; club and 5v5 formats carry
# three or more, and a finish there reflects a squad rather than the individual. Roster
# size is the reliable test — division names are inconsistent ("Open (5v5)", "OPEN",
# "Club Division", "Girls Open (5 Pairs)" are all team events).
PAIRS_PARTNERS = 1


def req(path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    h = dict(HDRS)
    if data is not None:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(API + path, data=body, headers=h)
    for a in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if a == 4:
                print("  FAIL", path, e)
                return None
            time.sleep(2 ** a)


# beside this file, not beside the caller: the collector runs from the data directory
SHORT_OVERRIDES = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "shortnames.json")))
SUBS = [
    (r"^\d{4}[/-]?\d{0,2}\s+", ""), (r"^\d+(st|nd|rd|th)\s+", ""),
    (r"\bChampionships\b", "Champs"), (r"\bChampionship\b", "Champ"),
    (r"\bNational\b", "Nat'l"), (r"\bQualifier\b", "Qual"),
    (r"\bInvitational\b", "Invit"), (r"\bTournament\b", "Tourney"),
    (r"\bUSA Volleyball\b", "USAV"), (r"\bOrange County\b", "Orange Cty"),
    (r"\bHuntington Beach\b", "Huntington Bch"), (r"\bBeach Volleyball\b", "BVB"),
    (r"\bJuniors\b", "Jrs"), (r"\s+", " "),
]


def shorten(name, limit=26):
    s = name.strip()
    if s in SHORT_OVERRIDES:
        return SHORT_OVERRIDES[s]
    s = s.lstrip(", ")
    for pat, rep in SUBS:
        s = re.sub(pat, rep, s)
    s = s.strip(" -–,")
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0]
    return (cut or s[:limit]).rstrip(" -–,")


def cutnote(g, n):
    """One sentence on how close the cut-off was, for the methodology note."""
    cut = g.get("cut") or {}
    top, nxt, nm = cut.get("nTop"), cut.get("next"), cut.get("nextName")
    if not (top and nxt and nm):
        return ""
    return (f"The cut is tight: #{n + 1} is {nm} at {nxt:.3f}, "
            f"{top - nxt:.3f} behind #{n}.")


def main(group):
    g = GROUPS[group]
    lo, hi = WINDOW
    entries, tour_info, tv, dropped = {}, {}, {}, []

    for name, pid, region in g["roster"]:
        prof = req(f"/playerprofile/{pid}") or {}
        rating = req(f"/playerprofile/{pid}/truvolley") or {}
        rows = []
        for t in prof.get("tournaments", []):
            if not (lo <= t["date"][:10] <= hi):
                continue
            div = (t.get("division") or "").strip()
            if any(c in div.lower() for c in COACH) or t.get("finish") in (None, 0):
                continue
            partners = [p["name"] for p in (t.get("partners") or [])]
            if len(partners) != PAIRS_PARTNERS:
                dropped.append((name, div, len(partners)))
                continue
            rows.append({"tid": t["id"], "tdId": t.get("tdId"), "division": div,
                         "finish": t["finish"], "date": t["date"][:10],
                         "partners": partners})
            tour_info[str(t["id"])] = {"name": t["tournament"].strip(),
                                       "date": t["date"][:10],
                                       "sanction": t.get("sanctioningBodyId")}
        entries[name] = rows
        tv[name] = {"region": region, "id": pid, "club": prof.get("club"),
                    "height": prof.get("height"), "grad": prof.get("gradYear"),
                    "cityState": f'{prof.get("city")}, {prof.get("state")}',
                    "truvolley": rating.get("truVolley"), "peak": rating.get("peak"),
                    "conf": rating.get("confidence"),
                    "w": rating.get("wins"), "matches": rating.get("matchesPlayed")}
        print(f"  {name:24s} id={pid:6d} TV={tv[name]['truvolley']} entries={len(rows)}")
        time.sleep(0.25)

    tids = sorted({e["tid"] for v in entries.values() for e in v})
    print(f"  fetching division counts for {len(tids)} events")
    counts = {}
    for i in range(0, len(tids), 40):
        res = req("/Tournament/CountsV3Bulk", {"tournamentIds": tids[i:i + 40]})
        if res:
            counts.update(res)
        time.sleep(0.35)
    divcount = {d["id"]: d["teamCount"] for divs in counts.values() for d in (divs or [])}

    comp, who = {}, defaultdict(dict)
    for name, rows in entries.items():
        for e in rows:
            k = f'{e["tid"]}:{e["tdId"]}'
            ti = tour_info[str(e["tid"])]
            e["field"] = divcount.get(e["tdId"])
            comp[k] = {"key": k, "tid": e["tid"], "tdId": e["tdId"],
                       "event": ti["name"], "short": shorten(ti["name"]),
                       "division": e["division"], "field": e["field"],
                       "date": ti["date"], "sanction": ti["sanction"] or "—"}
            who[k][name] = e

    thresh = g.get("thresh", THRESH)
    cols = [dict(comp[k], n=len(m)) for k, m in who.items() if len(m) >= thresh]
    cols.sort(key=lambda c: (-c["n"], c["date"], c["division"]))

    order = sorted(tv, key=lambda n: -(tv[n]["truvolley"] or 0))
    pl = []
    for name in order:
        p = tv[name]
        pl.append({
            "name": name, "id": p["id"], "region": p["region"], "club": p["club"],
            "height": p.get("height"), "grad": p.get("grad"),
            "city": p["cityState"], "tv": p["truvolley"], "peak": p["peak"],
            "w": p["w"], "l": (p["matches"] or 0) - (p["w"] or 0),
            "comps": len({f'{x["tid"]}:{x["tdId"]}' for x in entries[name]}),
            "cells": {c["key"]: {"f": who[c["key"]][name]["finish"],
                                 "partners": who[c["key"]][name]["partners"]}
                      for c in cols if name in who[c["key"]]},
        })

    pairs = []
    for k, m in who.items():
        if len(m) == 2:
            c = dict(comp[k])
            c["players"] = sorted(({"name": n, "id": tv[n]["id"], "f": e["finish"]}
                                   for n, e in m.items()), key=lambda x: x["f"])
            pairs.append(c)
    pairs.sort(key=lambda c: c["date"], reverse=True)

    site = {"group": group, "label": g["label"], "window": WINDOW,
            "players": pl, "comps": cols, "pairs": pairs,
            "totalComps": len(who),
            "totalEvents": len({e["tid"] for v in entries.values() for e in v}),
            "totalEntries": sum(len(v) for v in entries.values()),
            "droppedTeam": len(dropped), "thresh": thresh,
            "population": g.get("population"), "ratedPop": g.get("ratedPop"),
            "cutNote": cutnote(g, len(pl))}
    json.dump({"entries": entries, "tour_info": tour_info, "tv": tv},
              open(f"{group}_clean.json", "w"), indent=1)
    json.dump(site, open(f"{group}_site.json", "w"), indent=1)

    dist = defaultdict(int)
    for m in who.values():
        dist[len(m)] += 1
    n = len(g["roster"])
    print(f"\n  dropped {len(dropped)} non-doubles entries (club/5v5/clinic)")
    print(f"  {n} athletes · {site['totalEvents']} events · {site['totalComps']} competitions")
    print("  players-per-competition:", dict(sorted(dist.items(), reverse=True)))
    print(f"  shared by {thresh}+: {len(cols)} · by exactly 2: {len(pairs)}")
    return site


if __name__ == "__main__":
    for grp in (sys.argv[1:] or ["18U", "17U"]):
        print(f"=== {grp}")
        main(grp)
