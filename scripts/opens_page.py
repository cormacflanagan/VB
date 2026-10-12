"""Where to play a women's open: the fields, and how many games you actually get.

  python3 scripts/opens_page.py    ->  docs/womens-open.html

Two questions, answered from the same data. Which draws are hard enough to be worth
entering, and which of them give an athlete more than the four matches a pool-plus-playoff
format hands everybody? They pull against each other: the hardest fields are the ones you
leave soonest.

Sources are CBVA's own tournament database (scripts/cbva_api.py), which carries the pools
and brackets Volleyball Life does not, and the Volleyball Life tournament crawl for the
AVP, p1440 and collegiate events CBVA does not run. Ratings are a snapshot in
data/opens_tv.json: current TruVolley for every entrant, applied to fields up to three
years old, so older events read a little stronger than they were.
"""
import datetime, html, json, os, re, statistics as st, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendar_page import CSS

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "docs", "womens-open.html")
VBL = "https://volleyballlife.com"
CBVA_URL = "https://cbva.com"

HER_ID = 64896
HER_CBVA = 28433
HER_NAME = "Haisley Flanagan"
# Her pair rating, not her own: she enters with partners rated 9.1-9.5, so the teams that
# outrank her team are the ones averaging above this, not above her 9.68.
PAIR = 9.50
SINCE = "2023-09-01"
TOP = ("open", "aaa")
# Every CBVA city, filed north to south. The region is the unit a reader plans around:
# one drive, one weekend, often one organiser's series.
REGIONS = [
    ("North Coast", ["Santa Cruz", "Monterey Bay"]),
    ("Central Coast", ["Santa Barbara", "Pismo Beach", "Ventura"]),
    ("Los Angeles", ["Malibu", "Pacific Palisades", "Santa Monica", "Playa del Rey",
                     "Los Angeles", "Manhattan Beach", "Hermosa Beach", "Long Beach"]),
    ("Orange County", ["Huntington Beach", "Bolsa Chica, Huntington Beach", "Newport Beach",
                       "Laguna Beach", "Dana Point"]),
    ("San Diego", ["Oceanside", "Del Mar, San Diego", "San Diego", "South Mission Beach",
                   "Coronado, San Diego", "Catamaran Resort, San Diego"]),
]
REGION = {c: r for r, cs in REGIONS for c in cs}
ALL_CA = set(REGION)
# Venues outside CBVA's vocabulary that the Volleyball Life scan should still count as
# California. CBVA covers the beaches; these are the inland and collegiate sites.
EXTRA_CA = ("cal poly", "san luis obispo", "slo ", "davis", "stanford", "pepperdine",
            "ucla", "usc", "long beach state", "sacramento", "fresno", "venice",
            "redondo", "torrance", "el segundo", "capitola", "half moon bay")
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def esc(s):
    return html.escape(str(s), quote=True)


def rows(name, d=None):
    with open(os.path.join(d or DATA, name)) as fh:
        return [json.loads(l) for l in fh]


def load():
    cb = os.path.join(DATA, "cbva")
    tn = {t["id"]: t for t in rows("tournaments.jsonl", cb)}
    dv = {d["tdId"]: d for d in rows("divisions.jsonl", cb)}
    tm = defaultdict(list)
    for t in rows("teams.jsonl", cb):
        tm[t["tdId"]].append(t)
    mt = defaultdict(list)
    for m in rows("matches.jsonl", cb):
        mt[m["tdId"]].append(m)
    link = json.load(open(os.path.join(cb, "link.json")))["link"]
    tv = json.load(open(os.path.join(DATA, "opens_tv.json")))
    return tn, dv, tm, mt, link, tv


