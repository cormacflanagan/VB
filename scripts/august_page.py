"""Render an August page: the annual series as an inline SVG line chart.

Change over time, so a line. Two series carry it -- what the observer wrote down, and
NOAA's homogenised version of the same station -- and each is drawn twice: the annual
values thin, and an 11-year centred mean heavy on top of them. Hue separates the two
sources (checked for colour-vision separation against the page's own surface), and the
homogenised one is dashed as well, so the pair never depends on colour alone.

Every year carries a hit target with its own numbers on hover, so the figure needs no
script, and the full table below is the same data in a form a reader can search.

One renderer, two pages: the daytime maxima and the nighttime minima are the same shape of
question and differ only in wording, in whether a drift band is drawn, and in what the
evidence actually says. COPY holds the parts that differ.
"""
import html

W, H = 1060, 470
ML, MR, MT, MB = 58, 132, 18, 54
PW, PH = W - ML - MR, H - MT - MB

COPY = {
    "tmax": {
        "title": "August daily highs",
        "h1": 'August on the <em>Santa Cruz</em> sand',
        "value": "daily high", "values": "daily highs", "plain": "afternoon peak",
        "axis": "Mean daily high in August (&#176;F)",
        "warm": "Warmest August", "cool": "Coolest August",
        "warm_note": "warmest August in the record", "cool_note": "coolest August in the record",
        "other": ("august-nights.html", "August nights"),
    },
    "tmin": {
        "title": "August nightly lows",
        "h1": 'August <em>nights</em> in Santa Cruz',
        "value": "daily low", "values": "daily lows", "plain": "pre-dawn low",
        "axis": "Mean nightly low in August (&#176;F)",
        "warm": "Warmest nights", "cool": "Coolest nights",
        "warm_note": "warmest August nights in the record",
        "cool_note": "coolest August nights in the record",
        "other": ("august-temps.html", "August days"),
    },
}


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
    c = COPY[d["element"]]
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
         f'aria-label="Mean August {c["value"]} temperature at Santa Cruz, one point per '
         f'year from {d["observed_span"][0]} to {d["adjusted_span"][1]}, as observed and '
         f'as homogenised by NOAA.">']

    if d["drift"]:
        # the stretch where the station reads warm against its neighbour, marked where it
        # happens rather than only described underneath
        a, b = d["drift"]
        bx0, bx1 = sx(a - 0.5), sx(b + 0.5)
        gap = next(o_["diff"] for o_ in d["neighbour"]["decades"] if o_["decade"] == 2010)
        o.append(f'<rect class="band" x="{bx0:.1f}" y="{MT}" width="{bx1-bx0:.1f}" '
                 f'height="{PH}"><title>{a}&#8211;{b}: this station runs {gap:+.1f} &#176;F '
                 f'against {d["neighbour"]["name"]} over the 2010s, after two decades near '
                 f'+1.5. A difference that opens and closes against a neighbour 21 km away '
                 f'is the station, not the weather.</title></rect>')
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
             f'x="0" y="0">{c["axis"]}</text>')

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
    for y, dy in ((hot, -13), (cold, 20)):
        o.append(f'<circle class="mk" cx="{sx(y):.1f}" cy="{sy(obs[y]):.1f}" r="4"/>')
        o.append(f'<text class="ptlab" text-anchor="middle" x="{sx(y):.1f}" '
                 f'y="{sy(obs[y])+dy:.1f}">{y} &#183; {obs[y]:.1f}&#176;</text>')

    # series names ride at the right end of each line, so the legend is not load-bearing
    last_o, last_a = max(obs), max(adj)
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
.fig .endlab.obs { fill:var(--obs); }
.fig .endlab.adj { fill:var(--adj); }
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
.offs { display:flex; flex-wrap:wrap; gap:0; margin:6px 0 20px; max-width:1000px;
  border:1px solid var(--line); border-radius:3px; background:var(--surface);
  overflow:hidden; }
