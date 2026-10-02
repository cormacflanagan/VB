"""The age-eligible cohort's season calendar, and the season ahead.

  python3 scripts/cohort_calendar_page.py 2026_younger
      ->  docs/calendar-2026_younger.html

The class calendar (calendar_page.py) answers "where did one graduating year turn up".
A bracket does not work that way: an 18U field is grad 2026 *and younger*, so the girls a
2026 player actually meets include every strong 2027, 2028 and 2029 playing up. This is the
same calendar drawn for that whole field.

Two things it adds. The turnout table is the season just gone; underneath it is the season
ahead -- every fixture already posted that this cohort has a reason to look at, which is
where the p1440 Futures Tour lives. The Tour is listed in full whether or not anyone played
last year's edition, because a tour published as a season is a plan, not a result.
"""
import datetime, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendar_page import (CSS, CBVA, CBVA_URL, MIN_TURNOUT, SERIES, TIERS, VBL,
                           as_training, body, dfmt, esc, heat)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "docs")
# p1440 publishes the Futures Tour as a season, so it is listed whole rather than only
# where it matched something played last year.
P1440_ORGS = {41, 1144}
SEASON_FROM = "2026-09-15"
# announced but not yet rostered, so it cannot come from the roster scrape
NTDP_NEXT = [{"date": "2026-12-01", "endDate": "2026-12-31", "season": "Winter",
              "location": "not yet dated",
              "url": "https://usavolleyball.org/play/national-team-development-program"
                     "/beach-ntdp/beach-ntdp-training-series/"}]


def load(group):
    return (json.load(open(os.path.join(DATA, f"calendar_{group}.json"))),
            json.load(open(os.path.join(DATA, "upcoming_vb.json"))),
            json.load(open(os.path.join(HERE, f"roster_{group}.json"))))


def season_rows(D, feed):
    """Every fixture already posted for the season ahead that this cohort has a claim on.

    Three ways in, and the table says which: it is the next edition of something they
    played, it is a p1440 Futures Tour date, or it is a national championship. Anything
    else posted for the season is a local one-day draw and would bury the rest.
    """
    played = {}
    for e in D["events"]:
        if e.get("next"):
            played[e["next"]["id"]] = e
    out = []
    for t in feed:
        if t["startDate"] < SEASON_FROM:
            continue
        why = ("played" if t["id"] in played else
               "tour" if t["orgId"] in P1440_ORGS else
               "national" if t.get("national") else None)
        if not why:
            continue
        prev = played.get(t["id"])
        best = max(prev["brackets"], key=lambda b: b["t60"]) if prev else None
        out.append({"t": t, "why": why, "prev": prev, "best": best})
    out.sort(key=lambda r: (r["t"]["startDate"], r["t"]["name"]))
    return out


def juniors(t):
    """The girls' draws at an event, shortest sensible label."""
    seen, names = set(), []
    for d in t["divisions"]:
        n = re.sub(r"\s*\(.*?\)\s*", " ", d["name"]).strip()
        if n.lower() not in seen:
            seen.add(n.lower())
            names.append(n)
    return ", ".join(names[:5])


