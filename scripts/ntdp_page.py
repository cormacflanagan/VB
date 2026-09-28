"""The Beach NTDP attendance grid: who is named to a training-series roster, and when.

  python3 scripts/ntdp_page.py    ->  docs/ntdp-attendance.html

Reads the scraped rosters (ntdp_scrape.py) and the birthdates resolved against
Volleyball Life (ntdp_dob.py). Boys' and men's groups are dropped.

One grid per birth year. Because the age group is a birth-year cohort, a single
year's block shares an age ladder: every row steps up the bands together, so the
only thing that varies down the block is who keeps being named. Rows run by first
appearance, then by the length of the record.

Age bands fold to five rather than the seven the rosters use (U15 through U21).
Seven steps on one hue cannot clear the adjacent-lightness gate of the ordinal
ramp, and five is how USAV itself combines them -- "U17, U18", "U19/U20".
"""
import datetime, json, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ntdp_names import key

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "ntdp")
OUT = os.path.join(HERE, "..", "docs", "ntdp-attendance.html")
ORD = {"Spring": 0, "Summer": 1, "Fall": 2, "Winter": 3}
# Winter sits at the END of its series year: its rosters already use the next
# year's bands, which is visible in the data (2025 Winter U18 is all 2009 births).
MON = {"Spring": (5, 15), "Summer": (7, 26), "Fall": (9, 25), "Winter": (12, 15)}
BANDS = ["U15&#8211;U16", "U17", "U18", "U19", "U20&#8211;U21"]


def skey(s):
    y, q = s.split()
    return (int(y), ORD[q])


def band(div):
    """A combined group ("U19/U20") is filed under its lower bound."""
    ns = [int(x) for x in re.findall(r"U\s*-?\s*(\d{2})", str(div))]
    if not ns:
        return None, None
    n = min(ns)
    return n, (0 if n <= 16 else 1 if n == 17 else 2 if n == 18 else 3 if n == 19 else 4)


def load():
    """One record per athlete: her cells, her birthdate and her current rating."""
    rows = [r for r in json.load(open(os.path.join(DATA, "rosters.json")))
            if not re.match(r"(boys|men)", (r["division"] or ""), re.I)]
    players = json.load(open(os.path.join(DATA, "players.json")))

    def resolved(k):
        """Follow the fold left by ntdp_players.py for two names on one profile."""
        seen = set()
        while k in players and "same_as" in players[k] and k not in seen:
            seen.add(k)
            k = players[k]["same_as"]
        return k

    series = sorted({r["series"] for r in rows}, key=skey)
    girls = defaultdict(lambda: defaultdict(list))
    region = {}
    for r in rows:
        k = resolved(key(r["first"], r["last"]))
        # A girl can be listed twice in one series -- on her age-group roster and
        # on the national team named alongside it. That is one cell, not two rows.
        girls[k][r["series"]].append(str(r["division"]))
        # Keep the latest region USAV filed her under, as a fallback home.
        if r.get("region") and (k not in region or skey(r["series"]) > region[k][0]):
            region[k] = (skey(r["series"]), r["region"].strip())

    out = []
    for k, cells in girls.items():
        p = players.get(k, {})
        d = p.get("dob")
        d = d if d and "2002" <= d[:4] <= "2013" else None
        idx = [series.index(s) for s in cells]
        cs = {}
        for s, divs in cells.items():
            top = max(divs, key=lambda dv: (band(dv)[1] is not None, band(dv)[1] or 0))
            n, b = band(top)
            cs[series.index(s)] = {"g": " &#183; ".join(sorted(set(divs))), "n": n, "b": b}
        town = ", ".join(x for x in (p.get("city"), p.get("state")) if x)
        out.append({"name": p.get("name") or k.title(), "dob": d, "vid": p.get("id"),
                    "tv": p.get("tv"), "conf": p.get("conf") or 0, "m": p.get("m") or 0,
                    "town": town or None, "club": p.get("club"),
                    "region": region.get(k, (None, None))[1],
                    "first": min(idx), "last": max(idx), "n": len(cells), "cells": cs})
    return series, out


