"""The 2027-and-younger top 60, ranked on what the results actually establish.

  python3 scripts/cohort_rank_page.py   ->  docs/rank-2027_younger.html
                                            scripts/roster_2027_younger_fit.json

The first version of this page ranked the cohort on the raw maximum-likelihood rating from
scripts/rate.py, and it put Haleigh Bauer twelfth on a record of 100-14 that contained
three matches against anyone rated 7.5 or better. That is not a quibble about her; it is
the ranking reporting a number the evidence does not support, and it would do the same for
anyone whose schedule had that shape.

Two things starve a rating of evidence, and a match count detects neither:

  A lopsided schedule. A logistic model learns from a result in proportion to p(1-p), so a
  match won 96% of the time is worth about a twentieth of a coin-flip. A long record
  against overmatched fields is a small amount of evidence wearing a large number.

  A single partner. `strength(team) = mean(r1, r2)` pins the pair down and leaves the split
  between its halves loose. Play two thirds of your matches with one person and your own
  rating is largely inferred rather than observed.

scripts/uncertainty.py measures both at once by refitting the whole model on resampled
evidence and watching which ratings move, and scripts/shrink.py checks on held-out matches
whether the loosely-determined ones are systematically overrated -- they are -- and tunes
how far to pull them back. This page ranks on the pulled-back number.

That changes the question being answered. The old ranking asked how good a player might
be; this one asks how good her results oblige us to say she is. A player who has beaten
strong opposition repeatedly barely moves. A player whose record is long, lopsided and
shared with one partner moves a long way, and the schedule columns show why.

The old minimum-observations threshold is gone. It was a crude stand-in for exactly this,
and a bad one: it admitted a 400-match record against nobody and excluded a 15-match
record against the best players in the country.
"""
import json, os, sys
from collections import defaultdict

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
MIN_OBS = 4           # only to keep players with almost no record out of the tables


def load():
    se = json.load(open(os.path.join(DATA, "rating_se.json")))
    sh = json.load(open(os.path.join(DATA, "shrink.json")))
    pop = {int(k): v for k, v in json.load(open(os.path.join(DATA, COHORT))).items()}
    al = json.load(open(os.path.join(DATA, "aliases.json")))["alias"]
    for p in al:                       # a retired duplicate account is not a player
        pop.pop(int(p), None)
    return se["ratings"], se, sh, pop


def schedule(ids, rt):
    """Record and opponent strength for a set of players, from the merged corpus.

    Opponent strength uses the point estimate, not the shrunk one: the question these
    columns answer is who she played, and the best available reading of an opponent's
    strength is the unshrunk one.
    """
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


def scatter(pairs, w=940, h=340):
    """Ranking rating against TruVolley for the cohort's rated players."""
    L, R, T, B = 56, 20, 22, 46
    x0, x1, y0, y1 = 5.5, 10.5, 5.5, 10.5
    px = lambda v: L + (v - x0) / (x1 - x0) * (w - L - R)
    py = lambda v: h - B - (v - y0) / (y1 - y0) * (h - T - B)
    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" aria-label="Ranking rating '
         f'against TruVolley">']
    for v in range(6, 11):
        o.append(f'<line x1="{px(v):.1f}" y1="{T}" x2="{px(v):.1f}" y2="{h - B}" class="grid"/>')
        o.append(f'<line x1="{L}" y1="{py(v):.1f}" x2="{w - R}" y2="{py(v):.1f}" class="grid"/>')
        o.append(f'<text x="{px(v):.1f}" y="{h - B + 18}" class="tick" text-anchor="middle">{v}</text>')
        o.append(f'<text x="{L - 8}" y="{py(v) + 4:.1f}" class="tick" text-anchor="end">{v}</text>')
    o.append(f'<line x1="{px(y0):.1f}" y1="{py(y0):.1f}" x2="{px(y1):.1f}" '
             f'y2="{py(y1):.1f}" class="diag"/>')
    for tvv, mine, nm, top in pairs:
        if not (x0 <= tvv <= x1 and y0 <= mine <= y1):
            continue
        o.append(f'<circle cx="{px(tvv):.1f}" cy="{py(mine):.1f}" r="{3.6 if top else 2.4}" '
                 f'class="{"dot top" if top else "dot"}">'
                 f'<title>{esc(nm)}: TruVolley {tvv:.2f}, ranked at {mine:.2f}</title></circle>')
    o.append(f'<text x="{(L + w - R) / 2:.0f}" y="{h - 8}" class="axlab" '
             f'text-anchor="middle">TRUVOLLEY</text>')
    o.append(f'<text x="14" y="{(T + h - B) / 2:.0f}" class="axlab" '
             f'transform="rotate(-90 14 {(T + h - B) / 2:.0f})" text-anchor="middle">'
             f'RANKING RATING</text>')
    o.append("</svg>")
    return "\n".join(o)


