"""Render the August warmth page: the annual series as an inline SVG line chart.

Change over time, so a line. Two series carry it -- what the observer wrote down, and
NOAA's homogenised version of the same station -- and each is drawn twice: the annual
values thin, and an 11-year centred mean heavy on top of them. Hue separates the two
sources (checked for colour-vision separation against the page's own surface), and the
homogenised one is dashed as well, so the pair never depends on colour alone.

Every year carries a hit target with its own numbers on hover, so the figure needs no
script, and the full table below is the same data in a form a reader can search.
"""
import html

W, H = 1060, 470
ML, MR, MT, MB = 58, 132, 18, 54
PW, PH = W - ML - MR, H - MT - MB
DRIFT = (2009, 2015)   # where this station runs 4-6 degF warm against Watsonville


def esc(s):
    return html.escape(str(s))


def _c(fahrenheit):
    return (fahrenheit - 32) * 5 / 9


def sgn(v, places=2):
    """A signed number with a real minus sign rather than a hyphen."""
    return f"{'+' if v >= 0 else '&#8722;'}{abs(v):.{places}f}"


def _paths(series, sx, sy):
    """Polyline points, split wherever a year is missing so a gap stays a gap."""
    runs, run, prev = [], [], None
    for y in sorted(series):
        if prev is not None and y != prev + 1:
            runs.append(run)
            run = []
        run.append(f"{sx(y):.1f},{sy(series[y]):.1f}")
        prev = y
    runs.append(run)
    return [" ".join(r) for r in runs if len(r) > 1]


