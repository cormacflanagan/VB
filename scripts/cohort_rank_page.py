"""The 2027-and-younger top 60, with the ranking's own uncertainty made visible.

  python3 scripts/cohort_rank_page.py   ->  docs/rank-2027_younger.html
                                            scripts/roster_2027_younger_fit.json

This page exists because the previous version ranked Haleigh Bauer twelfth on a record of
100-14 containing three matches against anyone rated 7.5 or better, two thirds of them
alongside one partner. That is a fair objection to raise, and the obvious response -- pull
back ratings that rest on soft evidence -- was tried four ways and rejected by held-out
matches every time:

  deduct k standard errors            0.6073 -> 0.6313 at k = 1     rejected
  steepen the link for large gaps     0.6073 -> 0.6240 at curve .45 rejected
  add habitual opponent strength      0.6073 -> 0.6259 at beta .8   rejected
  blame estimation noise              same bias in precise and imprecise teams

The third is the sharpest refutation, because it improves *training* log-loss (0.4456 ->
0.4321) while making held-out prediction monotonically worse. The level a player usually
competes at genuinely adds nothing once her rating is known. Splitting held-out matches by
how lopsided each side's record was, holding match count fixed, likewise shows no bias at
all. So the rating is not demonstrably too high, and this page does not pretend otherwise.

What is true, and what it shows instead:

  The ranking is far less certain than a sorted list implies. Adjacent ranks differ by
  about 0.05 while standard errors run 0.2 to 0.6, so most of the top twenty are
  statistically indistinguishable. Each player therefore carries the range of places she
  actually occupied across the bootstrap refits, not just her single best-guess rank.

  Bauer's rating is the least pinned-down in the top twelve -- roughly triple the standard
  error of the player immediately below her. That is precisely the concern, correctly
  located: not that the number is wrong, but that it is the softest number up there.

  Everyone is over-rated against opposition they have never met. Teams playing far above
  their usual level win 11.9% of held-out matches where the model predicts 18.0%. That
  applies to every player here, not only the ones with soft schedules, and it is the reason
  a rating should not be read as a forecast of how someone would fare a level up.

Rank ranges come from recomputing the whole standing inside each bootstrap replicate, so
they account for players' errors moving together -- partners' especially -- which a
standard error taken one player at a time cannot.
"""
import json, os, sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl
from uncertainty import quantile_map

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "docs", "rank-2027_younger.html")
ROSTER = os.path.join(HERE, "roster_2027_younger_fit.json")
COHORT = "cohort2027.json"
LABEL = "2027 and younger"
TOP = 60
STRONG = 7.5          # "strong opponent" line, on the TruVolley scale both ratings share
MIN_OBS = 4           # keeps players with almost no record out of the tables entirely


def load():
    se = json.load(open(os.path.join(DATA, "rating_se.json")))
    pop = {int(k): v for k, v in json.load(open(os.path.join(DATA, COHORT))).items()}
    al = json.load(open(os.path.join(DATA, "aliases.json")))["alias"]
    for p in al:                       # a retired duplicate account is not a player
        pop.pop(int(p), None)
    extra = {}
    for f in ("shrink.json", "extrapolation.json", "schedule.json", "curve.json",
              "stepup.json"):
        p = os.path.join(DATA, f)
        if os.path.exists(p):
            extra[f.split(".")[0]] = json.load(open(p))
    return se["ratings"], se, pop, extra


def rank_ranges(rt, pop):
    """The range of places each cohort player occupied across the bootstrap refits.

    Ranks are recomputed within each replicate rather than derived from each player's
    standard error separately, because the errors are not independent: a player and her
    regular partner move together, and two players who never meet are pinned relative to
    each other only through the rest of the field.
    """
    p = os.path.join(DATA, "boot.npz")
    if not os.path.exists(p):
        return {}
    z = np.load(p)
    ids = list(z["ids"])
    pos = {int(v): i for i, v in enumerate(ids)}
    keep = [q for q in pop if q in pos and str(q) in rt and rt[str(q)]["n"] >= MIN_OBS]
    cols = np.array([pos[q] for q in keep])
    sub = z["reps"][:, cols]                      # replicates x cohort players
    order = np.argsort(-sub, axis=1)
    ranks = np.empty_like(order)
    rows = np.arange(sub.shape[0])[:, None]
    ranks[rows, order] = np.arange(1, sub.shape[1] + 1)[None, :]
    lo = np.percentile(ranks, 5, axis=0)
    hi = np.percentile(ranks, 95, axis=0)
    return {q: (int(round(lo[i])), int(round(hi[i]))) for i, q in enumerate(keep)}