def events(tn, dv, tm, mt, link, tv, cities, levels=TOP, since=SINCE):
    """One record per women's doubles draw: its field, and the games each team played."""
    def rate(pid):
        e = link.get(str(pid))
        return (tv.get(str(e["vblId"])) or {}).get("tv") if e else None

    out = []
    for tdid, d in dv.items():
        if d["gender"] != "female" or d["size"] != 2 or d["date"] < since:
            continue
        if d["level"] not in levels:
            continue
        t = tn.get(d["tid"]) or {}
        if t.get("city") not in cities:
            continue
        teams = [x for x in tm.get(tdid, []) if not x.get("withdrawn")]
        if not teams:
            continue
        per = Counter()
        for m in mt.get(tdid, []):
            for s in ("a", "b"):
                per[tuple(sorted(m[s]))] += 1
        games, top3, rated, above = [], [], [], 0
        for x in teams:
            g = per.get(tuple(sorted(x["p"])), 0)
            if g:
                games.append(g)
                if x.get("finish") and x["finish"] <= 3:
                    top3.append(g)
            r = [z for z in (rate(p) for p in x["p"]) if z]
            rated += r
            if len(r) == 2 and sum(r) / 2 > PAIR:
                above += 1
        out.append({"date": d["date"], "city": t.get("city"), "venue": t.get("venue"),
                    "level": d["level"], "tid": d["tid"], "teams": len(teams),
                    "games": games, "top3": top3, "rated": rated, "above": above})
    out.sort(key=lambda e: e["date"])
    return out


def agg(evs):
    """Collapse a venue's draws into the numbers that decide whether to enter."""
    yrs = len({e["date"][:4] for e in evs})
    rated = [z for e in evs for z in e["rated"]]
    games = [g for e in evs for g in e["games"]]
    top3 = [g for e in evs for g in e["top3"]]
    played = [e for e in evs if e["games"]]
    return {"n": len(evs), "per_year": len(evs) / max(yrs, 1),
            "teams": st.mean([e["teams"] for e in evs]),
            "above": st.mean([e["above"] for e in played]) if played else 0,
            "med": st.median(rated) if rated else 0,
            "p90": sorted(rated)[int(.9 * (len(rated) - 1))] if rated else 0,
            "n95": st.mean([sum(1 for z in e["rated"] if z >= 9.5) for e in evs]),
            "games": st.median(games) if games else 0,
            "top3": st.median(top3) if top3 else 0,
            "months": sorted({int(e["date"][5:7]) for e in evs}),
            "span": (min(e["date"] for e in evs), max(e["date"] for e in evs))}


def heat(share):
    for i, edge in enumerate((.001, .15, .30, .50, .72)):
        if share <= edge:
            return i + 1
    return 6


def her_record(dv, tm, link, tv):
    """Her own adult draws, so the page's benchmark is visible rather than asserted."""
    out = []
    for t in rows("teams.jsonl", os.path.join(DATA, "cbva")):
        if HER_CBVA not in t["p"]:
            continue
        d = dv.get(t["tdId"]) or {}
        if d.get("level") not in TOP + ("aa", "a"):
            continue
        other = [p for p in t["p"] if p != HER_CBVA]
        e = link.get(str(other[0])) if other else None
        rec = tv.get(str(e["vblId"])) if e else None
        out.append({"date": d["date"], "level": d["level"], "finish": t.get("finish"),
                    "partner": (rec or {}).get("name"), "ptv": (rec or {}).get("tv")})
    out.sort(key=lambda r: r["date"], reverse=True)
    return out


