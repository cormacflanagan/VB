"""The 2027-and-younger top 60, ranked by the fitted rating instead of TruVolley.

  python3 scripts/cohort_rank_page.py   ->  docs/rank-2027_younger.html
                                            scripts/roster_2027_younger_fit.json

Every other report in this repo cuts its group on TruVolley. This one cuts the same closed
cohort -- grad 2027 and younger, 17,178 girls -- on the rating fitted in scripts/rate.py,
which changes who is in the top 60 and not merely the order: nineteen names swap.

The two ratings measure different things. TruVolley moves when a player's *team* wins, so
a season with a strong partner lifts it. The fitted rating solves for individual strength
from match outcomes with partner quality as a term in the model, and it prices opponent
strength explicitly -- so a player who beats the same people every week gains little, and
one who loses narrowly to much better teams is not punished for entering.

The schedule columns are the explanation, not decoration: a player's mean opponent and her
share of matches against 7.5-and-above are usually enough to see why the two ratings
disagree about her.

A cohort member needs MIN_OBS observations to be ranked at all. The threshold barely
matters at the top -- the overlap with the TruVolley cut is 41 of 60 whether it is set at
zero or a hundred -- but it keeps a four-match record off the table.
"""
import json, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonl import read as read_jsonl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "docs", "rank-2027_younger.html")
ROSTER = os.path.join(HERE, "roster_2027_younger_fit.json")
COHORT = "cohort2027.json"
LABEL = "2027 and younger"
TOP = 60
MIN_OBS = 20
STRONG = 7.5          # "strong opponent" line, on the TruVolley scale both ratings share


def load():
    rt = json.load(open(os.path.join(DATA, "rating.json")))["ratings"]
    pop = {int(k): v for k, v in json.load(open(os.path.join(DATA, COHORT))).items()}
    return rt, pop


def schedule(ids, rt):
    """Record and opponent strength for a set of players, from the merged corpus."""
    acc = {p: {"w": 0, "l": 0, "opp": 0.0, "n": 0, "strong": 0, "sw": 0} for p in ids}
    for m in read_jsonl(os.path.join(DATA, "all_matches.jsonl")):
        for side, other, won in ((m["a"], m["b"], m["aWon"]),
                                 (m["b"], m["a"], not m["aWon"])):
            hit = [p for p in side if p in acc]
            if not hit:
                continue
            rs = [rt[str(o)]["r"] for o in other if str(o) in rt]
            if not rs:
                continue
            s = sum(rs) / len(rs)
            for p in hit:
                a = acc[p]
                a["w" if won else "l"] += 1
                a["opp"] += s
                a["n"] += 1
                if s >= STRONG:
                    a["strong"] += 1
                    a["sw"] += bool(won)
    return acc


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def scatter(pairs, w=940, h=340):
    """Fitted rating against TruVolley for the cohort's rated players."""
    L, R, T, B = 56, 20, 22, 46
    x0, x1, y0, y1 = 5.5, 10.5, 5.5, 10.5
    px = lambda v: L + (v - x0) / (x1 - x0) * (w - L - R)
    py = lambda v: h - B - (v - y0) / (y1 - y0) * (h - T - B)
    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" aria-label="Fitted rating '
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
                 f'<title>{esc(nm)}: TruVolley {tvv:.2f}, fitted {mine:.2f}</title></circle>')
    o.append(f'<text x="{(L + w - R) / 2:.0f}" y="{h - 8}" class="axlab" '
             f'text-anchor="middle">TRUVOLLEY</text>')
    o.append(f'<text x="14" y="{(T + h - B) / 2:.0f}" class="axlab" '
             f'transform="rotate(-90 14 {(T + h - B) / 2:.0f})" text-anchor="middle">FITTED</text>')
    o.append("</svg>")
    return "\n".join(o)