def calibration(buckets, w=940, h=300):
    """Predicted vs actual win rate for the less well determined side, by how much less.

    A paired-dot row per bucket rather than two bar series: the quantity that matters is
    the gap between the two values within a bucket, and a connector draws the eye to a gap
    in a way that two bars separated by a category boundary does not.
    """
    L, R, T, B = 150, 92, 30, 40
    lo = min(min(b["pred"], b["act"]) for b in buckets) - 0.03
    hi = max(max(b["pred"], b["act"]) for b in buckets) + 0.03
    px = lambda v: L + (v - lo) / (hi - lo) * (w - L - R)
    rowh = (h - T - B) / max(len(buckets), 1)
    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" aria-label="Predicted against '
         f'actual win rate by how loosely determined the players are">']
    step = 0.05
    v = round(lo / step) * step
    while v <= hi:
        if v >= lo:
            o.append(f'<line x1="{px(v):.1f}" y1="{T - 6}" x2="{px(v):.1f}" '
                     f'y2="{h - B}" class="grid"/>')
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
             f'SE GAP BETWEEN THE SIDES</text>')
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
  --pred:#8B9995; --act:#0B6E68;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
    --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
    --accent:#57C3B6; --up:#2AA08C; --down:#DCA84A; --chip:#1B2A27;
    --pred:#6E7D79; --act:#57C3B6;
  }
}
:root[data-theme="dark"] {
  --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
  --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
  --accent:#57C3B6; --up:#2AA08C; --down:#DCA84A; --chip:#1B2A27;
  --pred:#6E7D79; --act:#57C3B6;
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
.fact { flex:1 1 140px; padding:14px 18px; border-right:1px solid var(--hair); }
.fact:last-child { border-right:0; }
.fact b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.fact span { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }
.tbox { border:1px solid var(--line); border-radius:3px; overflow:auto; }
table { border-collapse:collapse; width:100%; font-size:13.5px; background:var(--surface); }
th, td { padding:6px 9px; border-bottom:1px solid var(--hair); text-align:left;
  white-space:nowrap; }
th { font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--faint);
  font-weight:650; border-bottom:1px solid var(--line); position:sticky; top:0;
  background:var(--surface); z-index:1; }
td.n, th.n { text-align:right; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums; }
td.nm { color:var(--ink); font-weight:550; white-space:nowrap; }
td.r { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-weight:650;
  color:var(--ink); text-align:right; font-variant-numeric:tabular-nums; }
td.pm { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; text-align:right;
  color:var(--faint); font-variant-numeric:tabular-nums; font-size:12.5px; }
.up { color:var(--up); font-weight:650; }
.down { color:var(--down); font-weight:650; }
.new { display:inline-block; font-size:9.5px; letter-spacing:.07em; text-transform:uppercase;
  background:var(--chip); color:var(--accent); padding:1px 5px; border-radius:2px;
  margin-left:6px; font-weight:650; }
.figbox { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:12px 10px 4px; overflow-x:auto; }
.fig { width:100%; min-width:660px; height:auto; display:block; }
.grid { stroke:var(--hair); stroke-width:1; }
.diag { stroke:var(--line); stroke-width:1.2; stroke-dasharray:4 4; }
.dot { fill:var(--muted); fill-opacity:.35; }
.dot.top { fill:var(--accent); fill-opacity:.85; }
.conn { stroke:var(--line); stroke-width:2; }
.pred { fill:var(--pred); }
.act { fill:var(--act); }
.tick { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  fill:var(--muted); }
.rowlab { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11.5px;
  fill:var(--body); }
