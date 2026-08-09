"""Render one group's competition matrix to a self-contained HTML page.

  python3 render_group.py 17U      ->  bntdp-17u.html
"""
import json, sys, html
from scatter import scatter

TEXT = {
    "18U": {
        "eyebrow": "USA Volleyball &#183; Beach NTDP Summer Training Series 2026 &#183; Girls U18",
        "title": "The 18U girls, and <em>who they actually played</em>",
        "lede": "All {N} athletes named to the Girls U18 roster for the Beach NTDP Summer "
                "Training Series at Chula Vista, against their Volleyball Life record",
        "note": "",
    },
    "17U": {
        "eyebrow": "USA Volleyball &#183; Beach NTDP Summer Training Series 2026 &#183; Girls U17",
        "title": "The 17U girls, and <em>who they actually played</em>",
        "lede": "All {N} athletes named to the Girls U17 roster for the Beach NTDP Summer "
                "Training Series at Chula Vista, against their Volleyball Life record",
        "note": "",
    },
    "2028": {
        "eyebrow": "Girls beach volleyball &#183; Class of 2028 &#183; National top 30",
        "title": "The class of 2028, and <em>where the top 30 keep meeting</em>",
        "lede": "The {N} highest-rated girls in the graduating class of 2028, against their "
                "Volleyball Life record",
        "note": "<li><b>How these 60 were chosen.</b> Volleyball Life publishes no class "
                "ranking, so the field was built by crawling the partner graph outward from "
                "known 2028 athletes and keeping every profile that reports a 2028 graduation "
                "year. The crawl was then run to closure &#8212; repeatedly expanding the "
                "partners of every player already found until a full round turned up nobody "
                "new above a 7.0 rating floor. That took the population to <b>1,574 girls in "
                "the class, 1,373 of them rated</b>; the 60 highest TruVolley scores are the "
                "roster here. The final round added 563 players and not one of them cleared "
                "the floor, so the cut is stable &#8212; though it is tight: #61 is Nikolina "
                "Mimic at 7.331, fifteen thousandths behind #60. This is a ranking by rating, "
                "not a scouting opinion, and TruVolley rewards win rate, so a light schedule "
                "in small fields can flatter a player.</li>",
    },
}


def cls(f, y):
    if not f or not y:
        return "na"
    if f == 1:
        return "win"
    if f <= 3:
        return "pod"
    p = f / y
    return "t1" if p <= .10 else "t2" if p <= .25 else "t3" if p <= .50 else "t4" if p <= .75 else "t5"