def vbl_janapr(tv, cbva_days, cbva_venues):
    """The AVP, p1440 and collegiate opens CBVA does not run, Jan-April, LA and SB.

    Volleyball Life also carries the CBVA events themselves, under names like "Women's Open
    at Ocean Park, Santa Monica". Those are the previous table, so they are dropped here by
    date: a draw held on a day CBVA ran one in the same town is CBVA's.
    """
    T = {t["id"]: t for t in rows("tournaments.jsonl", os.path.join(DATA, "vb"))}
    D = rows("divisions.jsonl", os.path.join(DATA, "vb"))
    ents = defaultdict(set)
    import gzip
    for path, op in ((os.path.join(DATA, "vb", "teams.jsonl.gz"), gzip.open),
                     (os.path.join(DATA, "vb", "teams.jsonl"), open)):
        if not os.path.exists(path):
            continue
        with op(path, "rt") as fh:
            for l in fh:
                x = json.loads(l)
                if not x.get("drop"):
                    ents[x["tdId"]].update(x["p"])
    # CBVA's own city and venue vocabulary covers the California beaches; EXTRA_CA adds
    # the collegiate and inland sites it has no reason to name.
    # CBVA's own city and venue vocabulary covers the California beaches; EXTRA_CA adds
    # the collegiate and inland sites it has no reason to name.
    vocab = {c.split(",")[0] for c in ALL_CA} | set(ALL_CA) | set(cbva_venues) | set(EXTRA_CA)
    pat = re.compile("|".join(re.escape(x) for x in sorted(vocab)), re.I)
    # Volleyball Life also carries the CBVA events themselves. They are named in a fixed
    # shape -- "Women's Open at Ocean Park, Santa Monica", or a bare date and venue -- so
    # the shape identifies them even on a day CBVA ran nothing else.
    cbva_named = re.compile(r"(^|\s)at .+?,\s|^\s*\d{1,2}/\d{1,2}/\d{2}", re.I)
    out = []
    for d in D:
        if d["players"] != 2 or d["gender"] not in ("Womens", "Girls"):
            continue
        if (d["name"] or "").strip().upper() not in ("OPEN", "AAA", "PRO"):
            continue
        t = T.get(d["tid"]) or {}
        s = t.get("start") or ""
        if not s or s < "2024-01-01" or int(s[5:7]) > 4 or d["teams"] < 8:
            continue
        where = (d.get("venue") or "") + " " + t.get("name", "")
        if not pat.search(where):
            continue
        if cbva_named.search(t.get("name", "")) or \
           any(c.lower() in where.lower() for c in cbva_days.get(s, ())):
            continue
        v = [tv[str(p)]["tv"] for p in ents.get(d["tdId"], ()) if tv.get(str(p), {}).get("tv")]
        if len(v) < 8:
            continue
        out.append({"date": s, "name": t.get("name"), "tid": t["id"], "teams": d["teams"],
                    "venue": d.get("venue") or "", "rated": len(v), "med": st.median(v),
                    "max": max(v), "n95": sum(1 for z in v if z >= 9.5),
                    "n105": sum(1 for z in v if z >= 10.5)})
    seen, uniq = set(), []
    for e in sorted(out, key=lambda e: (e["date"], -e["teams"])):
        k = (e["date"], e["name"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(e)
    return uniq


EXTRA = """
.bars { display:flex; align-items:flex-end; gap:10px; height:190px; padding:14px 6px 0;
  border:1px solid var(--line); border-radius:3px; background:var(--surface); }
.bar { flex:1; display:flex; flex-direction:column; justify-content:flex-end; height:100%;
  text-align:center; }
.bar i { display:block; background:var(--accent); border-radius:4px 4px 0 0; }
.bar.lo i { background:var(--accent-soft); }
.bar b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px;
  color:var(--ink); font-variant-numeric:tabular-nums; margin-bottom:4px; }
.bar span { display:block; font-size:11px; color:var(--muted); margin-top:6px; }
.grid2 { border-collapse:separate; border-spacing:0; width:auto; }
.grid2 th.vn { width:1%; }
.grid2 th.vn { text-align:left; padding:5px 12px 5px 0; font-weight:500; font-size:13px;
  color:var(--ink); white-space:nowrap; }
.grid2 td.mc { width:40px; min-width:40px; height:26px; text-align:center; padding:0;
  border:1px solid var(--surface); font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:11px; font-variant-numeric:tabular-nums; }
.grid2 thead th { font-size:10.5px; letter-spacing:.08em; text-transform:uppercase;
  color:var(--faint); font-weight:650; padding-bottom:6px; }
.tier { display:inline-block; font-size:10px; letter-spacing:.07em; text-transform:uppercase;
  font-weight:650; padding:2px 7px; border-radius:3px; white-space:nowrap; }
.t-pro { background:var(--gold-soft); color:var(--gold); }
.t-aim { background:var(--accent-soft); color:var(--accent); }
.t-vol { background:var(--wash); color:var(--muted); }
.rank { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-variant-numeric:tabular-nums; }
.win { color:var(--accent); font-weight:650; }
"""


def build():
    tn, dv, tm, mt, link, tv = load()
    la = events(tn, dv, tm, mt, link, tv, ALL_CA)
    home = {}
    for r, cities in REGIONS:
        for lv, key in ((TOP, "Open"), (("aa",), "AA"), (("a",), "A")):
            evs = events(tn, dv, tm, mt, link, tv, set(cities), lv)
            if evs:
                home[(r, key)] = agg(evs)
            elif key == "Open":
                home.setdefault((r, key), None)

    # ---- the format: how many games a team actually plays
    dist = Counter(g for e in la for g in e["games"])
    tot = sum(dist.values())
    mx = max(dist.values())
    bars = "".join(
        f'<div class="bar{"" if k >= 6 else " lo"}" title="{v} team-entries played {k} '
        f'{"match" if k == 1 else "matches"} &#8212; {100*v/tot:.0f}% of the field">'
        f'<b>{v}</b><i style="height:{92*v/mx:.0f}%"></i><span>{k}</span></div>'
        for k, v in sorted(dist.items()))

    # ---- venue table
    byven = defaultdict(list)
    for e in la:
        byven[(e["city"], e["venue"])].append(e)
    vrows = []
    for (c, v), evs in sorted(byven.items(), key=lambda kv: -agg(kv[1])["above"]):
        a = agg(evs)
        vrows.append(
            f'<tr><td class="evc"><b>{esc(v)}</b><span class="dv">{esc(c)} &#183; '
            f'{esc(REGION.get(c, "?"))}</span></td>'
            f'<td class="num rank">{a["per_year"]:.1f}</td>'
            f'<td class="num rank">{a["teams"]:.0f}</td>'
            f'<td class="num rank">{a["med"]:.2f}</td>'
            f'<td class="num rank">{a["n95"]:.1f}</td>'
            f'<td class="ht h{heat(a["above"]/5)}" title="On average {a["above"]:.1f} teams '
            f'in this draw average better than {PAIR:.2f}">{a["above"]:.1f}</td>'
            f'<td class="num rank">{a["games"]:.1f}</td>'
            f'<td class="num rank">{a["top3"]:.1f}</td>'
            f'<td class="dim">{", ".join(MON[m-1] for m in a["months"])}</td></tr>')

    # ---- season map: when each venue runs its open
    cal = defaultdict(Counter)
    for e in la:
        cal[(e["city"], e["venue"])][int(e["date"][5:7])] += 1
    order = sorted(cal, key=lambda k: -agg(byven[k])["above"])
    yrs = len({e["date"][:4] for e in la})
    cells = []
    for k in order:
        c, v = k
        tds = "".join(
            f'<td class="mc h{heat(cal[k][m]/yrs/1.2)}" title="{esc(v)} &#8212; '
            f'{cal[k][m]} open{"s" if cal[k][m] != 1 else ""} in {MON[m-1]} across {yrs} seasons">'
            f'{cal[k][m] or "&#183;"}</td>' for m in range(1, 13))
        cells.append(f'<tr><th class="vn" scope="row">{esc(v)}<span class="dv">{esc(c)}</span></th>{tds}</tr>')

    # ---- January to April
    ja = [e for e in la if int(e["date"][5:7]) <= 4]
    javen = defaultdict(list)
    for e in ja:
        javen[(e["city"], e["venue"])].append(e)
    jarows = []
    for (c, v), evs in sorted(javen.items(), key=lambda kv: -agg(kv[1])["above"]):
        a = agg(evs)
        when = ", ".join(datetime.date(*map(int, e["date"].split("-"))).strftime("%-d %b %y")
                         for e in evs)
        jarows.append(
            f'<tr><td class="evc"><b>{esc(v)}</b><span class="dv">{esc(c)}</span></td>'
            f'<td class="dim nw" style="font-size:12px">{when}</td>'
            f'<td class="num rank">{a["teams"]:.0f}</td>'
            f'<td class="num rank">{a["med"]:.2f}</td>'
            f'<td class="ht h{heat(a["above"]/5)}">{a["above"]:.1f}</td>'
            f'<td class="num rank">{a["games"]:.1f}</td>'
            f'<td class="num rank">{a["top3"]:.1f}</td></tr>')

    cbva_days = defaultdict(set)
    for e in la:
        cbva_days[e["date"]].add(e["city"])
        cbva_days[e["date"]].add(e["venue"])
    nc = vbl_janapr(tv, cbva_days, {e["venue"] for e in la})
    ncrows = "".join(
        f'<tr><td class="num dim nw">{datetime.date(*map(int, e["date"].split("-"))).strftime("%-d %b %y")}</td>'
        f'<td class="evc"><a class="lnk" href="{VBL}/tournament/{e["tid"]}" target="_blank" '
        f'rel="noopener">{esc(e["name"])}</a><span class="dv">{esc(e["venue"][:38])}</span></td>'
        f'<td class="num rank">{e["teams"]}</td>'
        f'<td class="num rank">{e["med"]:.2f}</td>'
        f'<td class="num rank">{e["max"]:.2f}</td>'
        f'<td class="num rank">{e["n95"]}</td>'
        f'<td class="num rank">{e["n105"]}</td>'
        f'<td><span class="tier {"t-pro" if e["med"] >= 10.0 else "t-aim" if e["med"] >= 9.3 else "t-vol"}">'
        f'{"out of reach" if e["med"] >= 10.0 else "step up" if e["med"] >= 9.3 else "level"}</span></td></tr>'
        for e in nc)

    # ---- her record
    rec = her_record(dv, tm, link, tv)
    def recrow(r):
        d = datetime.date(*map(int, r["date"].split("-"))).strftime("%-d %b %y")
        ptv = f'{r["ptv"]:.2f}' if r["ptv"] else "&#8212;"
        return (f'<tr><td class="num dim nw">{d}</td>'
                f'<td class="rank">{r["level"].upper()}</td>'
                f'<td class="rank{" win" if r["finish"] == 1 else ""}">'
                f'{r["finish"] or "&#8212;"}</td>'
                f'<td>{esc(r["partner"] or "&#8212;")}</td>'
                f'<td class="num rank">{ptv}</td></tr>')
    recrows = "".join(recrow(r) for r in rec)
    wins = sum(1 for r in rec if r["finish"] == 1 and r["level"] in TOP)
    # ---- the regions, north to south
    hrows = []
    for r, _ in REGIONS:
        a = home.get((r, "Open"))
        if a:
            cells_ = (f'<td class="num rank">{a["per_year"]:.1f}</td>'
                      f'<td class="num rank">{a["teams"]:.0f}</td>'
                      f'<td class="num rank">{a["med"]:.2f}</td>'
                      f'<td class="ht h{heat(a["above"]/8)}">{a["above"]:.1f}</td>'
                      f'<td class="num rank">{a["games"]:.1f}</td>'
                      f'<td class="dim">{", ".join(MON[m-1] for m in a["months"])}</td>')
        else:
            best = next((k for k in ("AA", "A") if home.get((r, k))), None)
            b = home.get((r, best)) if best else None
            note = (f'It tops out at {best}: {b["n"]} draw'
                    f'{"s" if b["n"] != 1 else ""} since 2023, median {b["med"]:.2f}.') if b \
                else "It has held no women&#8217;s doubles of any level."
            cells_ = f'<td class="dim" colspan="6">No open has been held here. {note}</td>'
        n = sum(1 for e in la if REGION.get(e["city"]) == r)
        hrows.append(f'<tr><td class="evc"><b>{esc(r)}</b>'
                     f'<span class="dv">{n} draw{"s" if n != 1 else ""}</span></td>{cells_}</tr>')

    sc = agg([e for e in la if e["city"] == "Santa Cruz"])
    la_best = max((agg(v) for v in byven.values()), key=lambda a: a["above"])
    best = [(k, agg(v)) for k, v in byven.items() if agg(v)["above"] >= 3
            and agg(v)["games"] >= 5]
    best.sort(key=lambda kv: -kv[1]["above"])
    sweet = ", ".join(f'<b>{esc(k[1])}</b>' for k, _ in best[:-1])
    sweet = f"{sweet} and <b>{esc(best[-1][0][1])}</b>" if len(best) > 1 else sweet
    today = datetime.date.today()

    return f"""<title>Where to Play a Women&#39;s Open</title>
<style>{CSS}{EXTRA}</style>

<div class="wrap">
<header>
  <p class="eyebrow">Girls beach volleyball &#183; every women&#8217;s open draw in
  California</p>
  <h1>Where to play a <em>women&#8217;s open</em></h1>
  <p class="standfirst">Which adult open draws are hard enough to be worth the drive, and
  which of them give you more than the four matches the format hands everybody. Every
  open held in California over three seasons, from Santa&#160;Cruz to San&#160;Diego. The
  two pull against each other: the hardest fields are the ones you leave soonest. Measured
  against a pair rating of {PAIR:.2f} &#8212; {HER_NAME} at {esc("9.68")} with the partners
  she actually enters with.</p>
  <div class="facts">
    <div class="fact"><b>{len(la)}</b><span>Open draws analysed</span></div>
    <div class="fact"><b>{tot:,}</b><span>Team entries</span></div>
    <div class="fact"><b>{len(byven)}</b><span>Venues</span></div>
    <div class="fact"><b>{dist[4]*100//tot}%</b><span>Played exactly 4</span></div>
    <div class="fact"><b>{sum(v for k, v in dist.items() if k >= 6)*100//tot}%</b><span>Played 6 or more</span></div>
    <div class="fact"><b>{SINCE[:7]}</b><span>Window opens</span></div>
  </div>
</header>

<section>
  <h2>Four games, unless you win</h2>
  <p class="lede">Every CBVA open runs the same shape &#8212; a pool, then a playoff &#8212;
  and the number of matches that produces barely moves with the size of the draw. An
  eight-team event and a forty-team event both hand a typical team four. Six or seven means
  a <b>top-three finish</b>, and that is the only lever there is.</p>
  <div class="bars">{bars}</div>
  <p class="lede" style="margin-top:12px">Team entries at the {len(la)} women&#8217;s opens
  held anywhere in California since
  {datetime.date(*map(int, SINCE.split("-"))).strftime("%B %Y")}. Shaded bars are the deep
  runs &#8212; {sum(v for k, v in dist.items() if k >= 6)} entries of {tot:,}. So the event
  to want is not the biggest or the hardest: it is the one where she is
  <i>inside the top handful</i>, because that is where the extra matches live.</p>
</section>

<section>
  <h2>The five regions</h2>
  <p class="lede">Every women&#8217;s open held in California since
  {datetime.date(*map(int, SINCE.split("-"))).strftime("%B %Y")}, gathered into the five
  stretches of coast CBVA runs on, north to south. The field hardens as you go south and
  the number of chances goes with it.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Region</th><th scope="col" class="num">Opens/yr</th>
        <th scope="col" class="num">Teams</th><th scope="col" class="num">Median TruVolley</th>
        <th scope="col" class="num">Teams above her</th>
        <th scope="col" class="num">Median games</th><th scope="col">Months</th>
      </tr></thead>
      <tbody>{"".join(hrows)}</tbody>
    </table>
  </div>
  <p class="lede" style="margin-top:14px">Two towns on the home coast hold none at all.
  <b>Monterey</b> tops out at AA and <b>Pismo&#160;Beach</b> at A, so the nearest open to
  Santa&#160;Cruz in either direction is Santa&#160;Cruz itself.
  <b>San&#160;Luis&#160;Obispo</b> is not CBVA and has held exactly one sand open ever
  &#8212; the Epic Cal&#160;Poly Smashdown of October 2024, 38 teams and a median of 9.20,
  with no edition since. What runs there now is the SLO&#160;SMASH <b>grass</b> series, and
  grass carries a separate rating: a player with a hundred grass matches and no sand has a
  sand TruVolley of zero. Grass results cannot move the number this page ranks on.</p>
</section>

<section>
  <h2>Every venue in the state</h2>
  <p class="lede">The same draws by venue rather than region, hardest field first. <b>Teams above her</b> counts the pairs in a typical field whose two players
  average better than {PAIR:.2f} &#8212; the teams she would actually have to beat. It is
  shaded on the same scale as the season map below.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Venue</th><th scope="col" class="num">Opens/yr</th>
        <th scope="col" class="num">Teams</th><th scope="col" class="num">Median TruVolley</th>
        <th scope="col" class="num">&#8805;9.5</th>
        <th scope="col" class="num">Teams above her</th>
        <th scope="col" class="num">Median games</th><th scope="col" class="num">If top&#8209;3</th>
        <th scope="col">Months</th>
      </tr></thead>
      <tbody>{"".join(vrows)}</tbody>
    </table>
  </div>
  <p class="lede" style="margin-top:14px">The trade is visible in two columns. The hardest
  venue on the list pairs {la_best["above"]:.1f} teams above her with a median of
  {la_best["games"]:.0f} games, because a hard field is a short day. The draws that give
  both &#8212; at least three teams above her <i>and</i> five games &#8212; are
  {sweet}. Those are the page&#8217;s answer.</p>
</section>

<section>
  <h2>When they happen</h2>
  <p class="lede">Opens held per month across the {yrs} seasons in the window, by venue,
  strongest field at the top. CBVA&#8217;s season is March to November and the good draws
  cluster in the middle of it. The blank winter is CBVA&#8217;s alone; the two dates that
  fill it belong to other organisers and are in the January&#8211;April tables below.</p>
  <div class="panel" style="padding:14px 16px">
    <table class="grid2">
      <thead><tr><th></th>{"".join(f'<th>{m}</th>' for m in MON)}</tr></thead>
      <tbody>{"".join(cells)}</tbody>
    </table>
  </div>
  <div class="legend">
    <span class="key">Opens per month:</span>
    <span class="key"><span class="ramp"><span style="background:var(--h1)"></span>
      <span style="background:var(--h2)"></span><span style="background:var(--h3)"></span>
      <span style="background:var(--h4)"></span><span style="background:var(--h5)"></span>
      <span style="background:var(--h6)"></span></span> none &#8594; every season</span>
  </div>
</section>

<section>
  <h2>January to April</h2>
  <p class="lede">CBVA has never run a women&#8217;s open in <b>January or February</b>
  &#8212; not once, in a database going back to 2005. Its season opens in the third week of
  March, and the March&#8211;April draws are the weakest of the year. Two winter dates exist
  outside CBVA, both at the top of the sport: the BNTDP Jr&#160;Pan&#160;Am Games Trials in
  January, which is an invitation, and Highline&#8217;s $5K Sponsorship Open at Ocean Park
  North on the last Saturday of February &#8212; 17 teams to a median of 10.01, nine of them
  above 10.5.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Venue</th><th scope="col">Dates it has run</th>
        <th scope="col" class="num">Teams</th><th scope="col" class="num">Median TruVolley</th>
        <th scope="col" class="num">Teams above her</th>
        <th scope="col" class="num">Median games</th><th scope="col" class="num">If top&#8209;3</th>
      </tr></thead>
      <tbody>{"".join(jarows)}</tbody>
    </table>
  </div>
  <h2 style="margin-top:34px">&#8230; and what CBVA does not run</h2>
  <p class="lede">The same window on Volleyball Life, which carries the AVP, p1440 and
  collegiate events. This is where the challenge actually is in early season &#8212; and
  where the trap is. The AVP League qualifiers are a professional tryout: a median above
  11.3, most of the field above 10.5, and a median of one and a half matches before you are
  out. <b>Out of reach</b> also covers the events that are not openly enterable at all: the
  USAV NORCECA playoffs and the FIVB BPT qualifiers are selection rather than entry, and so
  is the BNTDP Jr&#160;Pan&#160;Am Games Trials &#8212; the one January date in the whole
  window, and an invitation.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Event</th>
        <th scope="col" class="num">Teams</th><th scope="col" class="num">Median</th>
        <th scope="col" class="num">Best</th><th scope="col" class="num">&#8805;9.5</th>
        <th scope="col" class="num">&#8805;10.5</th><th scope="col">Tier</th>
      </tr></thead>
      <tbody>{ncrows}</tbody>
    </table>
  </div>
  <ul class="notes" style="margin-top:16px">
    <li><b>Aim here.</b> The AVP&#160;NEXT Huntington Beach Series in mid-April is the
    strongest non-professional field of the window; the AVP League Format open at Manhattan
    Beach Pier South in early March is the smallest but gave four matches, and its 2027
    edition is already in the system for 8&#160;March, not yet published.</li>
    <li><b>For volume, the third week of March at Newland</b>, Huntington Beach &#8212; run
    three years running, 21 to 22 teams, and the most matches of any draw in the window.</li>
    <li><b>Nothing here is bookable yet.</b> CBVA publishes about seven weeks ahead, so the
    late-March dates appear in early February; the AVP&#160;NEXT and Highline dates post six
    to eight weeks out.</li>
  </ul>
</section>

<section>
  <h2>The benchmark</h2>
  <p class="lede">Her own adult record, all of it at Santa Cruz: {len(rec)} draws, and
  {wins} open wins. The open she has outgrown is the one she can drive to.</p>
  <div class="cols">
    <div>
      <div class="panel"><table>
        <thead><tr><th scope="col">Date</th><th scope="col">Level</th>
          <th scope="col" class="num">Finish</th><th scope="col">Partner</th>
          <th scope="col" class="num">Partner TV</th></tr></thead>
        <tbody>{recrows}</tbody>
      </table></div>
    </div>
    <div>
      <p class="lede">Santa Cruz runs {sc["per_year"]:.0f} opens a year to a median of
      {sc["med"]:.2f}, with {sc["n95"]:.0f} players at 9.5 or better in a typical field. She
      is above the ninetieth percentile of that field ({sc["p90"]:.2f}) and has won the last
      three.</p>
      <p class="lede">Her pair rating is what the comparison runs on, not her own: she
      entered the 2026 opens with partners at 9.49 and 9.13, so a team averaging above
      {PAIR:.2f} is a team that outranks hers on paper. Change the partner and every
      &#8220;teams above her&#8221; number on this page moves.</p>
    </div>
  </div>
</section>

<section class="notes">
  <h2>How to read it, and what it is not</h2>
  <ul>
    <li><b>Ratings are current, the events are not.</b> Every entrant carries the TruVolley
    she holds today, applied to fields up to three years old, so an older draw reads a little
    stronger than it was. It says who turned out to be good, not who looked good on the day.</li>
    <li><b>Unrated entrants are left out of the medians.</b> They skew weak &#8212; inactive
    or unprofiled players &#8212; so every median here is slightly optimistic. At the thin
    venues (North Beach, Belmont Shore, Newland) only one or two pairs per draw are fully
    rated, so a zero in the &#8220;teams above her&#8221; column is a real signal but a soft
    one.</li>
    <li><b>Games are counted from the published pools and brackets</b>, so a team that
    forfeited or never checked in shows no matches and is dropped from the count rather than
    recorded as zero.</li>
    <li><b>Doubles only, and sand only.</b> Grass carries a separate TruVolley, as does coed
    and as do triples and quads: a player with a hundred grass or coed matches and no sand
    doubles has a sand rating of zero. None of those results can move the number this page
    ranks on.</li>
    <li><b>A draw existing is not a draw running.</b> Fields are listed as entered; CBVA
    cancels or merges small divisions, and the capacity published weeks out is not the field
    that shows up.</li>
  </ul>
</section>
<footer>
  CBVA tournaments, divisions, teams, pools and brackets from CBVA&#8217;s own API; AVP,
  p1440 and collegiate events from the Volleyball Life tournament crawl. TruVolley for
  {len(tv):,} entrants, retrieved {today.strftime("%-d %B %Y")}. Window
  {datetime.date(*map(int, SINCE.split("-"))).strftime("%-d %b %Y")} to
  {max(e["date"] for e in la)}.
</footer>
</div>
"""


if __name__ == "__main__":
    open(OUT, "w").write(build())
    print("wrote", OUT)