.off { flex:1 1 76px; padding:10px 12px; border-right:1px solid var(--hair); }
.off:last-child { border-right:0; }
.off b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:15px; font-weight:600; color:var(--ink); font-variant-numeric:tabular-nums; }
.off span { font-size:10.5px; letter-spacing:.08em; color:var(--faint); }
.off.wide b { color:var(--gold); }
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

NCEI = "https://www.ncei.noaa.gov/access/search/data-search/daily-summaries?stations="
USHCN_DOC = ("https://www.ncei.noaa.gov/products/land-based-station"
             "/us-historical-climatology-network")


def decade_split(d):
    """The first decade after which every decade average beats every one before it.

    A monotone step like that is what a real shift looks like against a record whose own
    noise is decade-scale. None means there is no such split, and the claim is not made.
    """
    means = {}
    for r in d["years"]:
        if r["mean_f"] is not None and not r["short"]:
            means.setdefault(r["year"] // 10 * 10, []).append(r["mean_f"])
    # a decade standing on one or two Augusts is not a decade average
    avg = {k: sum(v) / len(v) for k, v in means.items() if len(v) >= 5}
    decs = sorted(avg)
    for i in range(2, len(decs) - 1):
        before, after = [avg[x] for x in decs[:i]], [avg[x] for x in decs[i:]]
        if min(after) > max(before):
            return decs[i], max(before), min(after), decs[0], decs[i - 1]
    return None


def offsets(d):
    """The decade-by-decade difference against the neighbour, as a strip of cells."""
    n = d["neighbour"]
    worst = max(n["decades"], key=lambda o: abs(o["diff"]))["decade"]
    return "".join(
        f'<div class="off{" wide" if o["decade"] == worst else ""}">'
        f'<b>{sgn(o["diff"], 1)}</b><span>{o["decade"]}s &#183; {o["years"]}&#8202;yr</span>'
        f'</div>' for o in n["decades"])


def evidence(d, obs, adj, hot):
    """The middle section: why a second line is drawn, and what it changes here."""
    c, n = COPY[d["element"]], d["neighbour"]
    to, ta = d["observed_trend_f_per_decade"], d["adjusted_trend_f_per_decade"]
    shift = d["last30_f"] - d["first30_f"]
    strip = f"""  <div class="offs">{offsets(d)}</div>
  <p class="figcap" style="margin-bottom:22px">Santa Cruz minus {n["name"]}
  ({n["id"]}, {n["km"]}&#8202;km down the coast), mean August {c["value"]}, by decade.
  Decades with fewer than three comparable Augusts are left out. Two stations this close
  share their weather, so this difference should be flat; the widest decade is marked.</p>"""

    if d["element"] == "tmax":
        return f"""
<section>
  <h2>Why there are two lines</h2>
  <p class="lede">Santa Cruz in August is a marine-layer climate: the ocean sets the
  daytime ceiling, and on the face of it the ceiling has not moved. Over
  {d["observed_years"]} Augusts the observed trend is {sgn(to)}&#176;F per decade, and the
  last 30 Augusts average {sgn(shift, 1)}&#176;F against the first 30 &#8212; nothing, and
  the wrong sign for a warming story.</p>
  <p class="lede">The catch is that <b>the daytime record cannot settle its own sign.</b>
  Homogenising it &#8212; correcting for changes of observation hour, instrument and siting
  &#8212; turns {sgn(to)} into {sgn(ta)}&#176;F per decade. The correction is larger than
  the trend it is correcting, so which way August afternoons have gone here is a question
  this station cannot answer on its own.</p>
  <p class="lede">That the raw line carries station history is not a guess. Differenced
  against <b>{n["name"]}</b>, {n["km"]}&#8202;km down the coast, the August daytime gap
  wanders across {n["spread_f"]:.1f}&#176;F from decade to decade &#8212; it should be a
  constant.</p>
{strip}
  <p class="lede">The 2010s stand out: {sgn(next(o["diff"] for o in n["decades"] if o["decade"] == 2010), 1)}&#176;F,
  after two decades near +1.5. That is the shaded stretch on the chart, and it is why
  {hot} shows as the warmest August in {d["observed_span"][1] - d["observed_span"][0]} years
  at {obs[hot]:.1f}&#176;F. {hot} was genuinely hot everywhere on this coast &#8212;
  {n["name"]} was hot that August too &#8212; but this station's
  number is inflated on top of it, and the homogenised series puts it at
  {adj[hot]:.1f}&#176;F.</p>
  <p class="lede">The nights are the other half of the question, and unlike the afternoons
  they give a clear answer: <a href="{c["other"][0]}">{c["other"][1]}</a> warmed
  {d["diurnal"]["first30_f"] - d["diurnal"]["last30_f"]:.1f}&#176;F relative to the days,
  and that trend survives the same correction that erases this one.</p>
</section>"""

    dr = d["diurnal"]
    sp = decade_split(d)
    step = (f' Every decade average from the {sp[0]}s on is warmer than every decade '
            f'average before it: {sp[2]:.1f}&#176;F at the coolest, against '
            f'{sp[1]:.1f}&#176;F at the warmest of the {sp[3]}s&#8211;{sp[4]}s. A drift '
            f'that jitters cannot make a step like that.') if sp else ""
    return f"""
<section>
  <h2>The trend that survives the correction</h2>
  <p class="lede">Nights are where the signal is. Over {d["observed_years"]} Augusts the
  observed trend is <b>{sgn(to)}&#176;F per decade</b>, and the last 30 Augusts average
  <b>{sgn(shift, 1)}&#176;F warmer at night</b> than the first 30 &#8212;
  {d["first30_f"]:.1f}&#176;F against {d["last30_f"]:.1f}&#176;F. That is not a subtle
  effect: on the chart it is the one thing you do not need the heavy line to see.</p>
  <p class="lede">And it holds up. Homogenising the series &#8212; correcting for changes
  of observation hour, instrument and siting &#8212; moves {sgn(to)} to {sgn(ta)}&#176;F
  per decade. <b>The correction changes the size of the answer, not the answer.</b> That is
  the difference from the daytime series, where the same correction is larger than the
  trend and flips its sign.</p>
  <p class="lede">The neighbour test does not dent it either. Differenced against
  <b>{n["name"]}</b>, {n["km"]}&#8202;km down the coast, the August nighttime gap wanders
  across {n["spread_f"]:.1f}&#176;F over a century &#8212; both of these are real stations,
  tended by hand, and neither is a reference standard &#8212; but it wanders without
  direction, and the warming does not.{step}</p>
{strip}
  <p class="lede"><b>What this cannot separate is the town from the climate.</b>
  Homogenisation catches the thermometer moving; it does not catch a city growing around a
  thermometer that stayed put. Santa Cruz went from a town of a few thousand when this
  record opened to a city of sixty thousand, and
  built surfaces release at night what they absorbed by day &#8212; the textbook shape of an
  urban heat island is warmer nights with unchanged afternoons, which is exactly the shape
  here. A warming ocean pushes the same way. The record tells you August nights in this town
  are {abs(shift):.1f}&#176;F warmer than they were; it does not tell you how much of that
  is the town.</p>
  <p class="lede">Either way the day&#8211;night gap has closed. Across the
  {dr["years"]} Augusts with both readings, the mean spread between the day's high and its
  low fell from {dr["first30_f"]:.1f}&#176;F over the first 30 to
  {dr["last30_f"]:.1f}&#176;F over the last 30, {sgn(dr["trend_f_per_decade"])}&#176;F per
  decade &#8212; about a fifth of it gone. Read that with the caveat from
  <a href="{c["other"][0]}">{c["other"][1]}</a>: part of the daytime half of that gap is
  the station rather than the sky.</p>
</section>"""


def page(d):
    c = COPY[d["element"]]
    svg, hot, cold, obs, adj = figure(d)
    st = d["station"]
    y0, y1 = d["observed_span"]
    a0, a1 = d["adjusted_span"]
    est_years = [r["year"] for r in d["years"] if r["adj_estimated"]]
    shorts = [r for r in d["years"] if r["short"]]
    missing = [y for y in range(y0, y1 + 1)
               if not any(r["year"] == y and r["days"] for r in d["years"])]
    to, ta = d["observed_trend_f_per_decade"], d["adjusted_trend_f_per_decade"]
    shift = d["last30_f"] - d["first30_f"]

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
                    note = c["warm_note"]
                elif y == cold:
                    note = c["cool_note"]
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

    if d["element"] == "tmax":
        stand = (f'The town&#8217;s Augusts are remarkably level &#8212; the long-run mean '
                 f'daytime high is {d["observed_mean_f"]:.1f}&#176;F, and the spread from '
                 f'the coolest August to the warmest is under '
                 f'{max(obs.values()) - min(obs.values()):.0f}&#176;F. Whether the '
                 f'afternoons have warmed at all is a question this station cannot settle.')
        trend_tile = (f'<div class="fact"><b>{sgn(to)}&#176;F</b>'
                      f'<span>Trend per decade, observed</span>'
                      f'<i>{sgn(shift, 1)}&#176;F, last 30 Augusts against the first 30</i></div>')
    else:
        stand = (f'The long-run mean is {d["observed_mean_f"]:.1f}&#176;F &#8212; and unlike '
                 f'the afternoons, it has moved. The last 30 Augusts in the record average '
                 f'{abs(shift):.1f}&#176;F warmer at night than the first 30, a trend that '
                 f'survives every correction NOAA applies to the same station.')
        trend_tile = (f'<div class="fact"><b>{sgn(to)}&#176;F</b>'
                      f'<span>Trend per decade, observed</span>'
                      f'<i>{sgn(shift, 1)}&#176;F, last 30 Augusts against the first 30</i></div>'
                      f'<div class="fact"><b>{sgn(d["diurnal"]["trend_f_per_decade"])}&#176;F</b>'
                      f'<span>Day&#8211;night gap, per decade</span>'
                      f'<i>{d["diurnal"]["first30_f"]:.1f}&#176;F then, '
                      f'{d["diurnal"]["last30_f"]:.1f}&#176;F now</i></div>')

    return f"""<title>Santa Cruz &#183; {c["title"]}, {y0}&#8211;{a1}</title>
<style>{SHELL_CSS}{FIG_CSS}</style>
<div class="wrap">

<header>
  <p class="eyebrow">NOAA GHCN&#8209;Daily &#183; station {st["id"]} &#183; {y0}&#8211;{a1}</p>
  <h1>{c["h1"]}</h1>
  <p class="standfirst">The average of every {c["value"]} temperature in August, one number
  per year, back to {y0}. {d["observed_years"]} Augusts have a daily record complete enough
  to average; NOAA&#8217;s homogenised version of the same station carries the series to
  {a1}. {stand}</p>
</header>

<div class="facts">
  <div class="fact"><b>{d["observed_years"]}</b><span>Augusts averaged</span>
    <i>{y0}&#8211;{y1}, {d["min_days"]}+ days each</i></div>
  <div class="fact"><b>{d["observed_mean_f"]:.1f}&#176;F</b>
    <span>Long-run mean {c["value"]}</span>
    <i>{_c(d["observed_mean_f"]):.1f}&#176;C across the whole record</i></div>
  <div class="fact"><b>{obs[hot]:.1f}&#176;F</b><span>{c["warm"]}</span>
    <i>{hot}{" &#8212; see the caveat below" if d["drift"] else ""}</i></div>
  <div class="fact"><b>{obs[cold]:.1f}&#176;F</b><span>{c["cool"]}</span>
    <i>{cold}</i></div>
  {trend_tile}
  <div class="fact"><b>{sgn(ta)}&#176;F</b><span>Trend per decade, adjusted</span>
    <i>NOAA homogenised, {a0}&#8211;{a1}</i></div>
</div>

<section>
  <h2>One August, one number</h2>
  <p class="lede">Each thin line is the year&#8217;s own average: add up the {c["value"]}
  for every day the observer recorded in August, divide by the number of days. The heavy
  line over it is an {d["smooth"]}-year centred mean, which is what a climate signal would
  have to move. <b>Teal is the station record as written down.</b> <b>Gold is NOAA&#8217;s
  homogenised version</b> of the same station &#8212; the record corrected for the things
  that shift a thermometer&#8217;s reading without the weather shifting: a change in the
  hour of observation, a move across the yard, a new screen. It runs to {a1} because it
  fills the years after the station closed from neighbouring sites.</p>
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
{evidence(d, obs, adj, hot)}

<section>
  <h2>Every August</h2>
  <p class="lede">The chart&#8217;s data, decade by decade, with each decade&#8217;s own
  average in its header. <b>Days</b> is how many of the 31 the observer recorded and quality
  control accepted; a year in brackets fell short of {d["min_days"]} and is excluded from
  every average on this page. <b>Adjusted</b> is NOAA&#8217;s homogenised value,
  <span class="note">est</span> where it was infilled from neighbouring stations.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Year</th>
        <th scope="col" style="text-align:right">Days</th>
        <th scope="col" style="text-align:right">Mean {c["value"]} &#176;F</th>
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
    <li><b>The average is of {c["values"]}, not of daily temperature.</b> Each year&#8217;s
    number is the mean of {d["ghcn_element"]} over the days of August &#8212; the
    {c["plain"]}. The other element, and the daily average, are different series and move
    differently: that is the point of having
    <a href="{c["other"][0]}">both pages</a>.</li>
    <li><b>One station, because there is only one.</b> {st["name"]}, {st["id"]}, at
    {st["lat"]}&#176;N {abs(st["lon"])}&#176;W and {st["elevation_m"]}&#8202;m, a US
    Historical Climatology Network site reporting daily since {y0}. Every other Santa Cruz
    entry in GHCN is a modern volunteer rain gauge with no thermometer. Its own microclimate
    is the town&#8217;s, not the beach&#8217;s: a sea-cliff site a mile from the wharf,
    cooler than inland Scotts Valley and warmer than the water&#8217;s edge.</li>
    <li><b>Days that failed NOAA&#8217;s quality control are dropped</b> &#8212;
    {d["qc_rejected_days"]} of them across the whole August record for this element &#8212;
    and a year needs {d["min_days"]} of 31 days to be averaged at all. Averaging a
    half-observed month against a full one compares two different things.</li>
    <li><b>Reliability runs out at both ends, differently.</b> Before about 1900 the
    observing hour was less standardised, which is exactly what homogenisation exists to
    correct: read the gold line there. After April 2022 the station simply stopped, so
    {y1} is the last year with an observed value, and the {sum(1 for y in est_years if y > y1)}
    years past it &#8212; {len(est_years)} August values in total &#8212; are inference from
    neighbours rather than measurement here.</li>
    <li><b>The trend figures are ordinary least squares</b> on the annual means, in
    &#176;F per decade: {sgn(to, 3)} observed over {d["observed_years"]} Augusts,
    {sgn(ta, 3)} homogenised over
    {len([r for r in d["years"] if r["adj_f"] is not None])}. Neither is a forecast, and
    August alone says nothing about the rest of the year.</li>
  </ul>
</section>

<footer>
  Source: NOAA NCEI &#8212; <a href="{NCEI}{st["id"]}">GHCN&#8209;Daily station
  {st["id"]}</a> for the daily {c["values"]}, {d["neighbour"]["id"]}
  ({d["neighbour"]["name"]}) for the comparison, and <a href="{USHCN_DOC}">USHCN v2.5</a>
  ({st["ushcn"]}, the FLs.52j homogenised product) for the adjusted series. Rebuild with
  <code>python3 scripts/august_temps.py --refresh</code>; the derived series are in
  <code>data/august_temps.json</code> and <code>data/august_nights.json</code>.
</footer>

</div>
"""
