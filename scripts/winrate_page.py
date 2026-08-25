"""Win rate against opponent strength, in quarter-point TruVolley bands.

  python3 scripts/winrate_page.py   ->  docs/winrate.html

A placing says who finished above whom in one field. This asks a different question: at
what level of opposition does she stop winning? Every doubles match in the merged corpus
is bucketed by the mean TruVolley of the two players across the net, in the same quarter
points the rating itself is quoted in.

Two things about small samples are handled rather than hidden. Bars carry a Wilson 95%
interval, which is the right one for a proportion at n in single figures -- one win from
one match is 100% with an interval running from 21% to 100%, and the bar should say so.
And any band under MIN_SOLID matches is drawn hatched, so low confidence is legible
without relying on colour.

Only matches where *both* opponents carry a published TruVolley can be placed on this
axis, which is a minority of them; `coverage` in the output says how many were dropped.
"""
import datetime, json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "docs", "winrate.html")
HAISLEY = 64896
LO, HI, STEP = 6.0, 9.0, 0.25
MIN_SOLID = 5          # fewer matches than this and the bar is hatched


def truvolley():
    """Published TruVolley, from the cached cohort ratings and the college corpus."""
    tv = {}
    for k, v in json.load(open(os.path.join(DATA, "tvcache.json"))).items():
        if v.get("tv"):
            tv[int(k)] = v["tv"]
    for r in read_jsonl(os.path.join(DATA, "college", "players.jsonl")):
        if r.get("vblId") and r.get("tv"):
            tv.setdefault(r["vblId"], r["tv"])
    return tv


def wilson(w, n, z=1.96):
    """Score interval: at n = 1 a Wald interval is zero-width and a lie."""
    if not n:
        return 0.0, 0.0
    p = w / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def gather(tv, days, pid=HAISLEY):
    since = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    edges = [round(LO + STEP * i, 2) for i in range(int((HI - LO) / STEP))]
    bins = {e: [0, 0] for e in edges}
    seen = rated = 0
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        if pid not in m["a"] + m["b"] or not (since <= m["date"] <= "2026-12-31"):
            continue
        seen += 1
        home = pid in m["a"]
        opp = m["b"] if home else m["a"]
        if not all(o in tv for o in opp):
            continue
        rated += 1
        s = sum(tv[o] for o in opp) / len(opp)
        if not (LO <= s < HI):
            continue
        e = round(LO + STEP * int((s - LO) / STEP + 1e-9), 2)
        bins[e][m["aWon"] if home else not m["aWon"]] += 1
    rows = []
    for e in edges:
        l, w = bins[e]
        n = w + l
        lo, hi = wilson(w, n)
        rows.append({"lo": e, "hi": round(e + STEP, 2), "w": w, "l": l, "n": n,
                     "pct": 100 * w / n if n else None,
                     "ci": (100 * lo, 100 * hi) if n else None})
    return {"rows": rows, "seen": seen, "rated": rated,
            "inrange": sum(r["n"] for r in rows)}