def age_at(dob, s):
    if not dob:
        return None
    b = datetime.date(*map(int, dob.split("-")))
    y, q = s.split()
    return round((datetime.date(int(y), *MON[q]) - b).days / 365.25, 1)


def grid(series, girls):
    head = "".join(f'<th class="sh"><span>{s.split()[1]}</span>'
                   f'<b>{s.split()[0][2:]}</b></th>' for s in series)
    body = []
    for g in girls:
        cells = []
        for i, s in enumerate(series):
            c = g["cells"].get(i)
            if not c:
                cells.append('<td class="c e"></td>')
                continue
            a = age_at(g["dob"], s)
            tip = f"{g['name']} &#8212; {s} &#183; {c['g']}" + (f" &#183; age {a}" if a else "")
            cells.append(f'<td class="c b{c["b"]}" title="{tip}">'
                         f'<span>{c["n"] or ""}</span></td>')
        nm = g["name"]
        if g["vid"]:
            nm = (f'<a href="https://volleyballlife.com/player/{g["vid"]}" '
                  f'target="_blank" rel="noopener">{nm}</a>')
        if g["tv"]:
            rating = (f'<b title="TruVolley {g["tv"]:.3f} &#183; confidence {g["conf"]} '
                      f'&#183; {g["m"]} matches">{g["tv"]:.2f}</b>')
        else:
            rating = '<i title="no Volleyball Life rating">&#8212;</i>'
        # Third line: where she is from and who she plays for. The profile's own
        # town wins; failing that, the USAV region she was last rostered under,
        # which is a region and not a town, so it is marked as one.
        where = g["town"] or (f'{g["region"]} region' if g["region"] else "")
        place = " &#183; ".join(x for x in (where, g["club"]) if x) or "&#8212;"
        body.append(f'<tr><th class="rh"><span class="nm">{nm}</span>'
                    f'<span class="by">{g["dob"][:4] if g["dob"] else "&#8212;"}'
                    f' &#183; {rating}</span>'
                    f'<span class="pl" title="{place.replace("&#183;", "-")}">{place}</span></th>'
                    f'{"".join(cells)}<td class="tot">{g["n"]}</td></tr>')
    return f"""<div class="gridbox">
    <table class="grid">
      <thead><tr><th class="corner">Athlete &#183; born &#183; TruVolley<br>Home &#183; club</th>{head}
        <th class="th-tot">All</th></tr></thead>
      <tbody>{''.join(body)}</tbody>
    </table>
  </div>"""


