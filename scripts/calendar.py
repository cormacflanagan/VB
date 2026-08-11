"""Tournament calendar for a class group: who turned up, event by event.

Aggregates the group's doubles entries up to the *event* (not division), counts how
many of the top 60 / 30 / 15 played, and joins locations from the tournament summaries
feed. Where the same event recurs in the coming season it is matched by name so the
calendar doubles as a planning list.

  python3 calendar.py 2027   ->  calendar_2027.json
"""
import json, re, sys
from collections import defaultdict


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

    ev = {}
    for name, rows in clean["entries"].items():
        for e in rows:
            tid = e["tid"]
            ti = clean["tour_info"][str(tid)]
            r = ev.setdefault(tid, {
                "tid": tid, "name": ti["name"], "date": ti["date"],
                "sanction": ti["sanction"] or "—", "players": set(),
                "divisions": defaultdict(set), "best": {},
            })
            r["players"].add(name)
            r["divisions"][e["division"]].add(name)
            b = r["best"].get(name)
            if b is None or e["finish"] < b[0]:
                r["best"][name] = (e["finish"], e["field"], e["division"])

    out = []
    for tid, r in ev.items():
        s = summ.get(tid) or {}
        locs = [x for x in (s.get("locations") or []) if x]
        counts = {k: len(r["players"] & v) for k, v in tiers.items()}
        divs = sorted(r["divisions"].items(), key=lambda kv: -len(kv[1]))
        out.append({
            "tid": tid, "name": r["name"], "date": r["date"],
            "endDate": s.get("endDate") or r["date"],
            "sanction": r["sanction"], "location": ", ".join(locs[:2]),
            "t15": counts["t15"], "t30": counts["t30"], "t60": counts["t60"],
            "divisions": [{"name": d, "n": len(p)} for d, p in divs],
            "topFinishers": sorted(
                ({"name": n, "f": f, "field": fl, "div": dv}
                 for n, (f, fl, dv) in r["best"].items()),
                key=lambda x: x["f"])[:4],
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