def chart(rows, w=980, h=380, solid_only=False):
    L, R, T, B = 58, 26, 30, 76
    pw, ph = w - L - R, h - T - B
    bw = pw / len(rows)
    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" '
         f'aria-label="Win rate by opponent TruVolley band">',
         '<defs><pattern id="thin" width="6" height="6" patternUnits="userSpaceOnUse" '
         'patternTransform="rotate(45)"><rect width="6" height="6" class="hatchbg"/>'
         '<line x1="0" y1="0" x2="0" y2="6" class="hatchline"/></pattern></defs>']
    for pct in range(0, 101, 25):
        y = T + ph - ph * pct / 100
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{w - R}" y2="{y:.1f}" '
                 f'class="{"axis" if pct == 0 else "grid"}"/>')
        o.append(f'<text x="{L - 10}" y="{y + 4:.1f}" class="tick" '
                 f'text-anchor="end">{pct}%</text>')
    for i, r in enumerate(rows):
        x = L + i * bw
        cx = x + bw / 2
        o.append(f'<text x="{cx:.1f}" y="{h - B + 20}" class="tick" '
                 f'text-anchor="middle">{r["lo"]:.2f}</text>')
        if not r["n"]:
            o.append(f'<text x="{cx:.1f}" y="{T + ph - 8}" class="none" '
                     f'text-anchor="middle">&#8212;</text>')
            o.append(f'<text x="{cx:.1f}" y="{h - B + 38}" class="cnt" '
                     f'text-anchor="middle">0</text>')
            continue
        bh = ph * r["pct"] / 100
        cls = "bar" if r["n"] >= MIN_SOLID else "bar thin"
        o.append(f'<rect x="{x + 3:.1f}" y="{T + ph - bh:.1f}" width="{bw - 6:.1f}" '
                 f'height="{max(bh, 1.5):.1f}" rx="3" class="{cls}">'
                 f'<title>{r["lo"]:.2f}&#8211;{r["hi"]:.2f}: {r["w"]}&#8211;{r["l"]}, '
                 f'{r["pct"]:.0f}% (95% interval {r["ci"][0]:.0f}&#8211;{r["ci"][1]:.0f}%)'
                 f'</title></rect>')
        ylo = T + ph - ph * r["ci"][0] / 100
        yhi = T + ph - ph * r["ci"][1] / 100
        o.append(f'<line x1="{cx:.1f}" y1="{yhi:.1f}" x2="{cx:.1f}" y2="{ylo:.1f}" '
                 f'class="ci"/>')
        for yy in (yhi, ylo):
            o.append(f'<line x1="{cx - 5:.1f}" y1="{yy:.1f}" x2="{cx + 5:.1f}" '
                     f'y2="{yy:.1f}" class="ci"/>')
        o.append(f'<text x="{cx:.1f}" y="{yhi - 8:.1f}" class="val" '
                 f'text-anchor="middle">{r["pct"]:.0f}</text>')
        o.append(f'<text x="{cx:.1f}" y="{h - B + 38}" class="cnt" '
                 f'text-anchor="middle">{r["w"]}&#8211;{r["l"]}</text>')
    o.append(f'<text x="{L}" y="{h - B + 60}" class="axlab">OPPONENT TRUVOLLEY '
             f'(TEAM MEAN, LOWER EDGE OF BAND)</text>')
    o.append(f'<text x="{w - R}" y="{h - B + 60}" class="axlab" text-anchor="end">'
             f'W&#8211;L UNDER EACH BAND</text>')
    o.append("</svg>")
    return "\n".join(o)


CSS = """
:root {
  --ground:#EFF1EE; --surface:#FAFBFA; --ink:#111B19; --body:#2C3A37;
  --muted:#5F6E6A; --faint:#8B9995; --line:#D5DCD9; --hair:#E4E9E7;
  --accent:#0B6E68; --bar:#00806F; --barlite:#A2D6CC; --warn:#9A6B12;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
    --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
    --accent:#57C3B6; --bar:#2AA08C; --barlite:#1B5248; --warn:#DCA84A;
  }
}
:root[data-theme="dark"] {
  --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
  --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
  --accent:#57C3B6; --bar:#2AA08C; --barlite:#1B5248; --warn:#DCA84A;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; font-size:15px;
  line-height:1.6; -webkit-font-smoothing:antialiased; }
.wrap { max-width:1080px; margin:0 auto; padding:0 clamp(18px,2.4vw,40px) 64px; }
header { padding:56px 0 28px; border-bottom:1px solid var(--line); }
.eyebrow { font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin:0 0 16px; }
h1 { font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(30px,4.6vw,46px); line-height:1.07; letter-spacing:-.02em;
  color:var(--ink); margin:0 0 14px; font-weight:600; text-wrap:balance; max-width:24ch; }
h1 em { font-style:italic; color:var(--accent); }
.standfirst { font-size:17px; color:var(--muted); max-width:66ch; margin:0; }
h2 { font-family:"Iowan Old Style",Georgia,serif; font-size:23px; color:var(--ink);
  font-weight:600; margin:0 0 6px; text-wrap:balance; }
.lede { color:var(--muted); margin:0 0 20px; max-width:70ch; font-size:14.5px; }
section { padding:42px 0 0; }
p { max-width:70ch; }
.facts { display:flex; flex-wrap:wrap; margin:28px 0 0; border:1px solid var(--line);
  border-radius:3px; background:var(--surface); overflow:hidden; }
.fact { flex:1 1 150px; padding:14px 18px; border-right:1px solid var(--hair); }
.fact:last-child { border-right:0; }
.fact b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.fact span { font-size:11px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--faint); }
.figbox { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:14px 12px 6px; overflow-x:auto; }
.fig { width:100%; min-width:720px; height:auto; display:block; }
.grid { stroke:var(--hair); stroke-width:1; }
.axis { stroke:var(--line); stroke-width:1.4; }
.tick { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  fill:var(--muted); font-variant-numeric:tabular-nums; }
.cnt { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10.5px;
  fill:var(--faint); font-variant-numeric:tabular-nums; }
.val { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px;
  fill:var(--ink); font-weight:650; font-variant-numeric:tabular-nums; }
.none { font-size:13px; fill:var(--faint); }
.axlab { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px;
  letter-spacing:.1em; fill:var(--faint); }
.bar { fill:var(--bar); }
.bar.thin { fill:url(#thin); stroke:var(--bar); stroke-width:1; }
.hatchbg { fill:var(--surface); }
.hatchline { stroke:var(--bar); stroke-width:2.5; }
.ci { stroke:var(--ink); stroke-width:1.4; opacity:.55; }
.key { display:flex; flex-wrap:wrap; gap:22px; font-size:12px; color:var(--muted);
  margin:14px 0 0; padding:0 4px; }
.key i { display:inline-block; width:12px; height:12px; vertical-align:-2px;
  margin-right:7px; border-radius:2px; }
.k1 i { background:var(--bar); }
.k2 i { border:1px solid var(--bar); background:repeating-linear-gradient(45deg,
  var(--bar) 0 2px, var(--surface) 2px 5px); }
.k3 i { width:2px; height:14px; background:var(--ink); opacity:.55; border-radius:0;
  margin-left:5px; margin-right:12px; }
table { border-collapse:collapse; width:100%; font-size:13.5px; background:var(--surface); }
th, td { padding:6px 10px; border-bottom:1px solid var(--hair); text-align:left; }
th { font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint);
  font-weight:650; border-bottom:1px solid var(--line); }
td.n, th.n { text-align:right; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums; }
tr.low td { color:var(--muted); }
.tbox { border:1px solid var(--line); border-radius:3px; overflow:auto; }
ul { max-width:70ch; padding-left:20px; }
li { margin:0 0 10px; }
.warnbox { border-left:3px solid var(--warn); background:var(--surface);
  padding:14px 18px; border-radius:0 3px 3px 0; margin:22px 0 0; max-width:74ch; }
.warnbox b { color:var(--ink); }
footer { margin-top:52px; padding-top:18px; border-top:1px solid var(--line);
  font-size:12px; color:var(--faint); max-width:80ch; }
"""