CSS = """
:root {
  color-scheme: light;
  --ground:#EFF1EE; --surface:#FAFBFA; --raise:#FFFFFF;
  --ink:#111B19; --body:#2C3A37; --muted:#5F6E6A; --faint:#8B9995;
  --line:#D5DCD9; --hair:#E4E9E7; --wash:#EAEDEB;
  --accent:#0B6E68; --accent-soft:#D9E7E5;
  --b0:#86b6ef; --b1:#3987e5; --b2:#256abf; --b3:#184f95; --b4:#0d366b;
  --onb0:#0b1a2e; --onb1:#ffffff; --onb2:#ffffff; --onb3:#ffffff; --onb4:#ffffff;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground:#0B1211; --surface:#121B19; --raise:#182322;
    --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
    --line:#243330; --hair:#1C2827; --wash:#161F1E;
    --accent:#57C3B6; --accent-soft:#123733;
    --b0:#184f95; --b1:#256abf; --b2:#3987e5; --b3:#86b6ef; --b4:#cde2fb;
    --onb0:#ffffff; --onb1:#ffffff; --onb2:#ffffff; --onb3:#0b1a2e; --onb4:#0b1a2e;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --ground:#0B1211; --surface:#121B19; --raise:#182322;
  --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
  --line:#243330; --hair:#1C2827; --wash:#161F1E;
  --accent:#57C3B6; --accent-soft:#123733;
  --b0:#184f95; --b1:#256abf; --b2:#3987e5; --b3:#86b6ef; --b4:#cde2fb;
  --onb0:#ffffff; --onb1:#ffffff; --onb2:#ffffff; --onb3:#0b1a2e; --onb4:#0b1a2e;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--ground); color:var(--body); font-size:15px; line-height:1.6;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; -webkit-font-smoothing:antialiased; }
.wrap { padding:0 clamp(16px,2.4vw,44px); padding-block:0 64px; }
header { padding-block:56px 30px; border-bottom:1px solid var(--line); }
.eyebrow { font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--accent);
  font-weight:650; margin:0 0 16px; }
h1 { font-family:"Iowan Old Style",Georgia,"Times New Roman",serif; font-size:clamp(31px,4.8vw,50px);
  line-height:1.06; letter-spacing:-.02em; color:var(--ink); margin:0 0 14px; font-weight:600;
  text-wrap:balance; max-width:20ch; }
h1 em { font-style:italic; color:var(--accent); }
.standfirst { font-size:17px; color:var(--muted); max-width:66ch; margin:0; }
h2 { font-family:"Iowan Old Style",Georgia,serif; font-size:24px; color:var(--ink); font-weight:600;
  margin:0 0 6px; text-wrap:balance; }
.lede { color:var(--muted); margin:0 0 20px; max-width:72ch; font-size:14.5px; }
section { padding-block:44px 0; }
p { max-width:70ch; }
.facts { display:flex; flex-wrap:wrap; margin-block:28px 0; border:1px solid var(--line);
  border-radius:3px; background:var(--surface); overflow:hidden; }
.fact { flex:1 1 150px; padding:14px 18px; border-right:1px solid var(--hair); }
.fact:last-child { border-right:0; }
.fact b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:23px;
  color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.fact span { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }
.gridbox { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  overflow:auto; max-height:80vh; width:max-content; max-width:100%; }
table.grid { border-collapse:separate; border-spacing:0; }
.grid th, .grid td { border-bottom:1px solid var(--hair); }
.grid thead th { position:sticky; top:0; z-index:2; background:var(--wash);
  border-bottom:1px solid var(--line); }
.corner { position:sticky; left:0; top:0; z-index:4 !important; width:252px; min-width:252px;
  text-align:left; padding:8px 12px; font-size:10.5px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--faint); font-weight:650; border-right:1px solid var(--line); }
.sh { width:34px; min-width:34px; padding:7px 2px; text-align:center; font-weight:650; }
.sh span { display:block; font-size:9px; letter-spacing:.04em; text-transform:uppercase; color:var(--faint); }
.sh b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  color:var(--muted); font-variant-numeric:tabular-nums; }
.th-tot { width:40px; min-width:40px; padding:7px 4px; font-size:10px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--faint); font-weight:650; }
.rh { position:sticky; left:0; z-index:1; background:var(--surface); width:252px; min-width:252px;
  text-align:left; padding:5px 10px 5px 12px; font-weight:500; border-right:1px solid var(--line); }
.nm { display:block; font-size:12.5px; color:var(--ink); white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; max-width:228px; }
.by { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px;
  color:var(--faint); font-variant-numeric:tabular-nums; }
.by b { color:var(--accent); font-weight:650; }
.pl { display:block; font-size:10px; color:var(--faint); white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; max-width:228px; }
.by i { font-style:normal; }
.nm a { color:inherit; text-decoration:none; border-bottom:1px solid transparent; }
.nm a:hover { border-bottom-color:var(--accent); }
.c { width:34px; min-width:34px; height:34px; text-align:center; padding:0;
  border-right:1px solid var(--surface); }
.c span { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px;
  font-weight:650; line-height:34px; font-variant-numeric:tabular-nums; }
.c.e { background:repeating-linear-gradient(-45deg,transparent,transparent 5px,var(--hair) 5px,var(--hair) 6px); }
.b0 { background:var(--b0); } .b0 span { color:var(--onb0); }
.b1 { background:var(--b1); } .b1 span { color:var(--onb1); }
.b2 { background:var(--b2); } .b2 span { color:var(--onb2); }
.b3 { background:var(--b3); } .b3 span { color:var(--onb3); }
.b4 { background:var(--b4); } .b4 span { color:var(--onb4); }
.tot { width:40px; min-width:40px; text-align:center; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:11px; color:var(--muted); font-variant-numeric:tabular-nums; border-left:1px solid var(--hair); }
.grid tbody tr:hover .rh { background:var(--raise); }
.yr { display:flex; align-items:baseline; gap:12px; margin:30px 0 8px; }
.yr h3 { font-family:"Iowan Old Style",Georgia,serif; font-size:19px; color:var(--ink);
  font-weight:600; margin:0; }
.yr .meta { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px;
  color:var(--faint); font-variant-numeric:tabular-nums; }
.legend { display:flex; flex-wrap:wrap; gap:8px 20px; align-items:center; margin-block:14px 0;
  font-size:12px; color:var(--muted); }
.k { display:inline-flex; align-items:center; gap:7px; }
.k i { width:20px; height:13px; border-radius:2px; display:inline-block; }
.k i.b0 { background:var(--b0); } .k i.b1 { background:var(--b1); } .k i.b2 { background:var(--b2); }
.k i.b3 { background:var(--b3); } .k i.b4 { background:var(--b4); }
.k i.ne { background:repeating-linear-gradient(-45deg,transparent,transparent 4px,var(--line) 4px,var(--line) 5px);
  border:1px solid var(--hair); }
.cols { display:grid; gap:26px; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); }
.panel { border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:auto; }
.panel table { border-collapse:collapse; width:100%; font-size:13.5px; }
.panel th, .panel td { padding:6px 12px; border-bottom:1px solid var(--hair); text-align:left; }
.panel th { font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint);
  font-weight:650; background:var(--wash); border-bottom:1px solid var(--line); }
td.n { text-align:right; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums; }
td.bar { width:44%; }
td.bar i { display:block; height:9px; border-radius:0 4px 4px 0; background:var(--accent); }
.notes li { margin:0 0 10px; font-size:14px; color:var(--muted); max-width:74ch; }
.notes b { color:var(--ink); font-weight:650; }
.notes ul { padding-left:19px; }
footer { margin-top:50px; padding-top:18px; border-top:1px solid var(--line); font-size:12px;
  color:var(--faint); max-width:80ch; }
@media (max-width:560px) { .corner,.rh { width:168px; min-width:168px; }
  .nm,.pl { max-width:146px; } }
"""