.delta { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px;
  font-weight:650; fill:var(--ink); }
.legend { font-size:11.5px; fill:var(--muted); }
.axlab { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px;
  letter-spacing:.1em; fill:var(--faint); }
.two { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
@media (max-width:820px) { .two { grid-template-columns:1fr; } }
ul { max-width:74ch; padding-left:20px; }
li { margin:0 0 10px; }
footer { margin-top:50px; padding-top:18px; border-top:1px solid var(--line);
  font-size:12px; color:var(--faint); max-width:82ch; }
"""


def build():
    rt, seinfo, sh, pop = load()
    k = sh["k"]
    rated = [(p, v) for p, v in pop.items()
             if str(p) in rt and rt[str(p)]["n"] >= MIN_OBS]

    # The ranking number: the point estimate pulled back by k standard errors, then put on
    # the TruVolley scale. Deduct first and map second -- the quantile map is monotone but
    # not linear, so scaling the already-mapped k=1 gap in the file would be wrong wherever
    # the map's slope changes, which is precisely at the top where this matters most.
    to_tv = quantile_map()

    def rank_val(e):
        return float(to_tv(e["raw"] - k * e["se"]))

    mine = sorted(((rank_val(rt[str(p)]), p, v) for p, v in rated), reverse=True)
    myrank = {p: i for i, (_, p, _) in enumerate(mine, 1)}
    raw = sorted(((rt[str(p)]["r"], p, v) for p, v in rated), reverse=True)
    rawrank = {p: i for i, (_, p, _) in enumerate(raw, 1)}
    tvsort = sorted(((v.get("tv") or 0, p, v) for p, v in pop.items() if v.get("tv")),
                    reverse=True)
    tvrank = {p: i for i, (_, p, _) in enumerate(tvsort, 1)}
    top = mine[:TOP]
    ids = {p for _, p, _ in top}
    acc = schedule(ids | {p for _, p, _ in raw[:TOP]}, rt)

    rows, classes = [], defaultdict(int)
    for i, (r, p, v) in enumerate(top, 1):
        a = acc[p]
        e = rt[str(p)]
        tvv, tvk = v.get("tv"), tvrank.get(p)
        mv = (tvk - i) if tvk else None
        classes[v.get("grad")] += 1
        mvs = (f'<span class="up">+{mv}</span>' if mv and mv > 0 else
               f'<span class="down">{mv}</span>' if mv and mv < 0 else
               '<span class="n">0</span>' if mv == 0 else "&#8212;")
        share = (max(a["partners"].values()) / a["n"]) if a["partners"] and a["n"] else 0
        mo = f'{a["opp"] / a["n"]:.2f}' if a["n"] else "&#8212;"
        rows.append(
            f'<tr><td class="n">{i}</td>'
            f'<td class="nm">{esc(v["name"])}'
            + ("" if tvk and tvk <= TOP else '<span class="new">new</span>') + "</td>"
            f'<td class="r">{r:.3f}</td>'
            f'<td class="pm">&#8722;{e["r"] - r:.2f}</td>'
            f'<td class="n">{e["r"]:.3f}</td>'
            f'<td class="n">{tvv:.3f}</td><td class="n">{tvk or "&#8212;"}</td>'
            f'<td class="n">{mvs}</td>'
            f'<td class="n">{v.get("grad") or "&#8212;"}</td>'
            f'<td class="n">{esc(v["height"]) if v.get("height") else "&#8212;"}</td>'
            f'<td>{esc(v.get("state") or "&#8212;")}</td>'
            f'<td class="n">{a["w"]}&#8211;{a["l"]}</td>'
            f'<td class="n">{mo}</td>'
            f'<td class="n">{a["strong"]}</td>'
            f'<td class="n">{a["sw"]}&#8211;{a["strong"] - a["sw"]}</td>'
            f'<td class="n">{share:.0%}</td>'
            f'<td class="n">{e["n"]}</td></tr>')

    gained = [(myrank[p], v["name"], rank_val(rt[str(p)]), v.get("tv"), tvrank.get(p))
              for _, p, v in top if not (tvrank.get(p) and tvrank[p] <= TOP)]
    lost = [(tvrank[p], v["name"], v.get("tv"),
             rank_val(rt[str(p)]) if str(p) in rt else None, myrank.get(p))
            for _, p, v in tvsort[:TOP] if p not in ids]

    # what the correction itself moved: biggest fallers out of the unshrunk top 60
    dropped = []
    for _, p, v in raw[:TOP]:
        if p in ids:
            continue
        e, a = rt[str(p)], acc[p]
        dropped.append((rawrank[p], myrank[p], v["name"], e["r"], rank_val(e),
                        a["strong"], a["sw"], a["n"],
                        (max(a["partners"].values()) / a["n"]) if a["n"] else 0))
    dropped.sort(key=lambda t: t[1] - t[0], reverse=True)

    pairs = [(v.get("tv"), rank_val(rt[str(p)]), v["name"], p in ids)
             for p, v in rated if v.get("tv")]
    json.dump({"label": f"{LABEL} &#8212; top {TOP} by evidence-weighted rating",
               "k": k,
               "roster": [[v["name"], p, v.get("state") or "?"] for _, p, v in top],
               "meta": {str(p): {kk: v.get(kk) for kk in
                                 ("height", "club", "city", "state", "tv", "grad")}
                        for _, p, v in top},
               "population": len(pop), "rated": len(rated),
               "cut": {"nTop": top[-1][0],
                       "next": mine[TOP][0] if len(mine) > TOP else None,
                       "nextName": mine[TOP][2]["name"] if len(mine) > TOP else None},
               "classes": dict(sorted(classes.items()))},
              open(ROSTER, "w"), indent=1)

    younger = sum(n for y, n in classes.items() if y and y > 2027)
    spread = " &#183; ".join(f"{y} {n}" for y, n in sorted(classes.items()) if y)
    hi = max(acc[p]["strong"] for p in ids)
    hardest = [v["name"] for _, p, v in top if acc[p]["strong"] == hi][0]
    buckets = sh["calibration"]
    worst = max(buckets, key=lambda b: b["pred"] - b["act"])
    bias = worst["pred"] - worst["act"]
    lead = dropped[0] if dropped else None

    # The page has to be able to report that the correction was unnecessary. If held-out
    # matches show no bias, or the tuning picks k = 0, saying otherwise would be inventing
    # the result the page was built to look for.
    if k > 0 and bias > 0.005:
        verdict = (f"produces a confident-looking number that held-out matches show to be "
                   f"too high &#8212; by {bias:.1%} in the worst case. This ranking removes "
                   f"that.")
    elif k > 0:
        verdict = ("produces a number the results barely constrain. Held-out matches show "
                   "little systematic bias, but pulling each rating back to what its own "
                   "evidence supports still predicts them better.")
    else:
        verdict = ("produces a number the results barely constrain. Held-out matches "
                   "decline to call it inflated, so nothing is deducted here and the "
                   "ranking is the raw fit &#8212; the uncertainty is shown instead.")

    return f"""<title>The 2027 Field, Re-Ranked</title>
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="eyebrow">{LABEL} &#183; top {TOP} &#183; evidence-weighted rating</p>
  <h1>Ranked on what the results <em>establish</em></h1>
  <p class="standfirst">The 18U-eligible field, cut on a rating that is pulled back in
  proportion to how loosely a player's own results pin it down. A long record against
  overmatched opposition, or one shared almost entirely with a single partner,
  {verdict}</p>
</header>

<div class="facts">
  <div class="fact"><b>{k:g}&#215;</b><span>Standard errors deducted</span></div>
  <div class="fact"><b>{len(dropped)}</b><span>Fall out of the raw top {TOP}</span></div>
  <div class="fact"><b>{top[-1][0]:.3f}</b><span>Cut at #{TOP}</span></div>
  <div class="fact"><b>{len(rated):,}</b><span>Cohort players ranked</span></div>
  <div class="fact"><b>{younger}</b><span>Younger than 2027</span></div>
</div>

<section>
  <h2>The correction, measured rather than asserted</h2>
  <p class="lede">Every held-out match is oriented so the side whose players are the more
  loosely determined comes first, then grouped by how much looser they are. If the
  unshrunk rating were unbiased, the two dots in each row would sit on top of each other.
  {"They do not: the shakier side loses more often than it is predicted to. That is the raw"
   " rating being too generous to thin evidence"
   if bias > 0.005 else
   "They very nearly do, so the raw rating is not badly biased on average"} &#8212; measured
  across {sum(b["n"] for b in buckets):,} matches the model never saw.</p>
  <div class="figbox">{calibration(buckets)}</div>
  <p class="lede" style="margin-top:14px">How far to pull back is then not a matter of
  taste. Deducting <em>k</em> standard errors and scoring the same held-out matches gives a
  best <em>k</em> of {k:g}
  {"&#8212; the correction pays for itself in prediction, not just in fairness"
   if k > 0 else "&#8212; see the caveat below"}.</p>
</section>

<section>
  <h2>Top {TOP}</h2>
  <p class="lede">Rating is the ranking number; the small figure beside it is how far the
  point estimate was pulled back, and the next column is that point estimate. TV rank is
  the player's place in the same cohort on TruVolley. The last six columns are the
  evidence: her record, the mean rating of her opposition, how many matches came against
  {STRONG}-and-above and her record in them, and the share of her matches played with her
  most frequent partner &#8212; the two things that make a rating hard to pin down. By
  graduating year this cut is {spread}.</p>
  <div class="tbox"><table>
    <tr><th class="n">#</th><th>Player</th><th class="n">Rating</th><th class="n">Pull</th>
    <th class="n">Point</th><th class="n">TruVolley</th>
    <th class="n">TV rank</th><th class="n">Move</th><th class="n">Class</th>
    <th class="n">Ht</th><th>St</th><th class="n">W&#8211;L</th><th class="n">Mean opp</th>
    <th class="n">vs {STRONG}+</th><th class="n">Record</th><th class="n">Top ptnr</th>
    <th class="n">Obs</th></tr>
    {"".join(rows)}
  </table></div>
</section>

<section>
  <h2>Who the correction moved</h2>
  <p class="lede">These {len(dropped)} were inside the top {TOP} on the unshrunk rating and
  are not now. The pattern is the point: few matches against strong opposition, a high
  share with one partner, or both.{
  f' {esc(lead[2])} is the case that prompted this page &#8212; ranked {lead[0]} on the raw'
  f' number with {lead[5]} matches against {STRONG}-and-above out of {lead[7]}, and'
  f' {lead[8]:.0%} of them alongside one partner.' if lead else ""}</p>
  <div class="tbox"><table>
    <tr><th class="n">Raw #</th><th class="n">Now</th><th>Player</th>
    <th class="n">Point</th><th class="n">Rating</th><th class="n">vs {STRONG}+</th>
    <th class="n">Record</th><th class="n">Obs</th><th class="n">Top ptnr</th></tr>
    {"".join(f'<tr><td class="n">{a}</td><td class="n"><span class="down">{b}</span></td>'
             f'<td class="nm">{esc(nm)}</td><td class="n">{pt:.3f}</td>'
             f'<td class="r">{rv:.3f}</td><td class="n">{st}</td>'
             f'<td class="n">{sw}&#8211;{st - sw}</td><td class="n">{n}</td>'
             f'<td class="n">{sh_:.0%}</td></tr>'
             for a, b, nm, pt, rv, st, sw, n, sh_ in dropped)}
  </table></div>
</section>

<section>
  <h2>Where this lands against TruVolley</h2>
  <p class="lede">Each dot is a cohort player with both numbers; the {TOP} in this cut are
  filled. The dashed line is agreement. The whole cloud sits below it now, because every
  rating here has been pulled back &#8212; what matters is the spread around the line, not
  the offset.</p>
  <div class="figbox">{scatter(pairs)}</div>
  <div class="two" style="margin-top:26px">
    <div>
      <h2 style="font-size:18px">In, against TruVolley's {TOP}</h2>
      <div class="tbox"><table>
        <tr><th class="n">#</th><th>Player</th><th class="n">Rating</th>
        <th class="n">TV</th><th class="n">TV rank</th></tr>
        {"".join(f'<tr><td class="n">{r}</td><td class="nm">{esc(n)}</td>'
                 f'<td class="r">{m:.3f}</td><td class="n">{t:.3f}</td>'
                 f'<td class="n">{kk}</td></tr>' for r, n, m, t, kk in gained)}
      </table></div>
    </div>
    <div>
      <h2 style="font-size:18px">Out, against TruVolley's {TOP}</h2>
      <div class="tbox"><table>
        <tr><th class="n">TV#</th><th>Player</th><th class="n">TV</th>
        <th class="n">Rating</th><th class="n">Rank</th></tr>
        {"".join(f'<tr><td class="n">{kk}</td><td class="nm">{esc(n)}</td>'
                 f'<td class="n">{t:.3f}</td>'
                 f'<td class="r">{(f"{m:.3f}" if m else "&#8212;")}</td>'
                 f'<td class="n">{r or "unranked"}</td></tr>' for kk, n, t, m, r in lost)}
      </table></div>
    </div>
  </div>
</section>

<section>
  <h2>What this ranking is and is not</h2>
  <ul>
    <li><b>It answers a different question from the raw fit.</b> The point estimate is the
    model's best guess at how good a player is, and it is the right number to predict a
    match with. This column is the number her results oblige us to state, which is the
    right one to rank with. They differ most where the evidence is thinnest, which is
    exactly where a ranking does the most damage by guessing.</li>
    <li><b>The standard error is measured, not assumed.</b> The whole model is refit
    {seinfo["reps"]} times on evidence resampled by tournament-division &#8212; whole draws
    at a time, since six pool results out of one bracket are not six independent facts
    &#8212; and the spread of each player's rating across those refits is her standard
    error. It captures both failure modes at once: a lopsided schedule and a single
    partner both make a rating move under resampling.</li>
    <li><b>A match count cannot substitute for it.</b> The old version of this page
    required 20 observations, which admitted a 400-match record against nobody and would
    have excluded a 15-match record against the best players in the country. That
    threshold is gone.</li>
    <li><b>Opponent strength is still priced explicitly.</b> {esc(hardest)} played the
    hardest schedule in this {TOP}, at {hi} matches against {STRONG}-and-above. Beating the
    same local field every weekend earns little; losing narrowly to much stronger teams
    costs little.</li>
    <li><b>Duplicate accounts are merged first.</b> Players re-register, and the site then
    holds two profiles splitting one career. 171 such pairs were found and merged &#8212;
    same name, class and state, and never once at the same tournament, which two different
    girls on one regional circuit could not manage. Without it this cut listed Ashley
    Ruschill twice, at #44 and #55.</li>
    <li><b>Neither rating is the truth.</b> On held-out matches TruVolley and the raw fit
    are close, and TruVolley is quoted as of today so it has already absorbed the matches
    being predicted. The case for this ranking is that it is transparent, tunable, and
    honest about what it does not know.</li>
  </ul>
</section>

<footer>
  {LABEL}, the closed cohort of {len(pop):,} girls from a partner-graph crawl, ranked on a
  Bradley-Terry rating fitted to 679,241 matches from Volleyball Life, CBVA and college
  beach, then reduced by {k:g} standard errors estimated from {seinfo["reps"]} bootstrap
  refits over {seinfo["clusters"]:,} tournament-divisions. Records and opponent strength
  are computed over the same three-year window as the fit. Built by scripts/rate.py,
  scripts/uncertainty.py, scripts/shrink.py and scripts/cohort_rank_page.py.
</footer>
</div>
"""


if __name__ == "__main__":
    open(OUT, "w").write(build())
    print("wrote", OUT, "and", ROSTER)