def table(rows):
    out = []
    for r in rows:
        if not r["n"]:
            out.append(f'<tr class="low"><td class="n">{r["lo"]:.2f}&#8211;{r["hi"]:.2f}</td>'
                       f'<td class="n">0</td><td class="n">&#8212;</td>'
                       f'<td class="n">&#8212;</td><td class="n">&#8212;</td></tr>')
            continue
        cls = ' class="low"' if r["n"] < MIN_SOLID else ""
        out.append(f'<tr{cls}><td class="n">{r["lo"]:.2f}&#8211;{r["hi"]:.2f}</td>'
                   f'<td class="n">{r["n"]}</td><td class="n">{r["w"]}&#8211;{r["l"]}</td>'
                   f'<td class="n">{r["pct"]:.0f}%</td>'
                   f'<td class="n">{r["ci"][0]:.0f}&#8211;{r["ci"][1]:.0f}%</td></tr>')
    return "".join(out)


def build():
    tv = truvolley()
    yr = gather(tv, 365)
    two = gather(tv, 730)
    rows = yr["rows"]
    strong = [r for r in rows if r["lo"] >= 7.25]
    sw = sum(r["w"] for r in strong)
    sl = sum(r["l"] for r in strong)
    top = [r for r in rows if r["lo"] >= 8.0]
    tw, tl = sum(r["w"] for r in top), sum(r["l"] for r in top)
    thin = sum(1 for r in rows if 0 < r["n"] < MIN_SOLID)

    return f"""<title>Where Her Wins Stop</title>
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="eyebrow">Haisley Flanagan &#183; doubles &#183; twelve months to 24 August 2026</p>
  <h1>At what level of opponent does she <em>stop winning?</em></h1>
  <p class="standfirst">Every doubles match of the past year, bucketed by the mean
  TruVolley of the two players across the net. Bars are win rate; the whisker is a 95%
  interval, which at these sample sizes is most of the story.</p>
</header>

<div class="facts">
  <div class="fact"><b>{yr["inrange"]}</b><span>Matches in the 6.0&#8211;9.0 range</span></div>
  <div class="fact"><b>{sw}&#8211;{sl}</b><span>Against 7.25 and above</span></div>
  <div class="fact"><b>{tw}&#8211;{tl}</b><span>Against 8.0 and above</span></div>
  <div class="fact"><b>{yr["rated"]}<small> / {yr["seen"]}</small></b>
    <span>Matches with both opponents rated</span></div>
</div>

<section>
  <h2>Past twelve months</h2>
  <p class="lede">Quarter-point bands, the same increment TruVolley itself is quoted in.
  A band with fewer than {MIN_SOLID} matches is hatched: the bar is drawn, but the
  interval beside it is doing the honest work.</p>
  <div class="figbox">{chart(rows)}</div>
  <div class="key">
    <span class="k1"><i></i>{MIN_SOLID} matches or more</span>
    <span class="k2"><i></i>Fewer than {MIN_SOLID} &#8212; read the interval, not the bar</span>
    <span class="k3"><i></i>95% Wilson interval</span>
  </div>
  <p style="margin-top:22px">She is unbeaten below 7.25 and
  <b>{sw}&#8211;{sl} at 7.25 and above</b>. The shape worth noticing is that the drop is
  not gradual: 83% through the 7.25 band, 80% through both 7.75 and 8.00, then
  {rows[9]["w"]}&#8211;{rows[9]["l"]} at 8.25&#8211;8.50. On this year's evidence the wall is
  somewhere just above 8.2, not at 7.5.</p>
  <div class="warnbox"><b>{thin} of the {sum(1 for r in rows if r["n"])} populated bands
  hold fewer than {MIN_SOLID} matches.</b> A single win reads as 100% with an interval
  running from 21% to 100%, which is to say it carries almost no information. The
  intervals overlap across most of the chart, so the ordering of the bars between 7.25
  and 8.25 should not be read as a ranking.</div>
</section>

<section>
  <h2>Two years, for the sample</h2>
  <p class="lede">The same bands over twice the window: {two["inrange"]} matches instead
  of {yr["inrange"]}. Wider intervals collapse, and the picture is less flattering
  &#8212; which is what a bigger sample usually does.</p>
  <div class="figbox">{chart(two["rows"])}</div>
  <p style="margin-top:22px">Over two years she is
  {sum(r["w"] for r in two["rows"] if r["lo"] >= 8.0)}&#8211;{sum(r["l"] for r in two["rows"] if r["lo"] >= 8.0)}
  against 8.0 and above, against {tw}&#8211;{tl} in the past year alone. Both statements are
  true; the first has the sample and the second has the recency.</p>
</section>

<section>
  <h2>The numbers</h2>
  <p class="lede">Past twelve months. Rows in grey hold fewer than {MIN_SOLID} matches.</p>
  <div class="tbox"><table>
    <tr><th class="n">TruVolley band</th><th class="n">Matches</th><th class="n">W&#8211;L</th>
    <th class="n">Win rate</th><th class="n">95% interval</th></tr>
    {table(rows)}
  </table></div>
</section>

<section>
  <h2>How this is built, and what it cannot tell you</h2>
  <ul>
    <li><b>The axis is the opponent team's mean TruVolley</b>, not the stronger of the
    two. A 9.2 paired with a 6.0 lands at 7.6, which understates how hard that side is to
    beat when the strong player takes most of the ball.</li>
    <li><b>Only {yr["rated"]} of her {yr["seen"]} matches this year can be placed here.</b>
    A match needs a published TruVolley for both opponents, and the ones missing it are
    disproportionately adult players in local draws &#8212; so the chart leans toward her
    junior schedule more than her whole schedule does.</li>
    <li><b>Win rate is not the same as rating.</b> A player who enters only events she
    can win posts a high rate; the interesting number is where the rate breaks, which is
    what the band structure is for.</li>
    <li><b>Empty bands are empty, not zero.</b> Where a band shows a dash she played
    nobody at that level, which is itself the finding: her schedule has gaps above 8.25.</li>
    <li><b>Source.</b> 679,241 matches merged from Volleyball Life, CBVA and college
    beach; TruVolley as published, cached before the API began refusing requests.</li>
  </ul>
</section>

<footer>
  Haisley Flanagan (Volleyball Life id 64896), doubles only, twelve months to
  24 August 2026. Opponent strength is published TruVolley, not the rating fitted in this
  repository. Wilson score intervals at 95%.
</footer>
</div>
"""


if __name__ == "__main__":
    open(OUT, "w").write(build())
    print("wrote", OUT)