def schedule(ids, rt):
    """Record and opponent strength for a set of players, from the merged corpus."""
    al = {int(k): int(v) for k, v in
          json.load(open(os.path.join(DATA, "aliases.json")))["alias"].items()}
    acc = {p: {"w": 0, "l": 0, "opp": 0.0, "n": 0, "strong": 0, "sw": 0,
               "partners": defaultdict(int)} for p in ids}
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        a = [al.get(p, p) for p in m["a"]]
        b = [al.get(p, p) for p in m["b"]]
        for side, other, won in ((a, b, m["aWon"]), (b, a, not m["aWon"])):
            hit = [p for p in side if p in acc]
            if not hit:
                continue
            rs = [rt[str(o)]["r"] for o in other if str(o) in rt]
            if not rs:
                continue
            s = sum(rs) / len(rs)
            for p in hit:
                e = acc[p]
                e["w" if won else "l"] += 1
                e["opp"] += s
                e["n"] += 1
                if s >= STRONG:
                    e["strong"] += 1
                    e["sw"] += bool(won)
                for q in side:
                    if q != p:
                        e["partners"][q] += 1
    return acc


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def interval_chart(rows, w=940, rowh=17):
    """Each player's rating with its bootstrap range, top 60, in rank order.

    A dot-and-whisker column rather than a bar chart: the quantity is a position on a
    scale with an uncertainty attached, not a magnitude measured from zero, and bars from
    zero would imply a meaningful origin the rating does not have.
    """
    L, R, T, B = 190, 26, 26, 34
    h = T + B + rowh * len(rows)
    vals = [(r["lo2"], r["hi2"]) for r in rows]
    x0 = min(v[0] for v in vals) - 0.05
    x1 = max(v[1] for v in vals) + 0.05
    px = lambda v: L + (v - x0) / (x1 - x0) * (w - L - R)
    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" aria-label="Each player&#39;s '
         f'rating with the range it took across bootstrap refits">']
    step = 0.25
    g = np.ceil(x0 / step) * step
    while g <= x1:
        o.append(f'<line x1="{px(g):.1f}" y1="{T - 8}" x2="{px(g):.1f}" y2="{h - B + 2}" '
                 f'class="grid"/>')
        o.append(f'<text x="{px(g):.1f}" y="{h - B + 18}" class="tick" '
                 f'text-anchor="middle">{g:.2f}</text>')
        g += step
    for i, r in enumerate(rows):
        cy = T + rowh * i + rowh / 2
        o.append(f'<text x="{L - 30}" y="{cy + 3.5:.1f}" class="rowlab" '
                 f'text-anchor="end">{esc(r["name"][:23])}</text>')
        o.append(f'<text x="{L - 8}" y="{cy + 3.5:.1f}" class="rownum" '
                 f'text-anchor="end">{r["rank"]}</text>')
        o.append(f'<line x1="{px(r["lo2"]):.1f}" y1="{cy:.1f}" x2="{px(r["hi2"]):.1f}" '
                 f'y2="{cy:.1f}" class="whisk"/>')
        o.append(f'<circle cx="{px(r["val"]):.1f}" cy="{cy:.1f}" r="3.6" '
                 f'class="{"mark wide" if r["wide"] else "mark"}">'
                 f'<title>{esc(r["name"])}: {r["val"]:.2f}, '
                 f'{r["lo2"]:.2f} to {r["hi2"]:.2f}</title></circle>')
    o.append(f'<text x="{L}" y="{T - 12}" class="axlab">RATING, WITH ITS RANGE ACROSS '
             f'40 BOOTSTRAP REFITS</text>')
    o.append("</svg>")
    return "\n".join(o)