def build():
    import statistics as st
    from collections import Counter, defaultdict
    series, girls = load()
    n_slots = sum(g["n"] for g in girls)
    n_tv = sum(1 for g in girls if g["tv"])
    n_town = sum(1 for g in girls if g["town"])
    n_club = sum(1 for g in girls if g["club"])
    raw_names = len({f'{r["first"].strip()} {r["last"].strip()}' for r in
                     json.load(open(os.path.join(DATA, "rosters.json")))
                     if not re.match(r"(boys|men)", (r["division"] or ""), re.I)})
    today = datetime.date.today().strftime("%-d %B %Y")
    cnt = Counter(g["n"] for g in girls)
    ages = [age_at(g["dob"], series[g["first"]]) for g in girls if g["dob"]]
    undated = sum(1 for g in girls if not g["dob"])

    # One block per birth year. Within a year: first appearance, then the longest
    # records first, then name. Girls with no birthdate get their own block last.
    byyear = defaultdict(list)
    for g in girls:
        byyear[g["dob"][:4] if g["dob"] else None].append(g)
    years = sorted([y for y in byyear if y], key=int) + ([None] if None in byyear else [])

    blocks = []
    for y in years:
        # Strongest first. An unrated girl has no place on that scale, so she
        # sorts to the foot of the block rather than to the top as a zero.
        rows = sorted(byyear[y],
                      key=lambda g: (g["tv"] is None, -(g["tv"] or 0), g["name"]))
        once = sum(1 for g in rows if g["n"] == 1)
        places = sum(g["n"] for g in rows)
        label = f"Born {y}" if y else "Birth year unknown"
        span = ""
        if rows:
            lo, hi = min(g["first"] for g in rows), max(g["last"] for g in rows)
            span = f" &#183; {series[lo]} to {series[hi]}"
        blocks.append(
            f'<div class="yr"><h3>{label}</h3><span class="meta">{len(rows)} girls &#183; '
            f'{places} roster places &#183; {once} named once{span}</span></div>\n  '
            + grid(series, rows))

    ret = []
    for i in range(1, len(series)):
        prev = {g["name"] for g in girls if i - 1 in g["cells"]}
        cur = {g["name"] for g in girls if i in g["cells"]}
        ever = {g["name"] for g in girls if any(k < i for k in g["cells"])}
        ret.append((series[i], len(cur), len(cur & prev), len(cur - ever)))
    ret_rows = "".join(
        f'<tr><td>{s_}</td><td class="n">{c}</td><td class="n">{h}</td>'
        f'<td class="n">{nw}</td><td class="n">{round(100 * h / c)}%</td></tr>'
        for s_, c, h, nw in ret)
    dist = "".join(
        f'<tr><td class="n">{k}</td><td class="n">{v}</td>'
        f'<td class="bar"><i style="width:{100 * v / cnt[1]:.1f}%"></i></td></tr>'
        for k, v in sorted(cnt.items()))
    legend = "".join(f'<span class="k"><i class="b{i}"></i>{b}</span>'
                     for i, b in enumerate(BANDS))
    legend += '<span class="k"><i class="ne"></i>Not named</span>'

    html = f"""<title>Who Gets Called Back</title>
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="eyebrow">USA Volleyball &#183; Beach NTDP &#183; girls training series 2023&#8211;2026</p>
  <h1>Who gets <em>called back</em></h1>
  <p class="standfirst">Every girl named to a Beach NTDP training-series roster over four years,
  one row each, against the fifteen series that have been held. A filled cell is a roster
  appearance, and the number in it is the age group she attended as. One grid per birth year,
  because the age group is a birth-year cohort: a single year's block climbs the age ladder
  together, so the only thing that varies down a block is who keeps being named. Each name
  carries her birth year, her TruVolley rating as it stands today, and where she is from and
  who she plays for.</p>
  <div class="facts">
    <div class="fact"><b>{len(girls)}</b><span>Girls named</span></div>
    <div class="fact"><b>{n_slots}</b><span>Roster places</span></div>
    <div class="fact"><b>{cnt[1]}</b><span>Named exactly once</span></div>
    <div class="fact"><b>{st.median([g['n'] for g in girls]):.0f}</b><span>Median appearances</span></div>
    <div class="fact"><b>{st.median(ages):.1f}</b><span>Median age first named</span></div>
  </div>
</header>

<section>
  <h2>The grids</h2>
  <p class="lede">Series run left to right in the order they were held &#8212; Spring, Summer,
  Fall, then Winter, which falls at the end of its series year and already uses the next year's
  age bands. Within each birth year, rows run from the highest TruVolley down; the girls with no
  rating sit at the foot of the block.</p>
  <div class="legend">{legend}</div>
  {"".join(blocks)}
</section>

<section>
  <div class="cols">
    <div>
      <h2>Almost half never come back</h2>
      <p class="lede">How many series each girl has been named to.</p>
      <div class="panel"><table>
        <thead><tr><th>Series</th><th class="n">Girls</th><th></th></tr></thead>
        <tbody>{dist}</tbody>
      </table></div>
    </div>
    <div>
      <h2>Turnover, series by series</h2>
      <p class="lede">Of the girls on each roster, how many were on the one immediately before it,
      and how many had never been named to any earlier series.</p>
      <div class="panel"><table>
        <thead><tr><th>Series</th><th class="n">Named</th><th class="n">Held over</th>
          <th class="n">First time</th><th class="n">Held</th></tr></thead>
        <tbody>{ret_rows}</tbody>
      </table></div>
    </div>
  </div>
</section>

<section class="notes">
  <h2>How to read it</h2>
  <ul>
    <li><b>The order is today's rating, not the order they were picked in.</b> A block reads
    strongest-first on TruVolley as it stands now, which is hindsight: it puts the girls who turned
    out well at the top whatever their record looks like. Read down a block to see how much of the
    top of a birth year the programme kept calling back, and how much of it it only saw once.</li>
    <li><b>A gap is not a drop.</b> Plenty of girls miss a series and return. Reading across a row
    shows that invitation is decided series by series rather than as a standing place.</li>
    <li><b>A block shares one age ladder.</b> Because the band is set by birth year, every row in a
    block carries the same group number in the same column: birth year = series year &#8722; group
    number + 1. The Winter series is the exception that proves it &#8212; held at the end of its
    year, it already uses the following year's bands. What varies down a block is only who is
    still being named.</li>
    <li><b>The blocks are not the same size.</b> A birth year at the edge of the window has had
    fewer chances: 2012 has barely started and 2003 was already ageing out when the record
    begins.</li>
    <li><b>Home town and club are current, and self-reported.</b> Both come from the athlete's own
    Volleyball Life profile, so a club can be a season or two stale and some profiles carry none:
    {n_town} of the {len(girls)} girls give a town and {n_club} a club. Where the profile gives no
    town, the row falls back to the USAV region she was last rostered under, marked as a region
    rather than a town &#8212; that is a quarter of the country, not a home.</li>
    <li><b>The rating is today's, not the rating she held at the series.</b> TruVolley is a single
    current number per player, so a 2023 cell sits next to a 2026 rating. It says how good she
    turned out to be, not how good she looked when she was picked. {n_tv} of the {len(girls)} girls
    have one; it is blank for the rest, who either have no Volleyball Life profile or have never
    been rated. Hover a rating for its confidence and match count. All of them were refetched for
    this build, so they are on one side of the September 2026 rating replacement.</li>
    <li><b>Birth years come from Volleyball Life</b>, matched by name. {len(girls) - undated} of the
    {len(girls)} girls resolved to a profile carrying a date of birth; the other {undated} are in
    the last block. Where more than one profile carried the same name the one with a birthdate and
    the longest match record was taken, so a small number of birth years may be wrong.</li>
    <li><b>One girl, one row.</b> USAV spells the same athlete several ways &#8212; a footnote
    asterisk, a shouted surname, a nickname, a dropped middle name &#8212; and two spellings used
    to get two rows. Spellings are now folded together, and two names that resolve to the same
    Volleyball Life profile are merged even when the strings share nothing, which is what joins
    "Jess" to "Jessica Horwath". Same-surname pairs are not merged on a shared birthdate: Mallory
    and Molly LaBreche are twins, and several other pairs are sisters. That folding took
    {raw_names} roster spellings down to {len(girls)} athletes. A girl listed twice in one series,
    on her age group and on the national team named beside it, is one cell; the tooltip names
    both.</li>
    <li><b>Rosters only.</b> Being named is what this records. It says nothing about who attended,
    who was invited and declined, or who was cut.</li>
  </ul>
</section>
<footer>
  Rosters as published by USA Volleyball for the Beach NTDP training series, girls and women's
  groups only, 2023 through 2026. Fifteen series; the 2026 Winter series has not been dated.
  Birth years, TruVolley ratings, home towns and clubs from Volleyball Life player profiles,
  read {today}; regions from the USAV rosters themselves.
</footer>
</div>"""
    open(OUT, "w").write(html)
    print(f"wrote {OUT} ({len(html):,} bytes) -- {len(girls)} girls, {n_slots} places, "
          f"{len(blocks)} birth-year blocks")


if __name__ == "__main__":
    build()