def ord_(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def nicecity(c):
    if not c or c.startswith("None"):
        return ""
    city, _, st = c.rpartition(",")
    return (" ".join(w.capitalize() for w in city.split()) + ", " + st.strip()) if city else c


def tidy(n):
    n = " ".join(n.split()).lstrip(", ")
    return n[:1].upper() + n[1:] if n else n


def esc(s):
    return html.escape(str(s), quote=True)


def build(group):
    D = json.load(open(f"{group}_site.json"))
    players, comps, pairs = D["players"], D["comps"], D["pairs"]
    N = len(players)
    T = TEXT[group]

    lo, hi = 6.7, 9.7
    showht = any(p.get("height") for p in players)

    def htcell(p):
        return f'\n        <td class="num nw">{esc(p.get("height") or "—")}</td>' if showht else ""

    roster = []
    for p in players:
        pct = max(0, min(100, ((p["tv"] or lo) - lo) / (hi - lo) * 100))
        roster.append(f"""      <tr>
        <th scope="row"><span class="pn">{esc(p['name'])}</span><span class="pc">{esc(nicecity(p['city']))}</span></th>
        <td>{esc(p['region'])}</td>
        <td class="clubc">{esc(p['club'] or '—')}</td>{htcell(p)}
        <td class="num">
          <div class="rate"><span class="rv">{p['tv']:.3f}</span>
            <span class="bar"><span class="fill" style="width:{pct:.1f}%"></span></span>
          </div>
        </td>
        <td class="num dim">{p['peak']:.3f}</td>
        <td class="num nw">{p['w']}&#8202;&#8211;&#8202;{p['l']}</td>
        <td class="num">{p['comps']}</td>
      </tr>""")

    head = []
    for c in comps:
        fld = f'{c["field"]} teams' if c["field"] else "field n/a"
        head.append(
            f'      <th scope="col" class="evh" title="{esc(c["event"])} &#183; {esc(c["division"])} &#183; {esc(fld)} &#183; {esc(c["date"])}">'
            f'<span class="evn">{esc(c["short"])}</span>'
            f'<span class="evdiv">{esc(c["division"])}</span>'
            f'<span class="field">{esc(fld)}</span>'
            f'<span class="evd">{c["date"][5:7]}/{c["date"][8:10]} &#183; {esc(c["sanction"])}</span>'
            f'<span class="evc">{c["n"]}&#8201;of&#8201;{N}</span></th>')

    rows = []
    for p in players:
        tds = []
        pod = sum(1 for x in p["cells"].values() if x["f"] <= 3)
        for c in comps:
            cell = p["cells"].get(c["key"])
            if not cell:
                tds.append('        <td class="cell empty"><span>&#183;</span></td>')
                continue
            f = cell["f"]
            tip = f'{p["name"]} — {f}{ord_(f)} of {c["field"] or "?"} · {c["short"]} · {c["division"]}'
            if cell["partners"]:
                tip += " · with " + ", ".join(cell["partners"])
            tds.append(f'        <td class="cell {cls(f, c["field"])}" title="{esc(tip)}">'
                       f'<span class="fin">{f}</span></td>')
        rows.append(f"""      <tr>
        <th scope="row" class="rowh"><span class="pn">{esc(p['name'])}</span>
          <span class="rmeta"><span class="tvchip">{p['tv']:.2f}</span>
          <span class="rsum">{len(p['cells'])} shared &#183; {pod} podium{'s' if pod != 1 else ''}</span></span></th>
{chr(10).join(tds)}
      </tr>""")

    prs = []
    for c in pairs:
        a, b = c["players"]
        prs.append(f"""      <tr>
        <td class="num dim nw">{esc(c['date'])}</td>
        <td><span class="evn2">{esc(tidy(c['event']))}</span><span class="dv">{esc(c['division'])}</span></td>
        <td class="num">{c['field'] if c['field'] else '&#8211;'}</td>
        <td>{esc(a['name'])} <b class="pos">{a['f']}{ord_(a['f'])}</b></td>
        <td>{esc(b['name'])} <b class="pos">{b['f']}{ord_(b['f'])}</b></td>
      </tr>""")

    HILITE = {"2028": ("Lucy Matuszak", "Haisley Flanagan", "Lia Ray",
                       "Reese Hislop", "Karsyn Smith", "Ella Buchanan"),
              "17U": ("Lucy Matuszak", "Haisley Flanagan", "Olivia LeDoyen",
                      "Charlotte Jansen", "Elyse Smelcer"),
              "18U": ("Lauren Leach", "Olivia Herron", "Janie McCanna",
                      "Sarah Albers", "Jordyn Wilson")}[group]
    fig, slope, rr = scatter(players, HILITE)
    per10 = slope * 10
    stat = f"r&nbsp;=&nbsp;{rr:+.2f}, r&#178;&nbsp;=&nbsp;{rr * rr:.2f}"
    if abs(rr) < 0.15:
        trend = f"The fit is essentially flat ({stat}): how much an athlete plays has all but no bearing on her rating."
    elif abs(rr) < 0.45:
        trend = (f"The fit slopes {abs(per10):.2f} of a rating point "
                 f"{'down' if slope < 0 else 'up'} per additional ten competitions, but the "
                 f"relationship is weak ({stat}) and explains little of the spread.")
    else:
        trend = (f"The fit slopes {abs(per10):.2f} of a rating point "
                 f"{'down' if slope < 0 else 'up'} per additional ten competitions "
                 f"({stat}), a meaningful share of the spread.")
    figcap = (f"Each dot is one athlete; {len(players)} plotted. " + trend
              + " Named points are the extremes and the athletes discussed in the notes; "
                "the roster table above is the full table view.")

    regionhdr = "State" if group == "2028" else "USAV region"
    others = {"18U": "17U group and the class of 2028",
              "17U": "18U group and the class of 2028",
              "2028": "NTDP 18U and 17U groups"}[group]
    return f"""<title>BNTDP {group} Girls &#183; Record by Competition</title>
<style>
:root {{
  --ground:#EFF1EE; --surface:#FAFBFA; --raise:#FFFFFF;
  --ink:#111B19; --body:#2C3A37; --muted:#5F6E6A; --faint:#8B9995;
  --line:#D5DCD9; --hair:#E4E9E7;
  --accent:#0B6E68; --accent-soft:#D9E7E5;
  --gold:#9A6B12; --gold-soft:#F3E4C4;
  --wash:#EAEDEB;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#0B1211; --surface:#121B19; --raise:#182322;
    --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
    --line:#243330; --hair:#1C2827;
    --accent:#57C3B6; --accent-soft:#123733;
    --gold:#DCA84A; --gold-soft:#382B12;
    --wash:#161F1E;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#0B1211; --surface:#121B19; --raise:#182322;
  --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
  --line:#243330; --hair:#1C2827;
  --accent:#57C3B6; --accent-soft:#123733;
  --gold:#DCA84A; --gold-soft:#382B12;
  --wash:#161F1E;
}}

* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  font-size:15px; line-height:1.6; -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:1120px; margin:0 auto; padding:0 28px; }}

header {{ padding:64px 0 34px; border-bottom:1px solid var(--line); }}
.eyebrow {{ font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin:0 0 18px; }}
h1 {{ font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(34px,5.2vw,54px); line-height:1.05; letter-spacing:-.02em;
  color:var(--ink); margin:0 0 16px; font-weight:600; text-wrap:balance; }}
h1 em {{ font-style:italic; color:var(--accent); }}
.standfirst {{ font-size:17px; color:var(--muted); max-width:64ch; margin:0; }}
.facts {{ display:flex; flex-wrap:wrap; margin:32px 0 0;
  border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:hidden; }}
.fact {{ flex:1 1 130px; padding:14px 18px; border-right:1px solid var(--hair); }}
.fact:last-child {{ border-right:0; }}
.fact b {{ display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; line-height:1.2; }}
.fact span {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }}

section {{ padding:48px 0 0; }}
h2 {{ font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:25px; color:var(--ink); font-weight:600; letter-spacing:-.01em; margin:0 0 6px; }}
.lede {{ color:var(--muted); margin:0 0 22px; max-width:70ch; font-size:14.5px; }}

.panel {{ border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; }}
.roster th, .roster td, .pairs th, .pairs td {{
  padding:11px 14px; text-align:left; border-bottom:1px solid var(--hair); }}
.roster thead th, .pairs thead th {{
  font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint);
  font-weight:650; background:var(--wash); border-bottom:1px solid var(--line); white-space:nowrap; }}
.roster tbody tr:last-child th, .roster tbody tr:last-child td,
.pairs tbody tr:last-child td {{ border-bottom:0; }}
.roster tbody tr:hover, .pairs tbody tr:hover {{ background:var(--raise); }}
.roster th[scope="row"] {{ font-weight:500; }}
.pn {{ display:block; color:var(--ink); font-weight:600; white-space:nowrap; }}
.pc {{ display:block; font-size:11.5px; color:var(--faint); }}
.clubc {{ font-size:13px; color:var(--muted); }}
.num {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13.5px; }}
.dim {{ color:var(--faint); }}
.nw {{ white-space:nowrap; }}
.rate {{ display:flex; align-items:center; gap:9px; }}
.rv {{ color:var(--ink); font-weight:600; font-size:14.5px; }}
.bar {{ display:block; width:74px; height:5px; background:var(--wash);
  border:1px solid var(--hair); border-radius:2px; overflow:hidden; }}
.fill {{ display:block; height:100%; background:var(--accent); }}

.matrix-wrap {{ border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow-x:auto; }}
.matrix {{ border-collapse:separate; border-spacing:0; }}
.matrix th, .matrix td {{ border-bottom:1px solid var(--hair); border-right:1px solid var(--hair); }}
.matrix .evh {{ width:112px; min-width:112px; vertical-align:bottom; padding:12px 10px 10px;
  background:var(--wash); border-bottom:1px solid var(--line);
  position:sticky; top:0; z-index:2; text-align:left; }}
.evn {{ display:block; font-size:11.5px; line-height:1.3; color:var(--ink); font-weight:600; }}
.evdiv {{ display:block; font-size:10.5px; line-height:1.3; color:var(--muted); margin-top:2px; }}
.field {{ display:inline-block; margin-top:6px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; font-weight:650;
  color:var(--accent); background:var(--accent-soft); border-radius:2px; padding:2px 6px;
  font-variant-numeric:tabular-nums; white-space:nowrap; }}
.evd {{ display:block; margin-top:6px; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:10px; color:var(--faint); font-variant-numeric:tabular-nums; }}
.evc {{ display:block; margin-top:3px; font-size:9.5px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--muted); font-weight:650; }}
.matrix .rowh {{ position:sticky; left:0; z-index:3; background:var(--surface);
  width:196px; min-width:196px; padding:10px 14px 10px 16px; text-align:left;
  border-right:1px solid var(--line); font-weight:500; }}
.matrix thead .corner {{ position:sticky; left:0; top:0; z-index:4; background:var(--wash);
  border-right:1px solid var(--line); border-bottom:1px solid var(--line);
  width:196px; min-width:196px; padding:12px 16px; text-align:left; vertical-align:bottom;
  font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); font-weight:650; }}
.rmeta {{ display:flex; align-items:center; gap:8px; margin-top:4px; }}
.tvchip {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12px; font-weight:650; color:var(--accent); background:var(--accent-soft);
  border-radius:2px; padding:1px 5px; font-variant-numeric:tabular-nums; }}
.rsum {{ font-size:10.5px; color:var(--faint); white-space:nowrap; }}
.matrix tbody tr:hover .cell {{ box-shadow:inset 0 0 0 99px rgba(127,127,127,.055); }}
.cell {{ width:112px; min-width:112px; padding:11px 8px; text-align:center;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-variant-numeric:tabular-nums; }}
.fin {{ font-size:17px; font-weight:700; letter-spacing:-.01em; }}
.cell.win {{ background:var(--gold-soft); color:var(--gold); box-shadow:inset 3px 0 0 var(--gold); }}
.cell.pod {{ background:var(--gold-soft); color:var(--gold); }}
.cell.t1 {{ background:var(--accent-soft); color:var(--accent); }}
.cell.t2 {{ background:color-mix(in srgb,var(--accent-soft) 58%,transparent); color:var(--accent); }}
.cell.t3 {{ background:color-mix(in srgb,var(--accent-soft) 28%,transparent); color:var(--body); }}
.cell.t4 {{ color:var(--muted); }}
.cell.t5, .cell.na {{ color:var(--faint); }}
.cell.empty {{ color:var(--hair);
  background:repeating-linear-gradient(-45deg,transparent,transparent 5px,var(--hair) 5px,var(--hair) 6px); }}
.cell.empty span {{ opacity:.55; font-size:13px; }}

.legend {{ display:flex; flex-wrap:wrap; gap:8px 20px; align-items:center; margin:16px 0 0;
  font-size:12px; color:var(--muted); }}
.key {{ display:inline-flex; align-items:center; gap:7px; }}
.sw {{ width:22px; height:14px; border:1px solid var(--line); border-radius:2px; display:inline-block; }}
.sw.win {{ background:var(--gold-soft); box-shadow:inset 3px 0 0 var(--gold); }}
.sw.pod {{ background:var(--gold-soft); }}
.sw.t1 {{ background:var(--accent-soft); }}
.sw.t2 {{ background:color-mix(in srgb,var(--accent-soft) 58%,transparent); }}
.sw.t3 {{ background:color-mix(in srgb,var(--accent-soft) 28%,transparent); }}
.sw.t5 {{ background:var(--surface); }}
.evn2 {{ display:block; color:var(--ink); font-weight:600; font-size:13.5px; }}
.dv {{ display:block; font-size:11.5px; color:var(--faint); }}
.pos {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  color:var(--ink); font-weight:700; font-variant-numeric:tabular-nums; }}
.pairs td {{ font-size:13.5px; }}
.pairs td:nth-child(2) {{ max-width:330px; }}


.figwrap {{ border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:18px 20px 10px; overflow-x:auto; }}
.fig {{ display:block; min-width:620px; --mark:#00A385; --fitink:var(--muted); }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) .fig {{ --mark:#00AB87; }}
}}
:root[data-theme="dark"] .fig {{ --mark:#00AB87; }}
.fig .grid {{ stroke:var(--hair); stroke-width:1; }}
.fig .axis {{ stroke:var(--line); stroke-width:1; }}
.fig .tick {{ fill:var(--faint); font-size:11px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-variant-numeric:tabular-nums; }}
.fig .ty {{ text-anchor:end; }}
.fig .tx {{ text-anchor:middle; }}
.fig .axlab {{ fill:var(--muted); font-size:11.5px; text-anchor:middle;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; letter-spacing:.02em; }}
.fig .fit {{ stroke:var(--fitink); stroke-width:2; stroke-dasharray:7 5; opacity:.75; }}
.fig .fitlab {{ fill:var(--muted); font-size:11px; text-anchor:end;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
.fig .dot {{ fill:var(--mark); stroke:var(--surface); stroke-width:2; }}
.fig .dot.hi {{ fill:var(--surface); stroke:var(--mark); stroke-width:3; }}
.fig .ptlab {{ fill:var(--ink); font-size:11.5px; font-weight:600;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  paint-order:stroke; stroke:var(--surface); stroke-width:3px; }}
.figcap {{ color:var(--faint); font-size:12px; margin:10px 0 0; max-width:76ch; }}

.notes {{ margin:0 0 60px; }}
.notes ul {{ padding-left:19px; margin:10px 0 0; }}
.notes li {{ margin:7px 0; font-size:13.5px; color:var(--muted); max-width:76ch; }}
.notes b {{ color:var(--body); font-weight:600; }}
footer {{ border-top:1px solid var(--line); padding:22px 0 70px; font-size:12px; color:var(--faint); }}
a {{ color:var(--accent); }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; animation:none !important; }} }}
@media (max-width:720px) {{
  .wrap {{ padding:0 18px; }} header {{ padding-top:40px; }}
  .matrix .rowh, .matrix thead .corner {{ width:150px; min-width:150px; }}
}}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">{T['eyebrow']}</p>
  <h1>{T['title']}</h1>
  <p class="standfirst">{T['lede'].format(N=N)} for the twelve months
  ending 9 August 2026. <b>Doubles only</b> &#8212; club and five-a-side results are excluded,
  because a squad finish says little about the individual. Each age division counts as its own
  competition, so a 16U bracket and the 18U bracket running beside it are different columns. Every
  cell is a finishing position; the size of that field is in the column head.</p>
  <div class="facts">
    <div class="fact"><b>{N}</b><span>Athletes</span></div>
    <div class="fact"><b>{D['totalEvents']}</b><span>Events attended</span></div>
    <div class="fact"><b>{D['totalComps']}</b><span>Pairs competitions</span></div>
    <div class="fact"><b>{len(comps)}</b><span>Shared by {D.get('thresh', 3)}+</span></div>
    <div class="fact"><b>{D['droppedTeam']}</b><span>Club results dropped</span></div>
  </div>
</header>

<section>
  <h2>The roster</h2>
  <p class="lede">TruVolley is Volleyball Life's skill rating &#8212; one number derived from
  match-by-match results against rated opposition. It is computed by Volleyball Life across all
  formats, so unlike the matrix below it still reflects club play. Sorted strongest first.</p>
  <div class="panel">
    <table class="roster">
      <thead><tr>
        <th scope="col">Athlete</th><th scope="col">{regionhdr}</th><th scope="col">Club</th>{'<th scope="col">Height</th>' if showht else ''}
        <th scope="col">TruVolley</th><th scope="col">Peak</th>
        <th scope="col">W&#8211;L</th><th scope="col">Pairs comps</th>
      </tr></thead>
      <tbody>
{chr(10).join(roster)}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>Rating against workload</h2>
  <p class="lede">Whether the athletes with the highest ratings are the ones playing the most.
  TruVolley on the vertical, doubles competitions in the window on the horizontal.</p>
  <div class="figwrap">
{fig}
  </div>
  <p class="figcap">{figcap}</p>
</section>

<section>
  <h2>Players against shared competitions</h2>
  <p class="lede">The {len(comps)} competitions entered by at least {D.get('thresh', 3)} of the {N}, biggest
  turnout first. A cell is that athlete's finishing position in the field named above it;
  hatched means she did not enter. Hover any cell for her partner.</p>
</section>
</div>

<div class="wrap">
  <div class="matrix-wrap">
    <table class="matrix">
      <thead><tr>
        <th class="corner">Athlete &#183; TruVolley</th>
{chr(10).join(head)}
      </tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>
  <div class="legend">
    <span class="key"><span class="sw win"></span> Won it</span>
    <span class="key"><span class="sw pod"></span> Podium (2nd&#8211;3rd)</span>
    <span class="key"><span class="sw t1"></span> Top 10&#8202;% of field</span>
    <span class="key"><span class="sw t2"></span> Top 25&#8202;%</span>
    <span class="key"><span class="sw t3"></span> Top half</span>
    <span class="key"><span class="sw t5"></span> Bottom half</span>
  </div>
</div>

<div class="wrap">
<section>
  <h2>Where only two of them met</h2>
  <p class="lede">A further {len(pairs)} competitions drew exactly two of the roster &#8212; too thin
  for the matrix, but still head-to-heads. Newest first.</p>
  <div class="panel">
    <table class="pairs">
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Competition</th><th scope="col">Field</th>
        <th scope="col" colspan="2">Finishes</th>
      </tr></thead>
      <tbody>
{chr(10).join(prs)}
      </tbody>
    </table>
  </div>
</section>

<section class="notes">
  <h2>How to read it</h2>
  <ul>
    <li><b>Each division is its own competition.</b> At the AVP Juniors National Championships the
    18U, 17U, 16U and 15U brackets ran as separate fields; they appear as separate columns, and a
    5th in one says nothing about a 5th in another.</li>
    <li><b>Doubles only &#8212; club formats are excluded.</b> The BVCA Orange County dates,
    Club&#8202;v&#8202;Club, the AAU club championships and every 3v3 or 5v5 division are team
    events where a placing reflects a squad of five to twelve, not the athlete. {D['droppedTeam']}
    such results were dropped. The test is roster size rather than the division name, which is
    unreliable: &#8220;Open (5v5)&#8221;, &#8220;OPEN&#8221;, &#8220;Club Division&#8221; and
    &#8220;Girls Open (5 Pairs)&#8221; are all team formats. Every entry kept has exactly one
    partner.</li>
    <li><b>Ties are shared.</b> Beach draws award equal finishes to every team knocked out in the
    same round, which is why blocks of 5th, 9th and 17th recur down a column.</li>
    <li><b>Field size is the number of teams registered in that division</b>, as recorded by
    Volleyball Life &#8212; not the number that ultimately played, so a withdrawal leaves the
    denominator unchanged.</li>
    <li><b>Sanctioning bodies</b> are tagged in each column head: AVPA (AVP and AVP Juniors),
    USAV, AAU, BVCA, CBVA and p1440.</li>
    {T['note']}
  </ul>
</section>
<footer>
  {esc(D['label'])}. Results, field sizes and TruVolley ratings from Volleyball Life,
  retrieved 9 August 2026. Companion reports cover the {others}.
</footer>
</div>
"""


if __name__ == "__main__":
    for grp in (sys.argv[1:] or ["18U", "17U"]):
        out = f"bntdp-{grp.lower()}.html"
        open(out, "w").write(build(grp))
        print("wrote", out)