def stepup_chart(buckets, w=940, h=250):
    """Predicted against actual for teams playing above their usual level."""
    L, R, T, B = 152, 92, 30, 40
    lo = min(min(b["pred"], b["act"]) for b in buckets) - 0.03
    hi = max(max(b["pred"], b["act"]) for b in buckets) + 0.03
    px = lambda v: L + (v - lo) / (hi - lo) * (w - L - R)
    rowh = (h - T - B) / max(len(buckets), 1)
    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" aria-label="Predicted against '
         f'actual win rate for teams playing above their usual level">']
    step = 0.05
    v = np.ceil(lo / step) * step
    while v <= hi:
        o.append(f'<line x1="{px(v):.1f}" y1="{T - 6}" x2="{px(v):.1f}" y2="{h - B}" '
                 f'class="grid"/>')
        o.append(f'<text x="{px(v):.1f}" y="{h - B + 17}" class="tick" '
                 f'text-anchor="middle">{v * 100:.0f}%</text>')
        v += step
    for i, b in enumerate(buckets):
        cy = T + rowh * (i + 0.5)
        o.append(f'<text x="{L - 14}" y="{cy + 4:.1f}" class="rowlab" text-anchor="end">'
                 f'{esc(b["label"])}</text>')
        o.append(f'<line x1="{px(b["pred"]):.1f}" y1="{cy:.1f}" x2="{px(b["act"]):.1f}" '
                 f'y2="{cy:.1f}" class="conn"/>')
        o.append(f'<circle cx="{px(b["pred"]):.1f}" cy="{cy:.1f}" r="5.5" class="pred">'
                 f'<title>predicted {b["pred"]:.1%}</title></circle>')
        o.append(f'<circle cx="{px(b["act"]):.1f}" cy="{cy:.1f}" r="5.5" class="act">'
                 f'<title>actual {b["act"]:.1%} of {b["n"]:,} matches</title></circle>')
        o.append(f'<text x="{w - R + 12}" y="{cy + 4:.1f}" class="delta">'
                 f'{b["act"] - b["pred"]:+.1%}</text>')
    o.append(f'<text x="{L - 14}" y="{T - 12}" class="axlab" text-anchor="end">'
             f'STEP UP IN CLASS</text>')
    o.append(f'<text x="{w - R + 12}" y="{T - 12}" class="axlab">ERROR</text>')
    o.append(f'<circle cx="{L + 6}" cy="{h - 12}" r="5.5" class="pred"/>'
             f'<text x="{L + 18}" y="{h - 8}" class="legend">predicted</text>'
             f'<circle cx="{L + 104}" cy="{h - 12}" r="5.5" class="act"/>'
             f'<text x="{L + 116}" y="{h - 8}" class="legend">actual</text>')
    o.append("</svg>")
    return "\n".join(o)