CSS = """
:root {
  --ground:#EFF1EE; --surface:#FAFBFA; --ink:#111B19; --body:#2C3A37;
  --muted:#5F6E6A; --faint:#8B9995; --line:#D5DCD9; --hair:#E4E9E7;
  --accent:#0B6E68; --up:#00806F; --down:#9A6B12; --chip:#E4EDEB;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
    --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
    --accent:#57C3B6; --up:#2AA08C; --down:#DCA84A; --chip:#1B2A27;
  }
}
:root[data-theme="dark"] {
  --ground:#0B1211; --surface:#121B19; --ink:#E9EFEC; --body:#C6D2CE;
  --muted:#93A29E; --faint:#6E7D79; --line:#243330; --hair:#1C2827;
  --accent:#57C3B6; --up:#2AA08C; --down:#DCA84A; --chip:#1B2A27;
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
.lede { color:var(--muted); margin:0 0 18px; max-width:72ch; font-size:14.5px; }
section { padding:42px 0 0; }
p { max-width:72ch; }
.facts { display:flex; flex-wrap:wrap; margin:26px 0 0; border:1px solid var(--line);
  border-radius:3px; background:var(--surface); overflow:hidden; }
.fact { flex:1 1 140px; padding:14px 18px; border-right:1px solid var(--hair); }
.fact:last-child { border-right:0; }
.fact b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.fact span { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }
.tbox { border:1px solid var(--line); border-radius:3px; overflow:auto; max-height:none; }
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
.tick { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:11px;
  fill:var(--muted); }
.axlab { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:10px;
  letter-spacing:.1em; fill:var(--faint); }
.two { display:grid; grid-template-columns:1fr 1fr; gap:22px; }
@media (max-width:820px) { .two { grid-template-columns:1fr; } }
ul { max-width:72ch; padding-left:20px; }
li { margin:0 0 10px; }
footer { margin-top:50px; padding-top:18px; border-top:1px solid var(--line);
  font-size:12px; color:var(--faint); max-width:82ch; }
"""