def figure(d):
    obs = {r["year"]: r["mean_f"] for r in d["years"]
           if r["mean_f"] is not None and not r["short"]}
    adj = {r["year"]: r["adj_f"] for r in d["years"] if r["adj_f"] is not None}
    est = {r["year"] for r in d["years"] if r["adj_estimated"]}
    days = {r["year"]: r["days"] for r in d["years"]}
    short = {r["year"]: r["mean_f"] for r in d["years"] if r["short"]}

    import august_temps as A
    obs_sm, adj_sm = A.running(obs), A.running(adj)

    x0, x1 = min(min(obs), min(adj)) - 1, max(max(obs), max(adj)) + 1
    lo = min(min(obs.values()), min(adj.values())) - 1.2
    hi = max(max(obs.values()), max(adj.values())) + 1.2
    y0, y1 = int(lo // 2 * 2), int(-(-hi // 2) * 2)
    sx = lambda v: ML + (v - x0) / (x1 - x0) * PW
    sy = lambda v: MT + PH - (v - y0) / (y1 - y0) * PH
    step = PW / (x1 - x0)

    o = [f'<svg class="fig" viewBox="0 0 {W} {H}" role="img" width="100%" '
         f'aria-label="Mean August daily high temperature at Santa Cruz, one point per '
         f'year from {d["observed_span"][0]} to {d["adjusted_span"][1]}, as observed and '
         f'as homogenised by NOAA.">']

    # the stretch where the station reads warm against its neighbours, marked where it happens
    bx0, bx1 = sx(DRIFT[0] - 0.5), sx(DRIFT[1] + 0.5)
    o.append(f'<rect class="band" x="{bx0:.1f}" y="{MT}" width="{bx1-bx0:.1f}" '
             f'height="{PH}"><title>2009&#8211;2015: this station reads 4&#8211;6 &#176;F '
             f'warmer than Watsonville, against 1.3 &#176;F in the two decades before. A gap '
             f'that opens and closes against a neighbour is the station, not the '
             f'weather.</title></rect>')
    o.append(f'<text class="bandlab" x="{(bx0+bx1)/2:.0f}" y="{MT+13}">station drift</text>')

    for v in range(y0, y1 + 1, 2):
        y = sy(v)
        o.append(f'<line class="grid" x1="{ML}" y1="{y:.1f}" x2="{ML+PW}" y2="{y:.1f}"/>')
        o.append(f'<text class="tick ty" x="{ML-10}" y="{y+4:.1f}">{v}</text>')
    for v in range(1900, int(x1) + 1, 10):
        x = sx(v)
        o.append(f'<line class="grid" x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" y2="{MT+PH}"/>')
        o.append(f'<text class="tick tx" x="{x:.1f}" y="{MT+PH+22}">{v}</text>')
    o.append(f'<line class="axis" x1="{ML}" y1="{MT+PH}" x2="{ML+PW}" y2="{MT+PH}"/>')
    o.append(f'<line class="axis" x1="{ML}" y1="{MT}" x2="{ML}" y2="{MT+PH}"/>')
    o.append(f'<text class="axlab" transform="translate(14,{MT+PH/2:.0f}) rotate(-90)" '
             f'x="0" y="0">Mean daily high in August (&#176;F)</text>')

    for pts in _paths(adj, sx, sy):
        o.append(f'<polyline class="ln adj" points="{pts}"/>')
    for pts in _paths(obs, sx, sy):
        o.append(f'<polyline class="ln obs" points="{pts}"/>')
    for pts in _paths(adj_sm, sx, sy):
        o.append(f'<polyline class="ln adj sm" points="{pts}"/>')
    for pts in _paths(obs_sm, sx, sy):
        o.append(f'<polyline class="ln obs sm" points="{pts}"/>')

    # years the daily record is too thin to average, drawn as what they are: not a value
    for y in sorted(short):
        o.append(f'<line class="gap" x1="{sx(y):.1f}" y1="{MT+PH}" x2="{sx(y):.1f}" '
                 f'y2="{MT+PH-7}"><title>{y}: only {days[y]} of 31 days observed, so no '
                 f'monthly mean is drawn</title></line>')

    # the two extremes of the observed record, labelled rather than left to the reader
    hot = max(obs, key=obs.get)
    cold = min(obs, key=obs.get)
    for y, dy, anchor in ((hot, -13, "middle"), (cold, 20, "middle")):
        o.append(f'<circle class="mk" cx="{sx(y):.1f}" cy="{sy(obs[y]):.1f}" r="4"/>')
        o.append(f'<text class="ptlab" text-anchor="{anchor}" x="{sx(y):.1f}" '
                 f'y="{sy(obs[y])+dy:.1f}">{y} &#183; {obs[y]:.1f}&#176;</text>')

    # series names ride at the right end of each line, so the legend is not load-bearing
    last_o = max(obs)
    last_a = max(adj)
    o.append(f'<text class="endlab obs" x="{sx(last_o)+8:.0f}" y="{sy(obs[last_o])+4:.0f}">'
             f'as observed</text>')
    o.append(f'<text class="endlab adj" x="{sx(last_a)+8:.0f}" y="{sy(adj[last_a])+4:.0f}">'
             f'NOAA adjusted</text>')

    # one hit target per year: hover carries the numbers, so no script and no dots
    for y in range(int(min(obs)), int(max(adj)) + 1):
        bits = []
        if y in obs:
            bits.append(f"{obs[y]:.1f}&#176;F ({_c(obs[y]):.1f}&#176;C) observed, "
                        f"{days[y]} days")
        elif y in short:
            bits.append(f"only {days[y]} of 31 days observed")
        elif days.get(y, 0) == 0 and y <= d["observed_span"][1]:
            bits.append("no daily record")
        if y in adj:
            bits.append(f"{adj[y]:.1f}&#176;F adjusted"
                        + (", infilled from neighbours" if y in est else ""))
        o.append(f'<rect class="hit" x="{sx(y)-step/2:.1f}" y="{MT}" '
                 f'width="{step:.2f}" height="{PH}"><title>August {y} &#8212; '
                 f'{"; ".join(bits)}</title></rect>')

    o.append("</svg>")
    return "".join(o), hot, cold, obs, adj


FIG_CSS = """
.figwrap { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:18px 20px 10px; overflow-x:auto; }
.fig { display:block; min-width:820px; --obs:#00927E; --adj:#9A6B12; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .fig { --obs:#10A89A; --adj:#AD8412; }
}
:root[data-theme="dark"] .fig { --obs:#10A89A; --adj:#AD8412; }
.fig .grid { stroke:var(--hair); stroke-width:1; }
.fig .axis { stroke:var(--line); stroke-width:1; }
.fig .band { fill:var(--wash); stroke:var(--line); stroke-width:1;
  stroke-dasharray:3 4; }
.fig .bandlab { fill:var(--faint); font-size:10.5px; text-anchor:middle;
  letter-spacing:.09em; text-transform:uppercase;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
.fig .tick { fill:var(--faint); font-size:11px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-variant-numeric:tabular-nums; }
.fig .ty { text-anchor:end; }
.fig .tx { text-anchor:middle; }
.fig .axlab { fill:var(--muted); font-size:11.5px; text-anchor:middle;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; letter-spacing:.02em; }
.fig .ln { fill:none; stroke-linejoin:round; stroke-linecap:round; }
.fig .obs { stroke:var(--obs); }
.fig .adj { stroke:var(--adj); }
.fig .ln.obs { stroke-width:1.5; opacity:.5; }
.fig .ln.adj { stroke-width:1.5; opacity:.42; stroke-dasharray:3 3; }
.fig .ln.obs.sm { stroke-width:2.6; opacity:1; }
.fig .ln.adj.sm { stroke-width:2.4; opacity:1; stroke-dasharray:8 4; }
.fig .gap { stroke:var(--faint); stroke-width:2; opacity:.6; }
.fig .mk { fill:var(--obs); stroke:var(--surface); stroke-width:2; }
.fig .ptlab { fill:var(--ink); font-size:11.5px; font-weight:600;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; paint-order:stroke; stroke:var(--surface); stroke-width:3px; }
.fig .endlab { font-size:11.5px; font-weight:650; paint-order:stroke; stroke:var(--surface);
  stroke-width:3px; font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
.fig .endlab.obs { fill:var(--obs); stroke-width:3px; }
.fig .endlab.adj { fill:var(--adj); stroke-width:3px; }
.fig .hit { fill:transparent; }
.fig .hit:hover { fill:var(--accent-soft); opacity:.5; }
.figcap { color:var(--faint); font-size:12px; margin:10px 0 0; max-width:82ch; }
.keys { display:flex; flex-wrap:wrap; gap:18px; margin:14px 0 0; align-items:center; }
.keys .k { display:flex; align-items:center; gap:8px; font-size:12px; color:var(--muted); }
.keys .sw { width:26px; height:0; border-top-width:2.6px; border-top-style:solid; }
.keys .sw.obs { border-color:#00927E; }
.keys .sw.adj { border-color:#9A6B12; border-top-style:dashed; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .keys .sw.obs { border-color:#10A89A; }
  :root:not([data-theme="light"]) .keys .sw.adj { border-color:#AD8412; }
}
:root[data-theme="dark"] .keys .sw.obs { border-color:#10A89A; }
:root[data-theme="dark"] .keys .sw.adj { border-color:#AD8412; }
"""


SHELL_CSS = """
:root {
  --ground:#EFF1EE; --surface:#FAFBFA; --raise:#FFFFFF;
  --ink:#111B19; --body:#2C3A37; --muted:#5F6E6A; --faint:#8B9995;
  --line:#D5DCD9; --hair:#E4E9E7; --wash:#EAEDEB;
  --accent:#0B6E68; --accent-soft:#D9E7E5; --gold:#9A6B12; --gold-soft:#F3E4C4;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0B1211; --surface:#121B19; --raise:#182322;
    --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
    --line:#243330; --hair:#1C2827; --wash:#161F1E;
    --accent:#57C3B6; --accent-soft:#123733; --gold:#DCA84A; --gold-soft:#382B12;
  }
}
:root[data-theme="dark"] {
  --ground:#0B1211; --surface:#121B19; --raise:#182322;
  --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
  --line:#243330; --hair:#1C2827; --wash:#161F1E;
  --accent:#57C3B6; --accent-soft:#123733; --gold:#DCA84A; --gold-soft:#382B12;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; font-size:15px;
  line-height:1.6; -webkit-font-smoothing:antialiased; }
.wrap { max-width:none; margin:0; padding:0 clamp(18px,2.4vw,44px); }
header { padding:60px 0 32px; border-bottom:1px solid var(--line); }
.eyebrow { font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin:0 0 18px; }
h1 { font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(32px,5vw,50px); line-height:1.06; letter-spacing:-.02em; color:var(--ink);
  margin:0 0 16px; font-weight:600; text-wrap:balance; max-width:22ch; }
h1 em { font-style:italic; color:var(--accent); }
.standfirst { font-size:17px; color:var(--muted); max-width:68ch; margin:0; }
h2 { font-family:"Iowan Old Style",Georgia,"Times New Roman",serif; font-size:24px;
  color:var(--ink); font-weight:600; margin:0 0 6px; }
.lede { color:var(--muted); margin:0 0 20px; max-width:72ch; font-size:14.5px; }
.lede b { color:var(--body); font-weight:600; }
section { padding:44px 0 0; }
.facts { display:flex; flex-wrap:wrap; margin:30px 0 0; max-width:1300px;
  border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:hidden; }
.fact { flex:1 1 150px; padding:14px 18px; border-right:1px solid var(--hair); }
.fact:last-child { border-right:0; }
.fact b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.fact span { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }
.fact i { font-style:normal; font-size:12px; color:var(--muted); display:block; margin-top:2px; }
.panel { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  overflow-x:auto; max-height:620px; overflow-y:auto; }
table { border-collapse:collapse; width:100%; }
thead th { font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint);
  font-weight:650; background:var(--wash); border-bottom:1px solid var(--line);
  padding:10px 12px; text-align:left; white-space:nowrap; position:sticky; top:0; z-index:2; }
td { padding:8px 12px; border-bottom:1px solid var(--hair); vertical-align:top; }
tbody tr:hover td { background:var(--raise); }
.mrow th { background:var(--wash); border-top:1px solid var(--line);
  border-bottom:1px solid var(--line); padding:9px 12px; text-align:left;
  font-family:"Iowan Old Style",Georgia,serif; font-size:15px; color:var(--ink);
  font-weight:600; letter-spacing:.01em; position:sticky; top:37px; z-index:1; }
.mcount { font-family:system-ui,sans-serif; font-size:11px; font-weight:500;
  color:var(--faint); letter-spacing:.06em; text-transform:uppercase; margin-left:10px; }
.num { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13px; text-align:right; }
.yr { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:13px;
  color:var(--ink); font-weight:650; }
.dim { color:var(--faint); }
.note { font-size:11.5px; color:var(--faint); }
.hot { color:var(--ink); font-weight:650; }
.notes ul { padding-left:19px; margin:10px 0 0; }
.notes li { margin:7px 0; font-size:13.5px; color:var(--muted); max-width:78ch; }
.notes b { color:var(--body); font-weight:600; }
footer { border-top:1px solid var(--line); padding:20px 0 64px; margin-top:44px;
  font-size:12px; color:var(--faint); max-width:82ch; }
a { color:var(--accent); }
:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
"""

NCEI = "https://www.ncei.noaa.gov/access/search/data-search/daily-summaries?stations=" \
       "USC00047916"
USHCN_DOC = "https://www.ncei.noaa.gov/products/land-based-station/us-historical-climatology-network"


def page(d):
    svg, hot, cold, obs, adj = figure(d)
    st = d["station"]
    y0, y1 = d["observed_span"]
    a0, a1 = d["adjusted_span"]
    est_years = [r["year"] for r in d["years"] if r["adj_estimated"]]
    shorts = [r for r in d["years"] if r["short"]]
    missing = [y for y in range(y0, y1 + 1)
               if not any(r["year"] == y and r["days"] for r in d["years"])]
    trend_o = d["observed_trend_f_per_decade"]
    trend_a = d["adjusted_trend_f_per_decade"]
    first30 = [obs[y] for y in sorted(obs)[:30]]
    last30 = [obs[y] for y in sorted(obs)[-30:]]
    shift = sum(last30) / 30 - sum(first30) / 30

    rows, decades = [], {}
    for r in d["years"]:
        decades.setdefault(r["year"] // 10 * 10, []).append(r)
    for dec in sorted(decades):
        got = [r["mean_f"] for r in decades[dec] if r["mean_f"] is not None and not r["short"]]
        avg = f"{sum(got)/len(got):.1f}&#176;F" if got else "&#8212;"
        rows.append(f"""      <tr class="mrow"><th colspan="6" scope="colgroup">{dec}s
        <span class="mcount">{len(got)} August{"" if len(got) == 1 else "s"} averaged
        &#183; {avg}</span></th></tr>""")
        for r in decades[dec]:
            y = r["year"]
            if r["mean_f"] is None:
                mf = mc = "&#8212;"
                note = "no daily record" if y <= y1 else "station closed &#8212; adjusted only"
                cls = "num dim"
            elif r["short"]:
                mf = f'({r["mean_f"]:.1f})'
                mc = f'({_c(r["mean_f"]):.1f})'
                note = f'{r["days"]} of 31 days &#8212; not averaged'
                cls = "num dim"
            else:
                mf, mc = f'{r["mean_f"]:.1f}', f'{_c(r["mean_f"]):.1f}'
                note = ""
                cls = "num hot" if y in (hot, cold) else "num"
                if y == hot:
                    note = "warmest August in the record"
                elif y == cold:
                    note = "coolest August in the record"
            af = f'{r["adj_f"]:.1f}' if r["adj_f"] is not None else "&#8212;"
            if r["adj_estimated"] and r["adj_f"] is not None:
                af += ' <span class="note">est</span>'
            rows.append(f"""      <tr>
        <td class="yr">{y}</td>
        <td class="num dim">{r["days"] or "&#8212;"}</td>
        <td class="{cls}">{mf}</td>
        <td class="num dim">{mc}</td>
        <td class="num">{af}</td>
        <td class="note">{note}</td>
      </tr>""")

    return f"""<title>Santa Cruz &#183; August daily highs, {y0}&#8211;{a1}</title>
<style>{SHELL_CSS}{FIG_CSS}</style>
<div class="wrap">

<header>
  <p class="eyebrow">NOAA GHCN&#8209;Daily &#183; station {st["id"]} &#183; {y0}&#8211;{a1}</p>
  <h1>August on the <em>Santa Cruz</em> sand</h1>
  <p class="standfirst">The average of every daily high temperature in August, one number
  per year, back to {y0}. {d["observed_years"]} Augusts have a daily record complete
  enough to average; NOAA's homogenised version of the same station carries the series to
  {a1}. The town's Augusts are remarkably level &#8212; the long-run mean daytime high is
  {d["observed_mean_f"]:.1f}&#176;F, and the spread from the coolest August to the warmest
  is under {max(obs.values()) - min(obs.values()):.0f}&#176;F.</p>
</header>

<div class="facts">
  <div class="fact"><b>{d["observed_years"]}</b><span>Augusts averaged</span>
    <i>{y0}&#8211;{y1}, 28+ days each</i></div>
  <div class="fact"><b>{d["observed_mean_f"]:.1f}&#176;F</b><span>Long-run mean high</span>
    <i>{_c(d["observed_mean_f"]):.1f}&#176;C across the whole record</i></div>
  <div class="fact"><b>{obs[hot]:.1f}&#176;F</b><span>Warmest August</span>
    <i>{hot} &#8212; see the caveat below</i></div>
  <div class="fact"><b>{obs[cold]:.1f}&#176;F</b><span>Coolest August</span>
    <i>{cold}</i></div>
  <div class="fact"><b>{sgn(trend_o)}&#176;F</b><span>Trend per decade, observed</span>
    <i>{sgn(shift, 1)}&#176;F, last 30 Augusts against the first 30</i></div>
  <div class="fact"><b>{sgn(trend_a)}&#176;F</b><span>Trend per decade, adjusted</span>
    <i>NOAA homogenised, {a0}&#8211;{a1}</i></div>
</div>

<section>
  <h2>One August, one number</h2>
  <p class="lede">Each thin line is the year's own average: add up the daily high for
  every day the observer recorded in August, divide by the number of days. The heavy line
  over it is an {d["smooth"]}-year centred mean, which is what a climate signal would have
  to move. <b>Teal is the station record as written down.</b> <b>Gold is NOAA's
  homogenised version</b> of the same station &#8212; the record corrected for the things
  that shift a thermometer's reading without the weather shifting: a change in the hour of
  observation, a move across the yard, a new screen. It runs to {a1} because it fills the
  years after the station closed from neighbouring sites.</p>
  <div class="figwrap">
{svg}
  </div>
  <div class="keys">
    <span class="k"><span class="sw obs"></span> As observed &#8212; daily record,
      {y0}&#8211;{y1}</span>
    <span class="k"><span class="sw adj"></span> NOAA homogenised &#8212; monthly,
      {a0}&#8211;{a1}</span>
    <span class="k">Thin: single year. Heavy: {d["smooth"]}-year centred mean.</span>
  </div>
  <p class="figcap">Hover any year for its numbers. Gaps in a line are gaps in the record,
  not zero: {", ".join(str(m) for m in missing) or "none"} has no August daily data at all,
  and {len(shorts)} further Augusts &#8212;
  {", ".join(str(r["year"]) for r in shorts)} &#8212; were observed on fewer than
  {d["min_days"]} of their 31 days, marked by a tick on the axis and left out of the mean.</p>
</section>

<section>
  <h2>Why there are two lines</h2>
  <p class="lede">Santa Cruz in August is a marine-layer climate: the ocean sets the
  daytime ceiling, and the ceiling has barely moved. Over {d["observed_years"]} Augusts the
  observed trend is {sgn(trend_o)}&#176;F per decade &#8212; statistically nothing, and the
  wrong sign for a warming story. Nights are a different question, and not this chart's.</p>
  <p class="lede">But the raw line cannot be read on its own, because one stretch of it is
  the instrument rather than the weather. Measured against <b>Watsonville</b>, 21&#8202;km
  down the coast and still reporting, Santa Cruz reads about 1.3&#176;F warmer through the
  1990s and 2000s &#8212; then 4 to 6&#176;F warmer from {DRIFT[0]} to {DRIFT[1]}, then
  falls back. A gap that opens and closes against a neighbour is a station artefact. That
  is the shaded stretch on the chart, and it is why {hot} shows as the warmest August in
  {y1 - y0} years at {obs[hot]:.1f}&#176;F: {hot} was genuinely hot everywhere on this coast
  &#8212; Watsonville had its warmest August too &#8212; but this station's number is
  inflated on top of it. NOAA's homogenised series puts {hot} at
  {adj[hot]:.1f}&#176;F instead.</p>
  <p class="lede">The homogenised line is the one to read for trend: {sgn(trend_a)}&#176;F
  per decade, a real but small warming, and the one to read for the years after the station
  fell silent in April 2022. Its last {sum(1 for y in est_years if y > y1)} values are
  estimated from neighbouring stations rather than measured here, and
  {len(est_years)} August values in total carry that flag.</p>
</section>

<section>
  <h2>Every August</h2>
  <p class="lede">The chart's data, decade by decade, with each decade's own average in its
  header. <b>Days</b> is how many of the 31 the observer recorded and quality control
  accepted; a year in brackets fell short of {d["min_days"]} and is excluded from every
  average on this page. <b>Adjusted</b> is NOAA's homogenised value, <span class="note">est</span>
  where it was infilled from neighbouring stations.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Year</th>
        <th scope="col" style="text-align:right">Days</th>
        <th scope="col" style="text-align:right">Mean high &#176;F</th>
        <th scope="col" style="text-align:right">&#176;C</th>
        <th scope="col" style="text-align:right">Adjusted &#176;F</th>
        <th scope="col"></th>
      </tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>
</section>

<section class="notes">
  <h2>How it is computed, and what it is not</h2>
  <ul>
    <li><b>The average is of daily highs, not of daily temperature.</b> Each year's number
    is the mean of TMAX over the days of August &#8212; the afternoon peak, which is the
    number a beach day is planned around. The mean of TMIN, or of the daily average, is a
    different series and moves differently.</li>
    <li><b>One station, because there is only one.</b> {st["name"]}, {st["id"]}, at
    {st["lat"]}&#176;N {abs(st["lon"])}&#176;W and {st["elevation_m"]}&#8202;m, a US
    Historical Climatology Network site reporting daily since {y0}. Every other Santa Cruz
    entry in GHCN is a modern volunteer rain gauge with no thermometer. Its own microclimate
    is the town's, not the beach's: a sea-cliff site a mile from the wharf, cooler than
    inland Scotts Valley and warmer than the water's edge.</li>
    <li><b>Days that failed NOAA's quality control are dropped</b> &#8212;
    {d["qc_rejected_days"]} of them across the whole August record &#8212; and a year needs
    {d["min_days"]} of 31 days to be averaged at all. Averaging a half-observed month
    against a full one compares two different things.</li>
    <li><b>Reliability runs out at both ends, differently.</b> Before about 1900 the
    observing hour was less standardised, which is exactly what homogenisation exists to
    correct: read the gold line there. After April 2022 the station simply stopped, so
    {y1} is the last year with an observed value and everything past it is inference from
    neighbours.</li>
    <li><b>The trend figures are ordinary least squares</b> on the annual means, in
    &#176;F per decade: {sgn(trend_o, 3)} observed over {d["observed_years"]} Augusts,
    {sgn(trend_a, 3)} homogenised over {len([r for r in d["years"] if r["adj_f"] is not None])}.
    Neither is a forecast, and August alone says nothing about the rest of the year.</li>
  </ul>
</section>

<footer>
  Source: NOAA NCEI &#8212; <a href="{NCEI}">GHCN&#8209;Daily station {st["id"]}</a> for the
  daily maxima, and <a href="{USHCN_DOC}">USHCN v2.5</a> ({st["ushcn"]}, the FLs.52j
  homogenised product) for the adjusted series. Rebuild with
  <code>python3 scripts/august_temps.py --refresh</code>; the derived series is in
  <code>data/august_temps.json</code>.
</footer>

</div>
"""
