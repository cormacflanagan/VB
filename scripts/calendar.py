"""Tournament calendar for a class group: who turned up, event by event.

Aggregates the group's doubles entries up to the *event* (not division), counts how
many of the top 60 / 30 / 15 played, and joins locations from the tournament summaries
feed. Where the same event recurs in the coming season it is matched by name so the
calendar doubles as a planning list.

  python3 calendar.py 2027   ->  calendar_2027.json
"""
import json, re, sys
from collections import defaultdict


BRACKET_ORDER = ["18U", "17U", "16U", "15U", "14U", "Women's", "Coed", "Other"]


def bracket(div, season_end):
    """Fold a division name onto the age bracket it is actually played in.

    Organisers label the same field a dozen ways &mdash; "Girls 18U", "U18 Girls",
    "Girls 18:U (Grad Year 2026-2027)", "Class of '26 & Younger" are one competition.
    An explicit age wins; failing that the *youngest* graduating year admitted sets the
    ceiling, read against the season the window ends in. Combined brackets ("Girls
    18U/16U") take the older, which is the field you actually have to beat.
    """
    s = div.lower().replace("18:u", "18u")
    s = re.sub(r"(?<=[a-z])(?=\d)", " ", s)
    if "coed" in s or "co-ed" in s:
        return "Coed"
    ages = {int(m.group(1)) for m in re.finditer(r"\bu?\s?(1[2-8])\s?(?:u|under)?\b", s)}
    if ages:
        return f"{max(ages)}U"
    years = {int(y) for y in re.findall(r"\b(?:20)?(2[4-9])\b", s)}
    if years:
        age = 18 - (2000 + min(years) - season_end)
        return f"{age}U" if 12 <= age <= 18 else "Other"
    if "varsity" in s or "college" in s:
        return "18U"
    if "wom" in s or "open" in s or re.fullmatch(r"[^a-z]*aa?a?[^a-z]*", s):
        return "Women's"
    return "Other"


def norm(name):
    """Strip years and ordinals so the 2025-26 and 2026-27 editions of an event match."""
    s = name.lower()
    s = re.sub(r"\b(19|20)\d{2}([/-]\d{2})?\b", " ", s)
    s = re.sub(r"'\d{2}\b", " ", s)
    s = re.sub(r"\b\d+(st|nd|rd|th)\b", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\b(championships?|champ|open|tour|series|event|tournament|the|of|at|a)\b", " ", s)
    return " ".join(s.split())


def main(group):
    site = json.load(open(f"{group}_site.json"))
    clean = json.load(open(f"{group}_clean.json"))
    order = [p["name"] for p in site["players"]]
    tiers = {"t15": set(order[:15]), "t30": set(order[:30]), "t60": set(order)}

    summ = {}
    for f in ("past.json", "upcoming.json"):
        try:
            for t in json.load(open(f)):
                summ[t["id"]] = t
        except FileNotFoundError:
            pass

    season_end = int(site["window"][1][:4])
    ev = {}
    for name, rows in clean["entries"].items():
        for e in rows:
            tid = e["tid"]
            ti = clean["tour_info"][str(tid)]
            r = ev.setdefault(tid, {
                "tid": tid, "name": ti["name"], "date": ti["date"],
                "sanction": ti["sanction"] or "—", "players": set(),
                "brackets": defaultdict(lambda: {"players": set(), "divs": defaultdict(set),
                                                 "best": {}}),
                "best": {},
            })
            r["players"].add(name)
            g = r["brackets"][bracket(e["division"], season_end)]
            g["players"].add(name)
            g["divs"][e["division"]].add(name)
            for store in (r["best"], g["best"]):
                b = store.get(name)
                if b is None or e["finish"] < b[0]:
                    store[name] = (e["finish"], e["field"], e["division"])

    def finishers(best):
        return sorted(({"name": n, "f": f, "field": fl, "div": dv}
                       for n, (f, fl, dv) in best.items()), key=lambda x: x["f"])[:4]

    out = []
    for tid, r in ev.items():
        s = summ.get(tid) or {}
        locs = [x for x in (s.get("locations") or []) if x]
        counts = {k: len(r["players"] & v) for k, v in tiers.items()}
        brackets = []
        for b, g in r["brackets"].items():
            bc = {k: len(g["players"] & v) for k, v in tiers.items()}
            brackets.append({
                "bracket": b, "t15": bc["t15"], "t30": bc["t30"], "t60": bc["t60"],
                "divisions": [{"name": d, "n": len(p)} for d, p in
                              sorted(g["divs"].items(), key=lambda kv: -len(kv[1]))],
                "topFinishers": finishers(g["best"]),
            })
        brackets.sort(key=lambda x: (BRACKET_ORDER.index(x["bracket"])
                                     if x["bracket"] in BRACKET_ORDER else 99))
        divs = sorted(((d, p) for g in r["brackets"].values()
                       for d, p in g["divs"].items()), key=lambda kv: -len(kv[1]))
        out.append({
            "tid": tid, "name": r["name"], "date": r["date"],
            "endDate": s.get("endDate") or r["date"],
            "sanction": r["sanction"], "location": ", ".join(locs[:2]),
            "t15": counts["t15"], "t30": counts["t30"], "t60": counts["t60"],
            "brackets": brackets,
            "divisions": [{"name": d, "n": len(p)} for d, p in divs],
            "topFinishers": finishers(r["best"]),
        })
    out.sort(key=lambda x: (x["date"], -x["t60"]))

    # match each event to next season's edition, so the calendar is usable for planning
    nxt = {}
    for t in json.load(open("upcoming.json")):
        if t["startDate"] >= "2026-08-12":
            nxt.setdefault(norm(t["name"]), t)
    matched = 0
    for e in out:
        m = nxt.get(norm(e["name"]))
        if m:
            e["next"] = {"id": m["id"], "date": m["startDate"], "name": m["name"]}
            matched += 1

    json.dump({"group": group, "label": site["label"], "window": site["window"],
               "events": out, "matchedNext": matched}, open(f"calendar_{group}.json", "w"), indent=1)
    print(f"{len(out)} events; {matched} matched to a 2026-27 edition")
    print(f"\n{'DATE':11}{'60':>3}{'30':>3}{'15':>3}  EVENT")
    for e in sorted(out, key=lambda x: -x["t60"])[:20]:
        print(f"{e['date']} {e['t60']:>3}{e['t30']:>3}{e['t15']:>3}  {e['name'][:52]:52s} {e['location'][:22]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2027")