def build():
    rt, pop = load()
    rated = [(p, v) for p, v in pop.items()
             if str(p) in rt and rt[str(p)]["n"] >= MIN_OBS]
    mine = sorted(((rt[str(p)]["r"], p, v) for p, v in rated), reverse=True)
    myrank = {p: i for i, (_, p, _) in enumerate(mine, 1)}
    tvsort = sorted(((v.get("tv") or 0, p, v) for p, v in pop.items() if v.get("tv")),
                    reverse=True)
    tvrank = {p: i for i, (_, p, _) in enumerate(tvsort, 1)}
    top = mine[:TOP]
    ids = {p for _, p, _ in top}
    old = {r[1] for r in json.load(open(os.path.join(HERE,
                                  "roster_2027_younger.json")))["roster"]}
    acc = schedule(ids, rt)

    rows, classes = [], defaultdict(int)
    for i, (r, p, v) in enumerate(top, 1):
        a = acc[p]
        tvv = v.get("tv")
        tvk = tvrank.get(p)
        mv = (tvk - i) if tvk else None
        classes[v.get("grad")] += 1
        mvs = (f'<span class="up">+{mv}</span>' if mv and mv > 0 else
               f'<span class="down">{mv}</span>' if mv and mv < 0 else
               '<span class="n">0</span>' if mv == 0 else "&#8212;")
        rows.append(
            f'<tr><td class="n">{i}</td>'
            f'<td class="nm">{esc(v["name"])}'
            + ("" if p in old else '<span class="new">new</span>') + "</td>"
            f'<td class="r">{r:.3f}</td>'
            f'<td class="n">{tvv:.3f}</td><td class="n">{tvk or "&#8212;"}</td>'
            f'<td class="n">{mvs}</td>'
            f'<td class="n">{v.get("grad") or "&#8212;"}</td>'
            f'<td class="n">{esc(v["height"]) if v.get("height") else "&#8212;"}</td>'
            f'<td>{esc(v.get("state") or "&#8212;")}</td>'
            f'<td class="n">{a["w"]}&#8211;{a["l"]}</td>'
            f'<td class="n">{(a["opp"] / a["n"]):.2f}</td>'
            f'<td class="n">{a["strong"]}</td>'
            f'<td class="n">{a["sw"]}&#8211;{a["strong"] - a["sw"]}</td>'
            f'<td class="n">{rt[str(p)]["n"]}</td></tr>')

    gained = [(myrank[p], v["name"], rt[str(p)]["r"], v.get("tv"), tvrank.get(p))
              for _, p, v in top if p not in old]
    lost = [(tvrank[p], v["name"], v.get("tv"), rt.get(str(p), {}).get("r"),
             myrank.get(p)) for _, p, v in tvsort[:TOP] if p not in ids]

    pairs = [(v.get("tv"), rt[str(p)]["r"], v["name"], p in ids)
             for p, v in rated if v.get("tv")]
    json.dump({"label": f"{LABEL} &#8212; top {TOP} by fitted rating",
               "roster": [[v["name"], p, v.get("state") or "?"] for _, p, v in top],
               "meta": {str(p): {k: v.get(k) for k in
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
    vol = max(top, key=lambda t: acc[t[1]]["w"])
    va = acc[vol[1]]
    hi = max(a["strong"] for a in acc.values())
    hardest = [v["name"] for _, p, v in top if acc[p]["strong"] == hi][0]

    return f"""<title>The 2027 Field, Re-Ranked</title>
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="eyebrow">{LABEL} &#183; top {TOP} &#183; fitted rating</p>
  <h1>The same cohort, cut on <em>who they beat</em></h1>
  <p class="standfirst">The 18U-eligible field ranked by the rating fitted in this
  repository rather than by TruVolley. It is the same closed cohort of
  {len(pop):,} girls, but {len(gained)} of the {TOP} names change &#8212; because this
  rating prices the opponent, and TruVolley prices the result.</p>
</header>

<div class="facts">
  <div class="fact"><b>{len(gained)}</b><span>Names that change</span></div>
  <div class="fact"><b>{top[-1][0]:.3f}</b><span>Cut at #{TOP}</span></div>
  <div class="fact"><b>{len(rated):,}</b><span>Cohort players ranked</span></div>
  <div class="fact"><b>{MIN_OBS}</b><span>Minimum observations</span></div>
  <div class="fact"><b>{younger}</b><span>Younger than 2027</span></div>
</div>

<section>
  <h2>Top {TOP} by fitted rating</h2>
  <p class="lede">TV rank is the player's place in the same cohort on TruVolley; move is
  how far she travels between the two. The last four columns are the explanation: her
  record, the mean rating of the opposition she faced, how many of those matches were
  against {STRONG}-and-above, and her record in them. By graduating year this cut is
  {spread}.</p>
  <div class="tbox"><table>
    <tr><th class="n">#</th><th>Player</th><th class="n">Fitted</th><th class="n">TruVolley</th>
    <th class="n">TV rank</th><th class="n">Move</th><th class="n">Class</th>
    <th class="n">Ht</th><th>St</th><th class="n">W&#8211;L</th><th class="n">Mean opp</th>
    <th class="n">vs {STRONG}+</th><th class="n">Record</th><th class="n">Obs</th></tr>
    {"".join(rows)}
  </table></div>
</section>

<section>
  <h2>Where the two ratings disagree</h2>
  <p class="lede">Each dot is a cohort player with both numbers; the {TOP} in this cut are
  filled. The dashed line is agreement. Above it the fitted rating is the more generous,
  below it TruVolley is.</p>
  <div class="figbox">{scatter(pairs)}</div>
  <div class="two" style="margin-top:26px">
    <div>
      <h2 style="font-size:18px">In on the fitted rating</h2>
      <div class="tbox"><table>
        <tr><th class="n">#</th><th>Player</th><th class="n">Fitted</th>
        <th class="n">TV</th><th class="n">TV rank</th></tr>
        {"".join(f'<tr><td class="n">{r}</td><td class="nm">{esc(n)}</td>'
                 f'<td class="r">{m:.3f}</td><td class="n">{t:.3f}</td>'
                 f'<td class="n">{k}</td></tr>' for r, n, m, t, k in gained)}
      </table></div>
    </div>
    <div>
      <h2 style="font-size:18px">Out on the fitted rating</h2>
      <div class="tbox"><table>
        <tr><th class="n">TV#</th><th>Player</th><th class="n">TV</th>
        <th class="n">Fitted</th><th class="n">Rank</th></tr>
        {"".join(f'<tr><td class="n">{k}</td><td class="nm">{esc(n)}</td>'
                 f'<td class="n">{t:.3f}</td>'
                 f'<td class="r">{(f"{m:.3f}" if m else "&#8212;")}</td>'
                 f'<td class="n">{r or "unranked"}</td></tr>' for k, n, t, m, r in lost)}
      </table></div>
    </div>
  </div>
</section>

<section>
  <h2>What the difference is measuring</h2>
  <ul>
    <li><b>TruVolley moves when the team wins.</b> A season alongside a strong partner
    lifts it whether or not the player was the reason. The fitted rating solves for
    individual strength with partner quality as a term in the model, so the partner is
    subtracted rather than absorbed.</li>
    <li><b>Opponent strength is priced explicitly.</b> Beating the same local field every
    weekend earns little; losing narrowly to much stronger teams costs little. The
    <em>mean opp</em> and <em>vs {STRONG}+</em> columns are usually enough to see which
    side of that a player sits on &#8212; {esc(hardest)} played the hardest schedule in
    this {TOP}, at {hi} matches against {STRONG}-and-above.</li>
    <li><b>Volume against moderate opposition carries weight, and the columns say so.</b>
    {esc(vol[2]["name"])} ranks {[i for i, t in enumerate(top, 1) if t[1] == vol[1]][0]}
    on a record of {va["w"]}&#8211;{va["l"]} &#8212; {100 * va["w"] // (va["w"] + va["l"])}%
    across {va["w"] + va["l"]} matches &#8212; but her mean opponent is
    {(va["opp"] / va["n"]):.2f} and she is {va["sw"]}&#8211;{va["strong"] - va["sw"]}
    against {STRONG}-and-above. Beating a moderate field that often does imply a real
    edge, and the model prices it as one; whether it would survive a harder schedule is
    exactly what those two columns leave the reader to judge.</li>
    <li><b>Neither is the truth.</b> On held-out matches the two are close: TruVolley
    scores 0.357 log-loss to this fit's 0.397 with accuracy tied at about 0.84, and
    TruVolley is quoted as of today so it has already absorbed the matches being
    predicted. The case for this ranking is that it is transparent and tunable, not that
    it is sharper.</li>
    <li><b>It is one setting of a tunable model.</b> `scripts/rating.json` fixes a
    three-year window, a 365-day half-life, ridge 0.25 and a team model that is the mean
    of its two players &#8212; each chosen on held-out prediction. A shorter half-life
    favours whoever is improving fastest and moves ranks by ten places or more.</li>
    <li><b>Ratings are on the TruVolley scale by a quantile map</b>, so the two columns
    are directly comparable. The map is monotone: it changes no one's order.</li>
  </ul>
</section>

<footer>
  {LABEL}, the closed cohort of {len(pop):,} girls from a partner-graph crawl, ranked on a
  Bradley-Terry rating fitted to 679,241 matches from Volleyball Life, CBVA and college
  beach. Players with fewer than {MIN_OBS} observations are not ranked. Records and
  opponent strength are computed over the same three-year window as the fit.
</footer>
</div>
"""


if __name__ == "__main__":
    open(OUT, "w").write(build())
    print("wrote", OUT, "and", ROSTER)