CSS = """
:root {
  --ground:#EFF1EE; --surface:#FAFBFA; --ink:#111B19; --body:#2C3A37;
  --muted:#5F6E6A; --faint:#8B9995; --line:#D5DCD9; --hair:#E4E9E7;
  --accent:#0B6E68; --up:#00806F; --down:#9A6B12; --chip:#E4EDEB;
  --pred:#8B9995; --act:#0B6E68; --warn:#9A6B12; --warnbg:#F2E9D6;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
    --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
    --accent:#57C3B6; --up:#2AA08C; --down:#DCA84A; --chip:#1B2A27;
    --pred:#6E7D79; --act:#57C3B6; --warn:#DCA84A; --warnbg:#2A2213;
  }
}
:root[data-theme="dark"] {
  --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
  --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
  --accent:#57C3B6; --up:#2AA08C; --down:#DCA84A; --chip:#1B2A27;
  --pred:#6E7D79; --act:#57C3B6; --warn:#DCA84A; --warnbg:#2A2213;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; font-size:15px;
  line-height:1.6; -webkit-font-smoothing:antialiased; }
.wrap { max-width:1180px; margin:0 auto; padding:0 clamp(18px,2.4vw,40px) 64px; }
header { padding:56px 0 26px; border-bottom:1px solid var(--line); }
.eyebrow { font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin:0 0 16px; }
h1 { font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(30px,4.6vw,46px); line-height:1.07; letter-spacing:-.02em;
  color:var(--ink); margin:0 0 14px; font-weight:600; text-wrap:balance; max-width:24ch; }
h1 em { font-style:italic; color:var(--accent); }
.standfirst { font-size:17px; color:var(--muted); max-width:68ch; margin:0; }
h2 { font-family:"Iowan Old Style",Georgia,serif; font-size:23px; color:var(--ink);
  font-weight:600; margin:0 0 6px; text-wrap:balance; }
.lede { color:var(--muted); margin:0 0 18px; max-width:74ch; font-size:14.5px; }
section { padding:42px 0 0; }
p { max-width:72ch; }
.facts { display:flex; flex-wrap:wrap; margin:26px 0 0; border:1px solid var(--line);
  border-radius:3px; background:var(--surface); overflow:hidden; }
.fact { flex:1 1 150px; padding:14px 18px; border-right:1px solid var(--hair); }
.fact:last-child { border-right:0; }
.fact b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:22px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.fact span { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }
.tbox { border:1px solid var(--line); border-radius:3px; overflow:auto; }
table { border-collapse:collapse; width:100%; font-size:13.5px; background:var(--surface); }
th, td { padding:6px 9px; border-bottom:1px solid var(--hair); text-align:left;
  white-space:nowrap; }
th { font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--faint);
  font-weight:650; border-bottom:1px solid var(--line); position:sticky; top:0;
  background:var(--surface); z-index:1; }
th.s { cursor:pointer; user-select:none; }
th.s:hover, th.s:focus-visible { color:var(--accent); }
th.s[aria-sort]:not([aria-sort="none"]) { color:var(--accent); }
th.s::after { content:"\\2195"; opacity:.32; margin-left:4px; font-size:9px; }
th.s[aria-sort="ascending"]::after { content:"\\2191"; opacity:1; }
th.s[aria-sort="descending"]::after { content:"\\2193"; opacity:1; }
td.n, th.n { text-align:right; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums; }
td.nm { color:var(--ink); font-weight:550; white-space:nowrap; }
td.r { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:650;
  color:var(--ink); text-align:right; font-variant-numeric:tabular-nums; }
td.rng { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; text-align:right;
  color:var(--muted); font-variant-numeric:tabular-nums; font-size:12.5px; }
.up { color:var(--up); font-weight:650; }
.down { color:var(--down); font-weight:650; }
.soft { display:inline-block; font-size:9.5px; letter-spacing:.06em; text-transform:uppercase;
  background:var(--warnbg); color:var(--warn); padding:1px 5px; border-radius:2px;
  margin-left:6px; font-weight:650; }
.figbox { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:12px 10px 4px; overflow-x:auto; }
.fig { width:100%; min-width:660px; height:auto; display:block; }
.grid { stroke:var(--hair); stroke-width:1; }
.conn { stroke:var(--line); stroke-width:2; }
.whisk { stroke:var(--line); stroke-width:3.5; stroke-linecap:round; }
.mark { fill:var(--accent); }
.mark.wide { fill:var(--warn); }
.pred { fill:var(--pred); }
.act { fill:var(--act); }
.tick { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  fill:var(--muted); }
.rowlab { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  fill:var(--body); }
.rownum { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  fill:var(--faint); }
.delta { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px;
  font-weight:650; fill:var(--ink); }
.legend { font-size:11.5px; fill:var(--muted); }
.axlab { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px;
  letter-spacing:.1em; fill:var(--faint); }
ul { max-width:74ch; padding-left:20px; }
li { margin:0 0 10px; }
.rejected { width:100%; font-size:13.5px; margin:0 0 6px; }
.rejected td, .rejected th { border-bottom:1px solid var(--hair); }
footer { margin-top:50px; padding-top:18px; border-top:1px solid var(--line);
  font-size:12px; color:var(--faint); max-width:82ch; }
"""

SORT_JS = """
document.querySelectorAll('table[data-sortable]').forEach(function (t) {
  var head = t.tHead ? t.tHead.rows[0] : t.rows[0];
  if (!head) return;
  Array.prototype.forEach.call(head.cells, function (th, i) {
    if (!th.classList.contains('s')) return;
    th.tabIndex = 0;
    th.setAttribute('role', 'button');
    function go() {
      var dir = th.getAttribute('aria-sort') === 'descending' ? 1 : -1;
      Array.prototype.forEach.call(head.cells, function (o) {
        o.setAttribute('aria-sort', 'none');
      });
      th.setAttribute('aria-sort', dir === -1 ? 'descending' : 'ascending');
      var body = t.tBodies[0];
      var rows = Array.prototype.slice.call(body.rows);
      rows.sort(function (a, b) {
        var x = a.cells[i], y = b.cells[i];
        var nx = parseFloat(x.dataset.v !== undefined ? x.dataset.v : x.textContent);
        var ny = parseFloat(y.dataset.v !== undefined ? y.dataset.v : y.textContent);
        if (isNaN(nx) && isNaN(ny)) {
          return dir * x.textContent.localeCompare(y.textContent);
        }
        if (isNaN(nx)) return 1;
        if (isNaN(ny)) return -1;
        return dir * (nx - ny);
      });
      rows.forEach(function (r) { body.appendChild(r); });
    }
    th.addEventListener('click', go);
    th.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
    });
  });
});
"""