def build(group):
    D, feed, roster = load(group)
    wfrom, wto = D["window"]
    year = int(group[:4])

    events = []
    for e in D["events"]:
        keep = [b for b in e["brackets"] if b["t60"] >= MIN_TURNOUT]
        if keep:
            events.append(dict(e, brackets=keep))
    dropped = sum(len(e["brackets"]) for e in D["events"]) - \
        sum(len(e["brackets"]) for e in events)

    order = [(p["name"], p.get("id")) for p in
             json.load(open(os.path.join(DATA, f"{group}_site.json")))["players"]]
    tiers = {"t60": dict(order), "t30": dict(order[:30]), "t15": dict(order[:15])}
    events += [as_training(t, tiers) for t in SERIES["series"]
               if wfrom <= t["date"] <= wto]
    events.sort(key=lambda e: (e["date"], -max(b["t60"] for b in e["brackets"])))
    rowcount = sum(len(e["brackets"]) for e in events)

    months, cur = [], None
    for e in events:
        k = e["date"][:7]
        if k != cur:
            cur = k
            months.append((k, []))
        months[-1][1].append(e)

    def best(e):
        return max(b["t60"] for b in e["brackets"])

    peak = {k: max(best(x) for x in v) for k, v in months}
    mx = max(peak.values())
    bars = []
    for k, v in months:
        lab = datetime.date(int(k[:4]), int(k[5:7]), 1).strftime("%b")
        top = max(v, key=best)
        tb = max(top["brackets"], key=lambda b: b["t60"])
        bars.append(
            f'<div class="mb" title="{esc(lab)} {k[:4]} &#183; busiest: {esc(top["name"])} '
            f'&#183; {esc(tb["bracket"])} ({tb["t60"]} of 60)">'
            f'<span class="mbar" style="height:{peak[k] / mx * 100:.0f}%"></span>'
            f'<span class="mbn">{peak[k]}</span><span class="mbl">{lab}</span></div>')

    rows = []
    for k, v in months:
        d0 = datetime.date(int(k[:4]), int(k[5:7]), 1)
        rows.append(f'<tr class="mrow"><th colspan="9" scope="rowgroup">'
                    f'{d0.strftime("%B %Y")}<span class="mcount">{len(v)} event'
                    f'{"s" if len(v) != 1 else ""}</span></th></tr>')
        for e in v:
            dd = dfmt(e["date"])
            span = (f'&#8211;{dfmt(e["endDate"]).day}'
                    if e.get("endDate") and e["endDate"] != e["date"] else "")
            nxt = ""
            if e.get("next"):
                nxt = (f'<a class="lnk nx" href="{VBL}/tournament/{e["next"]["id"]}" '
                       f'target="_blank" rel="noopener">'
                       f'{dfmt(e["next"]["date"]).strftime("%-d %b %Y")}</a>')
            n = len(e["brackets"])
            rs = f' rowspan="{n}"' if n > 1 else ""
            for i, b in enumerate(e["brackets"]):
                cells = "".join(
                    f'<td class="ht h{heat(b[k2], size)}" '
                    f'title="{b[k2]} of the {label.lower()} played {esc(b["bracket"])}">'
                    f'{b[k2] or "&#183;"}</td>' for k2, size, label in TIERS)
                divs = ", ".join(esc(d["name"]) + (f' <i>&#215;{d["n"]}</i>' if d["n"] else "")
                                 for d in b["divisions"][:2])
                if b.get("roster"):
                    who = esc(", ".join(f"{a['first']} {a['last']}" for a in b["roster"]))
                    divs = f'<span title="{who}">{divs}</span>'
                href = (e["url"] if e.get("training")
                        else f'{VBL}/tournament/{e["tid"]}')
                lead = "" if i else f"""
        <td class="dt num"{rs}>{dd.strftime("%-d")}{span} <span class="dow">{dd.strftime("%a")}</span></td>
        <td class="evc"{rs}><a class="lnk" href="{href}" target="_blank"
          rel="noopener">{esc(e['name'])}</a>{
          '<span class="lt tr">training</span>' if e.get('training') else ''}</td>"""
                tail = "" if i else f"""
        <td class="loc"{rs}>{esc(e['location']) if e['location'] else '&#8212;'}</td>
        <td class="bdy"{rs}>{body(e)}</td>
        <td class="nxc"{rs}>{nxt or '<span class="dim">&#8212;</span>'}</td>"""
                cls = ("evs" if not i else "evc2") + (" trn" if e.get("training") else "")
                rows.append(f"""      <tr class="{cls}">{lead}
        <td class="brk"><b>{esc(b['bracket'])}</b><span class="dv">{divs}</span></td>
{cells}{tail}
      </tr>""")

    # ---- the season ahead
    sched = season_rows(D, feed)
    WHY = {"played": ('<span class="lt">returning</span>', "This cohort played the last edition"),
           "tour": ('<span class="lt tr">Futures Tour</span>', "A p1440 Futures Tour date"),
           "national": ('<span class="lt nat">national</span>', "A national championship")}
    smonths, cur = [], None
    for r in sched:
        k = r["t"]["startDate"][:7]
        if k != cur:
            cur = k
            smonths.append((k, []))
        smonths[-1][1].append(r)
    srows = []
    for k, v in smonths:
        d0 = datetime.date(int(k[:4]), int(k[5:7]), 1)
        srows.append(f'<tr class="mrow"><th colspan="6" scope="rowgroup">'
                     f'{d0.strftime("%B %Y")}<span class="mcount">{len(v)} date'
                     f'{"s" if len(v) != 1 else ""}</span></th></tr>')
        for r in v:
            t, b = r["t"], r["best"]
            dd = dfmt(t["startDate"])
            span = (f'&#8211;{dfmt(t["endDate"]).day}'
                    if t["endDate"] and t["endDate"] != t["startDate"] else "")
            tag, why = WHY[r["why"]]
            last = '<span class="dim">&#8212;</span>'
            if b:
                last = ("".join(
                    f'<span class="pill h{heat(b[k2], size)}" title="{b[k2]} of the '
                    f'{label.lower()}">{b[k2] or "&#183;"}</span>'
                    for k2, size, label in TIERS)
                    + f'<span class="dv">{esc(b["bracket"])} at '
                      f'{dfmt(r["prev"]["date"]).strftime("%-d %b %Y")}</span>')
            srows.append(f"""      <tr>
        <td class="dt num">{dd.strftime("%-d")}{span} <span class="dow">{dd.strftime("%a")}</span></td>
        <td class="evc"><a class="lnk" href="{VBL}/tournament/{t['id']}" target="_blank"
          rel="noopener">{esc(t['name'])}</a><span class="dv">{esc(juniors(t))}</span></td>
        <td class="loc">{esc(t['locations'][0]) if t['locations'] else '&#8212;'}</td>
        <td class="bdy">{esc(t['org'] or '&#8212;')}</td>
        <td class="bdy" title="{why}">{tag}</td>
        <td class="nxc">{last}</td>
      </tr>""")

    tour = [r for r in sched if r["why"] == "tour"]
    returning = [r for r in sched if r["why"] == "played"]
    classes = roster.get("classes") or {}
    older = sum(n for y, n in classes.items() if int(y) <= year)
    retrieved = datetime.date.today()

    return f"""<title>{year} and Younger &#183; Season calendar</title>
<style>{CSS}
.lt.nat {{ background:var(--gold-soft); color:var(--gold); }}
.pill {{ display:inline-block; min-width:22px; padding:1px 5px; margin-right:3px;
  border-radius:3px; font-size:12px; text-align:center; font-variant-numeric:tabular-nums; }}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">Girls beach volleyball &#183; {year} and younger &#183; Season calendar</p>
  <h1>Where the {year}-and-younger field <em>actually turns up</em></h1>
  <p class="standfirst">Every tournament the 60 highest-rated girls graduating in {year} or
  later contested in the twelve months to {dfmt(wto).strftime('%-d %B %Y')}, in calendar
  order, split by age bracket, with how many of the top 60, top 30 and top 15 entered each
  field. Underneath it, the season ahead: every date already posted that this field has a
  reason to look at, the p1440 Futures Tour included.</p>
  <div class="facts">
    <div class="fact"><b>{rowcount}</b><span>Brackets shown</span></div>
    <div class="fact"><b>{len(events)}</b><span>Across events</span></div>
    <div class="fact"><b>{max(best(e) for e in events)}</b><span>Biggest single field</span></div>
    <div class="fact"><b>{len(sched)}</b><span>Dates posted ahead</span></div>
    <div class="fact"><b>{len(tour)}</b><span>Futures Tour stops</span></div>
    <div class="fact"><b>{len(D['events'])}</b><span>Events entered in all</span></div>
  </div>
</header>

<section>
  <h2>The shape of the season</h2>
  <p class="lede">The biggest single field in each month &#8212; how many of the top 60 met in
  one bracket at the busiest event of that month.</p>
  <div class="months">{"".join(bars)}</div>
</section>

<section>
  <h2>The calendar</h2>
  <p class="lede">One row per <i>bracket</i>, not per event: the 18U field and the 17U field
  running beside it are separate competitions, so each is counted and judged on its own. Every
  bracket that drew at least {MIN_TURNOUT} of the top 60 is here, oldest first; {dropped}
  further brackets drew fewer and are left out. Shading runs on the share of each tier present,
  so the three columns are directly comparable: 12 of the top 15 shades darker than 21 of the
  top 30. The last column is this season's edition where one is already scheduled.</p>
  <p class="lede"><b>The NTDP training series</b>, marked <span class="lt tr">training</span>:
  invitational residential camps that produce no result, so their turnout columns count who was
  <i>selected</i>, not who entered. Rosters come from USA Volleyball, one row per girls' age
  group, with the names on hover.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Tournament</th><th scope="col">Bracket</th>
        <th scope="col" style="text-align:center">Top 60</th>
        <th scope="col" style="text-align:center">Top 30</th>
        <th scope="col" style="text-align:center">Top 15</th>
        <th scope="col">Location</th><th scope="col">Body</th>
        <th scope="col">This season</th>
      </tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>
  <div class="legend">
    <span class="key">Share of the tier present:</span>
    <span class="key"><span class="ramp"><span style="background:var(--h1)"></span>
      <span style="background:var(--h2)"></span><span style="background:var(--h3)"></span>
      <span style="background:var(--h4)"></span><span style="background:var(--h5)"></span>
      <span style="background:var(--h6)"></span></span> low &#8594; high</span>
    <span class="key"><span class="sw"></span> nobody from that tier</span>
  </div>
</section>

<section>
  <h2>This season</h2>
  <p class="lede">{len(sched)} dates from {dfmt(SEASON_FROM).strftime('%-d %B %Y')} onwards,
  in calendar order. A date earns its place three ways, and the tag says which:
  <span class="lt">returning</span> &#8212; this field played the last edition, and the right-hand
  column carries that turnout; <span class="lt tr">Futures Tour</span> &#8212; a p1440 Futures
  Tour date, listed whole because the Tour is published as a season rather than discovered
  one stop at a time; <span class="lt nat">national</span> &#8212; a national championship.
  Everything else posted this far out is a local one-day draw and would bury the rest.</p>
  <p class="lede">Read the right-hand column as <i>where the depth was</i>, not where it will
  be: these girls move up a bracket for the new season, so last year's 17U number describes a
  field they have now left.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Event</th><th scope="col">Location</th>
        <th scope="col">Run by</th><th scope="col">Why listed</th>
        <th scope="col">Last season 60&#8202;/&#8202;30&#8202;/&#8202;15</th>
      </tr></thead>
      <tbody>
{chr(10).join(srows)}
      </tbody>
    </table>
  </div>
</section>

<section class="notes">
  <h2>How to read it, and what it is not</h2>
  <ul>
    <li><b>This is a field, not a year group.</b> The cohort is everyone graduating in {year}
    or later, because that is who an 18U draw admits. {older} of the top 60 graduate in {year}
    itself; the rest are younger girls playing up, and they are the reason the field is harder
    than a single class would suggest.</li>
    <li><b>Turnout counts athletes, not teams.</b> A number is how many of that tier entered
    that bracket; a girl who played both the 18U and the 17U is counted in both rows, which is
    the point of splitting them.</li>
    <li><b>Brackets are folded onto the age they are actually played at.</b> Organisers label
    one field a dozen ways &#8212; "Girls 18U", "U18 Girls", "Girls 18:U (Grad Year 2026-2027)"
    and "Class of '26 &amp; Younger" are the same competition. An explicit age wins; failing
    that the youngest graduating year admitted sets the ceiling.</li>
    <li><b>Doubles only.</b> Club, 3v3 and 5v5 entries are excluded throughout: a placing in
    those says little about an individual.</li>
    <li><b>A blank in the last column means "not posted", not "not happening".</b> Only
    {len(returning)} of the {len(D['events'])} events this field entered have a new edition
    listed yet. Matching is by name after stripping years and ordinals, so a renamed event
    misses too.</li>
    <li><b>The forward schedule is as complete as Volleyball Life is.</b> It is rebuilt by
    walking tournament ids rather than read from a listing feed, so an event appears the day
    its organiser creates it there &#8212; and an event run off Volleyball Life does not appear
    at all. FIVB and international dates are out of scope.</li>
    <li><b>The training series are not tournaments.</b> They are invitational residential camps
    with no draw and no result, so Volleyball Life has no record of them; dates and rosters come
    from USA Volleyball. Their turnout columns count selections, not entries, and are not
    comparable with a tournament's.</li>
    <li><b>Locations come from the tournament record</b> and are blank where the organiser left
    them unset, which is common for one-day local events.</li>
  </ul>
</section>
<footer>
  {esc(D['label'])} by TruVolley, from a partner-graph crawl run on the predicate
  <i>graduating year &#8805; {year}</i>. Results, turnout and locations from Volleyball Life;
  the forward schedule from a crawl of tournament ids, both retrieved
  {retrieved.strftime('%-d %B %Y')}. Window {dfmt(wfrom).strftime('%-d %b %Y')} to
  {dfmt(wto).strftime('%-d %b %Y')}.
</footer>
</div>
"""


if __name__ == "__main__":
    g = sys.argv[1] if len(sys.argv) > 1 else "2026_younger"
    path = os.path.join(OUT, f"calendar-{g}.html")
    open(path, "w").write(build(g))
    print("wrote", path)