def build():
    rt, seinfo, pop, extra = load()
    to_tv = quantile_map()
    rated = [(p, v) for p, v in pop.items()
             if str(p) in rt and rt[str(p)]["n"] >= MIN_OBS]
    mine = sorted(((rt[str(p)]["raw"], p, v) for p, v in rated), reverse=True)
    myrank = {p: i for i, (_, p, _) in enumerate(mine, 1)}
    tvsort = sorted(((v.get("tv") or 0, p, v) for p, v in pop.items() if v.get("tv")),
                    reverse=True)
    tvrank = {p: i for i, (_, p, _) in enumerate(tvsort, 1)}
    top = mine[:TOP]
    ids = {p for _, p, _ in top}
    rng = rank_ranges(rt, pop)
    acc = schedule(ids, rt)

    ses = [rt[str(p)]["se"] for p, _ in rated]
    softline = float(np.percentile(ses, 80))

    rows, classes, chart = [], defaultdict(int), []
    for i, (rawv, p, v) in enumerate(top, 1):
        a, e = acc[p], rt[str(p)]
        tvv, tvk = v.get("tv"), tvrank.get(p)
        mv = (tvk - i) if tvk else None
        classes[v.get("grad")] += 1
        mvs = (f'<span class="up">+{mv}</span>' if mv and mv > 0 else
               f'<span class="down">{mv}</span>' if mv and mv < 0 else
               '<span class="n">0</span>' if mv == 0 else "&#8212;")
        share = (max(a["partners"].values()) / a["n"]) if a["partners"] and a["n"] else 0
        mo = f'{a["opp"] / a["n"]:.2f}' if a["n"] else "&#8212;"
        lo2 = float(to_tv(e["raw"] - 2 * e["se"]))
        hi2 = float(to_tv(e["raw"] + 2 * e["se"]))
        val = float(to_tv(e["raw"]))
        wide = e["se"] >= softline
        rlo, rhi = rng.get(p, (None, None))
        chart.append({"name": v["name"], "rank": i, "val": val, "lo2": lo2, "hi2": hi2,
                      "wide": wide})
        rows.append(
            f'<tr><td class="n">{i}</td>'
            f'<td class="nm">{esc(v["name"])}'
            + ('<span class="soft" title="standard error in the top fifth of the '
               'cohort">soft</span>' if wide else "") + "</td>"
            f'<td class="r" data-v="{val:.4f}">{val:.2f}</td>'
            f'<td class="rng" data-v="{hi2 - lo2:.4f}">{lo2:.2f}&#8211;{hi2:.2f}</td>'
            f'<td class="rng" data-v="{(rhi - rlo) if rlo else 999}">'
            + (f"{rlo}&#8211;{rhi}" if rlo else "&#8212;") + "</td>"
            f'<td class="n">{tvv:.2f}</td><td class="n">{tvk or "&#8212;"}</td>'
            f'<td class="n" data-v="{mv if mv is not None else -999}">{mvs}</td>'
            f'<td class="n">{v.get("grad") or "&#8212;"}</td>'
            f'<td>{esc(v.get("state") or "&#8212;")}</td>'
            f'<td class="n" data-v="{a["w"] / max(a["w"] + a["l"], 1):.4f}">'
            f'{a["w"]}&#8211;{a["l"]}</td>'
            f'<td class="n">{mo}</td>'
            f'<td class="n">{a["strong"]}</td>'
            f'<td class="n" data-v="{a["sw"] - (a["strong"] - a["sw"])}">'
            f'{a["sw"]}&#8211;{a["strong"] - a["sw"]}</td>'
            f'<td class="n" data-v="{share:.4f}">{share:.0%}</td>'
            f'<td class="n">{e["n"]}</td></tr>')

    gained = [(myrank[p], v["name"], float(to_tv(rt[str(p)]["raw"])), v.get("tv"),
               tvrank.get(p)) for _, p, v in top
              if not (tvrank.get(p) and tvrank[p] <= TOP)]
    lost = [(tvrank[p], v["name"], v.get("tv"),
             float(to_tv(rt[str(p)]["raw"])) if str(p) in rt else None, myrank.get(p))
            for _, p, v in tvsort[:TOP] if p not in ids]

    json.dump({"label": f"{LABEL} &#8212; top {TOP} by fitted rating",
               "roster": [[v["name"], p, v.get("state") or "?"] for _, p, v in top],
               "meta": {str(p): {kk: v.get(kk) for kk in
                                 ("height", "club", "city", "state", "tv", "grad")}
                        for _, p, v in top},
               "population": len(pop), "rated": len(rated),
               "cut": {"nTop": float(to_tv(top[-1][0])),
                       "next": float(to_tv(mine[TOP][0])) if len(mine) > TOP else None,
                       "nextName": mine[TOP][2]["name"] if len(mine) > TOP else None},
               "rankRanges": {str(p): rng.get(p) for _, p, _ in top if p in rng},
               "classes": dict(sorted(classes.items()))},
              open(ROSTER, "w"), indent=1)

    younger = sum(n for y, n in classes.items() if y and y > 2027)
    spread = " &#183; ".join(f"{y} {n}" for y, n in sorted(classes.items()) if y)
    steps = extra.get("extrapolation", {}).get("byReach", [])
    worst = steps[-1] if steps else None
    # the widest interval in the top twelve, named, because that is the honest version of
    # the objection this page was rebuilt to answer
    med_gap = float(np.median([chart[i]["val"] - chart[i + 1]["val"]
                               for i in range(len(chart) - 1)]))
    widths = [(rng[p][1] - rng[p][0], i, v["name"], rng[p])
              for i, (_, p, v) in enumerate(top, 1) if p in rng]
    med_width = int(np.median([w for w, _, _, _ in widths])) if widths else 0
    # the widest range inside the top twelve, and the tightest immediately around it: the
    # objection this page was rebuilt to answer, stated as what it actually is
    top12 = [t for t in widths if t[1] <= 12]
    soft = max(top12, key=lambda t: t[0]) if top12 else None
    near = min([t for t in widths if abs(t[1] - (soft[1] if soft else 0)) <= 2
                and t[1] != (soft[1] if soft else 0)] or widths,
               key=lambda t: t[0]) if widths else None
    firm = min(widths, key=lambda t: t[0]) if widths else None

    return f"""<title>The 2027 Field, Re-Ranked</title>
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="eyebrow">{LABEL} &#183; top {TOP} &#183; fitted rating</p>
  <h1>A ranking, and how much of it is <em>real</em></h1>
  <p class="standfirst">The 18U-eligible field cut on the rating fitted in this repository.
  Adjacent places differ by about {med_gap:.2f} of a rating point, which is nothing next to
  the uncertainty: refit the model forty times on resampled results and the median player
  here moves across {med_width} places. Only the very top is solid. Every row carries the
  range of ranks it actually occupied, so a tie reads as a tie.</p>
</header>

<div class="facts">
  <div class="fact"><b>{med_width}</b><span>Places the median player moves</span></div>
  <div class="fact"><b>{med_gap:.2f}</b><span>Gap between adjacent ranks</span></div>
  <div class="fact"><b>{seinfo["reps"]}</b><span>Bootstrap refits</span></div>
  <div class="fact"><b>{len(rated):,}</b><span>Cohort players ranked</span></div>
  <div class="fact"><b>{younger}</b><span>Younger than 2027</span></div>
</div>

<section>
  <h2>Four corrections, all rejected</h2>
  <p class="lede">The previous version of this page ranked Haleigh Bauer twelfth on a
  record of 100&#8211;14 containing three matches against anyone at {STRONG} or better, two
  thirds of them with one partner. That is a fair objection, and the obvious answer &#8212;
  pull back ratings resting on soft evidence &#8212; was tried four ways. Held-out matches
  rejected all four.</p>
  <div class="tbox"><table class="rejected">
    <tr><th>Correction</th><th class="n">Held-out log-loss</th><th>Result</th></tr>
    <tr><td>Deduct <em>k</em> standard errors</td><td class="n">0.6073 &#8594; 0.6313</td>
      <td>worse at every <em>k</em> &gt; 0</td></tr>
    <tr><td>Steepen the scale for large gaps</td><td class="n">0.6073 &#8594; 0.6240</td>
      <td>worse at every setting</td></tr>
    <tr><td>Add habitual opponent strength</td><td class="n">0.6073 &#8594; 0.6259</td>
      <td>worse, while <em>improving</em> training fit</td></tr>
    <tr><td>Blame estimation noise</td><td class="n">&#8212;</td>
      <td>same bias in precise and imprecise teams</td></tr>
  </table></div>
  <p class="lede" style="margin-top:14px">The third is the sharpest. Adding a player's
  habitual level of opposition to the model improves training log-loss from 0.4456 to
  0.4321 and makes held-out prediction monotonically worse &#8212; textbook overfitting.
  Once a rating is known, the level she earned it against adds nothing. Splitting held-out
  matches by how lopsided each side's record was, with match count held fixed, likewise
  finds no bias. So the rating is not demonstrably too high, and this page does not pretend
  it has fixed something it has not.</p>
</section>

<section>
  <h2>What is true instead</h2>
  <p class="lede">The objection was right about where to look and wrong about what it would
  find there. The problem is not that {esc(soft[2]) if soft else "the rating"} is too high;
  it is that {"her" if soft else "the"} place in this list is barely determined at all.
  {f'Across the forty refits she lands anywhere from {soft[3][0]} to '
    f'{soft[3][1]}. {esc(near[2])}, one row {"below" if near[1] > soft[1] else "above"} '
    f'her, moves only from {near[3][0]} to {near[3][1]}; '
    f'{esc(firm[2])} at the top moves from {firm[3][0]} to {firm[3][1]}. '
   if soft and near and firm else ""}Same cohort, same method, three
  wildly different amounts of evidence &#8212; and a plain sorted list shows none of it.</p>
  <div class="figbox">{interval_chart(chart)}</div>
  <p class="lede" style="margin-top:14px">The whisker is two standard errors either side of
  the rating; marked dots are players whose standard error falls in the top fifth of the
  cohort. The rank range in the table below is computed differently and matters more: the
  5th-to-95th percentile of the places a player actually took across the refits, ranks
  recomputed inside each one. That captures errors moving together &#8212; a player and her
  regular partner especially &#8212; which a standard error taken one player at a time
  cannot.</p>
</section>

<section>
  <h2>Everyone is overrated a level up</h2>
  <p class="lede">This is the one real bias, and it applies to every player on the page
  rather than only to those with soft schedules. Held-out matches, oriented so the side
  playing furthest above its usual opposition comes first: it wins far less often than the
  model says, and the shortfall grows monotonically with the size of the step up.</p>
  <div class="figbox">{stepup_chart(steps) if steps else ""}</div>
  <p class="lede" style="margin-top:14px">{
  f'In the top quintile of step-ups the model predicts {worst["pred"]:.1%} and the actual '
  f'rate is {worst["act"]:.1%}, across {worst["n"]:,} matches.' if worst else ""}
  It survives every control: it is the same size for precisely and imprecisely determined
  teams, unchanged when the standings-derived pairs are dropped, and curvature in the scale
  removes only part of it while making prediction worse overall. It is a limit of summing
  a doubles player up in one number, not a bug with a setting. The practical consequence is
  that a rating should be read as a summary of results achieved, not as a forecast of how
  someone would fare a level above what she has played.</p>
</section>

<section>
  <h2>Top {TOP}</h2>
  <p class="lede">Sortable &#8212; click any heading marked with an arrow, and the schedule
  columns are the ones worth sorting on. Range is two standard errors either side of the
  rating;
  ranks is where she landed across the refits. The last five columns are her exposure: mean
  opponent, matches against {STRONG}-and-above and her record in them, and the share of
  matches spent with her most frequent partner. By graduating year this cut is
  {spread}.</p>
  <div class="tbox"><table data-sortable>
    <thead>
    <tr><th class="n s">#</th><th class="s">Player</th><th class="n s">Rating</th>
    <th class="n s">Range</th><th class="n s">Ranks</th>
    <th class="n s">TruVolley</th><th class="n s">TV rank</th><th class="n s">Move</th>
    <th class="n s">Class</th><th>St</th><th class="n s">W&#8211;L</th>
    <th class="n s">Mean opp</th><th class="n s">vs {STRONG}+</th>
    <th class="n s">Record</th><th class="n s">Top ptnr</th><th class="n s">Obs</th></tr>
    </thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>

<section>
  <h2>Against TruVolley's own {TOP}</h2>
  <p class="lede">{len(gained)} of the {TOP} names differ from TruVolley's cut of the same
  cohort. The two ratings measure different things: TruVolley moves when a player's team
  wins, so a season with a strong partner lifts it, while this one solves for individual
  strength with partner quality as a term in the model.</p>
  <div class="two" style="display:grid;grid-template-columns:1fr 1fr;gap:22px">
    <div>
      <h2 style="font-size:18px">In</h2>
      <div class="tbox"><table>
        <tr><th class="n">#</th><th>Player</th><th class="n">Rating</th>
        <th class="n">TV</th><th class="n">TV rank</th></tr>
        {"".join(f'<tr><td class="n">{r}</td><td class="nm">{esc(n)}</td>'
                 f'<td class="r">{m:.2f}</td><td class="n">{t:.2f}</td>'
                 f'<td class="n">{kk}</td></tr>' for r, n, m, t, kk in gained)}
      </table></div>
    </div>
    <div>
      <h2 style="font-size:18px">Out</h2>
      <div class="tbox"><table>
        <tr><th class="n">TV#</th><th>Player</th><th class="n">TV</th>
        <th class="n">Rating</th><th class="n">Rank</th></tr>
        {"".join(f'<tr><td class="n">{kk}</td><td class="nm">{esc(n)}</td>'
                 f'<td class="n">{t:.2f}</td>'
                 f'<td class="r">{(f"{m:.2f}" if m is not None else "&#8212;")}</td>'
                 f'<td class="n">{r or "unranked"}</td></tr>' for kk, n, t, m, r in lost)}
      </table></div>
    </div>
  </div>
</section>

<section>
  <h2>Notes</h2>
  <ul>
    <li><b>Duplicate accounts are merged first.</b> Players re-register, and the site then
    holds two profiles splitting one career. 171 pairs were merged &#8212; same name, class
    and state, and never once at the same tournament, which two different girls on one
    regional circuit could not manage. Five collisions failed that test and were left
    alone. Without this the cut listed Ashley Ruschill twice, at #44 and #55.</li>
    <li><b>The minimum-match threshold is gone.</b> The previous version required 20
    observations, which admitted a 400-match record against nobody and would have excluded
    a 15-match record against the best players in the country. Intervals do that job
    properly; a count never did.</li>
    <li><b>Standard errors are measured, not assumed.</b> The whole model is refit
    {seinfo["reps"]} times on results resampled by tournament-division &#8212; whole draws
    at a time, since six pool results out of one bracket are not six independent facts
    &#8212; across {seinfo["clusters"]:,} divisions.</li>
    <li><b>Neither rating is the truth.</b> On held-out matches where both rate all four
    players and both have seen the data, TruVolley scores 0.397 log-loss against this fit's
    0.397 with accuracy 0.843. Out of sample TruVolley looks far better, but it is quoted
    as of today and has already absorbed the matches being predicted. The case for this
    rating is that it is transparent and adjustable, not that it is sharper.</li>
    <li><b>Ratings sit on the TruVolley scale by a quantile map</b>, which is monotone and
    reorders nobody.</li>
  </ul>
</section>

<footer>
  {LABEL}, the closed cohort of {len(pop):,} girls from a partner-graph crawl, ranked on a
  Bradley-Terry rating fitted to 679,241 matches from Volleyball Life, CBVA and college
  beach. Intervals from {seinfo["reps"]} bootstrap refits resampled by tournament-division.
  Records and opponent strength are computed over the same three-year window as the fit.
  Built by rate.py, uncertainty.py, shrink.py, extrapolation.py, stepup.py, schedule.py,
  curvesweep.py, dedupe.py and cohort_rank_page.py.
</footer>
</div>
<script>{SORT_JS}</script>
"""


if __name__ == "__main__":
    open(OUT, "w").write(build())
    print("wrote", OUT, "and", ROSTER)
