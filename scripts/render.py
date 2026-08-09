import json, html
from collections import defaultdict

D = json.load(open("site_data.json"))
clean = json.load(open("clean.json"))
players, events = D["players"], D["events"]

total_events = len({str(e["tid"]) for v in clean["entries"].values() for e in v})
total_entries = sum(len(v) for v in clean["entries"].values())


def cls(f, y):
    if not f or not y:
        return "na"
    if f == 1:
        return "win"
    if f <= 3:
        return "pod"
    p = f / y
    if p <= 0.10:
        return "t1"
    if p <= 0.25:
        return "t2"
    if p <= 0.50:
        return "t3"
    if p <= 0.75:
        return "t4"
    return "t5"


def nicecity(c):
    if not c:
        return ""
    city, _, st = c.rpartition(",")
    return (" ".join(w.capitalize() for w in city.split()) + ", " + st.strip()) if city else c


def esc(s):
    return html.escape(str(s), quote=True)


# ---------- roster table ----------
lo, hi = 7.5, 9.7
roster = []
for p in players:
    pct = max(0, min(100, (p["tv"] - lo) / (hi - lo) * 100))
    roster.append(f"""      <tr>
        <th scope="row"><span class="pn">{esc(p['name'])}</span><span class="pc">{esc(nicecity(p['city']))}</span></th>
        <td>{esc(p['region'])}</td>
        <td class="clubc">{esc(p['club'])}</td>
        <td class="num">
          <div class="rate"><span class="rv">{p['tv']:.3f}</span>
            <span class="bar"><span class="fill" style="width:{pct:.1f}%"></span></span>
          </div>
        </td>
        <td class="num dim">{p['peak']:.3f}</td>
        <td class="num nw">{p['w']}&#8202;&#8211;&#8202;{p['l']}</td>
        <td class="num">{p['played']}</td>
      </tr>""")

# ---------- matrix ----------
head = []
for e in events:
    m, dd = e["date"][5:7], e["date"][8:10]
    head.append(
        f'      <th scope="col" class="evh" title="{esc(e["name"])} &#183; {esc(e["date"])}">'
        f'<span class="evn">{esc(e["short"])}</span>'
        f'<span class="evd">{m}/{dd}</span>'
        f'<span class="evs">{esc(e["sanction"])}</span>'
        f'<span class="evc">{e["n"]}&#8201;of&#8201;13</span></th>')

FOOT = {}
rows = []
for p in players:
    tds = []
    pod = sum(1 for c in p["cells"].values() if c["f"] and c["f"] <= 3)
    for e in events:
        c = p["cells"].get(e["id"])
        if not c:
            tds.append('        <td class="cell empty"><span>&#183;</span></td>')
            continue
        f, y = c["f"], c["y"]
        yy = str(y) if y else "?"
        mark = ""
        tip = f'{e["short"]} · {c["div"]} · {("field of " + str(y)) if y else "field size unavailable"}'
        if c["partners"]:
            tip += " · with " + ", ".join(c["partners"])
        if c["extra"]:
            mark = '<i class="mk">+</i>'
            ex = "; ".join(f'{x["f"]}/{x["y"] or "?"} {x["div"]}' for x in c["extra"])
            tip += f" · also entered: {ex}"
            FOOT[(p["name"], e["short"])] = ex
        tds.append(
            f'        <td class="cell {cls(f, y)}" title="{esc(tip)}">'
            f'<span class="fr"><b>{f}</b><s>/</s>{yy}</span>{mark}</td>')
    rows.append(f"""      <tr>
        <th scope="row" class="rowh"><span class="pn">{esc(p['name'])}</span>
          <span class="rmeta"><span class="tvchip">{p['tv']:.2f}</span>
          <span class="rsum">{len(p['cells'])} ev &#183; {pod} podium{'s' if pod != 1 else ''}</span></span></th>
{chr(10).join(tds)}
      </tr>""")

foot_items = "".join(
    f"<li><b>{esc(n)}</b> at <b>{esc(ev)}</b> &#8212; second entry: {esc(x)}</li>"
    for (n, ev), x in sorted(FOOT.items()))

HTML = f"""<title>BNTDP 18U Girls &#183; Shared Tournament Record</title>
<style>
:root {{
  --ground:#EFF1EE; --surface:#FAFBFA; --raise:#FFFFFF;
  --ink:#111B19; --body:#2C3A37; --muted:#5F6E6A; --faint:#8B9995;
  --line:#D5DCD9; --hair:#E4E9E7;
  --accent:#0B6E68; --accent-soft:#D9E7E5; --accent-mid:#8FC3BE;
  --gold:#9A6B12; --gold-soft:#F3E4C4; --gold-mid:#E3C583;
  --wash:#EAEDEB;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#0B1211; --surface:#121B19; --raise:#182322;
    --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
    --line:#243330; --hair:#1C2827;
    --accent:#57C3B6; --accent-soft:#123733; --accent-mid:#1E5C55;
    --gold:#DCA84A; --gold-soft:#382B12; --gold-mid:#6B5121;
    --wash:#161F1E;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#0B1211; --surface:#121B19; --raise:#182322;
  --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
  --line:#243330; --hair:#1C2827;
  --accent:#57C3B6; --accent-soft:#123733; --accent-mid:#1E5C55;
  --gold:#DCA84A; --gold-soft:#382B12; --gold-mid:#6B5121;
  --wash:#161F1E;
}}

* {{ box-sizing:border-box; }}
body {{
  margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  font-size:15px; line-height:1.6;
  -webkit-font-smoothing:antialiased;
}}
.wrap {{ max-width:1120px; margin:0 auto; padding:0 28px; }}
.serif {{ font-family:"Iowan Old Style",Georgia,"Times New Roman",serif; }}

/* ---- masthead ---- */
header {{ padding:64px 0 34px; border-bottom:1px solid var(--line); }}
.eyebrow {{
  font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin:0 0 18px;
}}
h1 {{
  font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(34px,5.2vw,54px); line-height:1.05; letter-spacing:-.02em;
  color:var(--ink); margin:0 0 16px; font-weight:600; text-wrap:balance;
}}
h1 em {{ font-style:italic; color:var(--accent); }}
.standfirst {{ font-size:17px; color:var(--muted); max-width:64ch; margin:0; }}
.facts {{ display:flex; flex-wrap:wrap; gap:0; margin:32px 0 0;
  border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:hidden; }}
.fact {{ flex:1 1 130px; padding:14px 18px; border-right:1px solid var(--hair); }}
.fact:last-child {{ border-right:0; }}
.fact b {{ display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; line-height:1.2; }}
.fact span {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }}

/* ---- sections ---- */
section {{ padding:48px 0 0; }}
h2 {{
  font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:25px; color:var(--ink); font-weight:600; letter-spacing:-.01em;
  margin:0 0 6px;
}}
.lede {{ color:var(--muted); margin:0 0 22px; max-width:70ch; font-size:14.5px; }}

/* ---- roster ---- */
.panel {{ border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; }}
.roster th, .roster td {{ padding:11px 14px; text-align:left; border-bottom:1px solid var(--hair); }}
.roster thead th {{
  font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint);
  font-weight:650; background:var(--wash); border-bottom:1px solid var(--line); white-space:nowrap;
}}
.roster tbody tr:last-child th, .roster tbody tr:last-child td {{ border-bottom:0; }}
.roster tbody tr:hover {{ background:var(--raise); }}
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

/* ---- matrix ---- */
.matrix-wrap {{ border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow-x:auto; }}
.matrix {{ border-collapse:separate; border-spacing:0; }}
.matrix th, .matrix td {{ border-bottom:1px solid var(--hair); border-right:1px solid var(--hair); }}
.matrix .evh {{
  width:96px; min-width:96px; vertical-align:bottom; padding:12px 9px 10px;
  background:var(--wash); border-bottom:1px solid var(--line);
  position:sticky; top:0; z-index:2; text-align:left;
}}
.evn {{ display:block; font-size:11.5px; line-height:1.3; color:var(--ink); font-weight:600; }}
.evd {{ display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:11px; color:var(--muted); margin-top:3px; font-variant-numeric:tabular-nums; }}
.evs {{ display:inline-block; margin-top:5px; font-size:9px; letter-spacing:.07em;
  text-transform:uppercase; color:var(--faint); border:1px solid var(--line);
  border-radius:2px; padding:1px 4px; }}
.evc {{ display:block; margin-top:5px; font-size:9.5px; letter-spacing:.05em;
  text-transform:uppercase; color:var(--accent); font-weight:650; }}
.matrix .rowh {{
  position:sticky; left:0; z-index:3; background:var(--surface);
  width:186px; min-width:186px; padding:10px 14px 10px 16px; text-align:left;
  border-right:1px solid var(--line); font-weight:500;
}}
.matrix thead .corner {{
  position:sticky; left:0; top:0; z-index:4; background:var(--wash);
  border-right:1px solid var(--line); border-bottom:1px solid var(--line);
  width:186px; min-width:186px; padding:12px 16px; text-align:left; vertical-align:bottom;
  font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint); font-weight:650;
}}
.rmeta {{ display:flex; align-items:center; gap:8px; margin-top:4px; }}
.tvchip {{
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12px; font-weight:650; color:var(--accent);
  background:var(--accent-soft); border-radius:2px; padding:1px 5px;
  font-variant-numeric:tabular-nums;
}}
.rsum {{ font-size:10.5px; color:var(--faint); white-space:nowrap; }}
.matrix tbody tr:hover .cell {{ box-shadow:inset 0 0 0 99px rgba(127,127,127,.055); }}
.cell {{
  width:96px; min-width:96px; padding:9px 8px; text-align:center; position:relative;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13px;
}}
.fr b {{ font-weight:700; font-size:14px; }}
.fr s {{ text-decoration:none; opacity:.4; margin:0 1px; }}
.mk {{ position:absolute; top:3px; right:5px; font-style:normal;
  font-size:9px; color:var(--faint); font-weight:700; }}
.cell.win {{ background:var(--gold-soft); color:var(--gold); box-shadow:inset 3px 0 0 var(--gold); }}
.cell.win b {{ color:var(--gold); }}
.cell.pod {{ background:var(--gold-soft); color:var(--gold); }}
.cell.t1 {{ background:var(--accent-soft); color:var(--accent); }}
.cell.t2 {{ background:color-mix(in srgb,var(--accent-soft) 58%,transparent); color:var(--accent); }}
.cell.t3 {{ background:color-mix(in srgb,var(--accent-soft) 28%,transparent); color:var(--body); }}
.cell.t4 {{ color:var(--muted); }}
.cell.t5 {{ color:var(--faint); }}
.cell.na {{ color:var(--faint); }}
.cell.empty {{ color:var(--hair); background:repeating-linear-gradient(-45deg,transparent,transparent 5px,var(--hair) 5px,var(--hair) 6px); }}
.cell.empty span {{ opacity:.55; }}

/* ---- legend / notes ---- */
.legend {{ display:flex; flex-wrap:wrap; gap:8px 20px; align-items:center; margin:16px 0 0; font-size:12px; color:var(--muted); }}
.key {{ display:inline-flex; align-items:center; gap:7px; }}
.sw {{ width:22px; height:14px; border:1px solid var(--line); border-radius:2px; display:inline-block; }}
.sw.win {{ background:var(--gold-soft); box-shadow:inset 3px 0 0 var(--gold); }}
.sw.pod {{ background:var(--gold-soft); }}
.sw.t1 {{ background:var(--accent-soft); }}
.sw.t2 {{ background:color-mix(in srgb,var(--accent-soft) 58%,transparent); }}
.sw.t3 {{ background:color-mix(in srgb,var(--accent-soft) 28%,transparent); }}
.sw.t5 {{ background:var(--surface); }}
.notes {{ margin:0 0 60px; }}
.notes ul {{ padding-left:19px; margin:10px 0 0; }}
.notes li {{ margin:7px 0; font-size:13.5px; color:var(--muted); max-width:76ch; }}
.notes b {{ color:var(--body); font-weight:600; }}
code {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12.5px; background:var(--wash); padding:1px 5px; border-radius:2px; color:var(--body); }}
footer {{ border-top:1px solid var(--line); padding:22px 0 70px; font-size:12px; color:var(--faint); }}
a {{ color:var(--accent); }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; animation:none !important; }} }}
@media (max-width:720px) {{
  .wrap {{ padding:0 18px; }}
  header {{ padding-top:40px; }}
  .matrix .rowh, .matrix thead .corner {{ width:150px; min-width:150px; }}
}}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">USA Volleyball &#183; Beach NTDP Summer Training Series 2026</p>
  <h1>The 18U girls, and <em>where they've all played</em></h1>
  <p class="standfirst">All thirteen athletes named to the Girls U18 roster for the Beach NTDP Summer
  Training Series at Chula Vista, cross-referenced against their Volleyball Life competition record
  for the twelve months ending 9 August 2026. Every cell is a finish over the size of the field
  in that athlete's division.</p>
  <div class="facts">
    <div class="fact"><b>13</b><span>Athletes</span></div>
    <div class="fact"><b>{total_events}</b><span>Distinct events</span></div>
    <div class="fact"><b>{len(events)}</b><span>Shared by 3+</span></div>
    <div class="fact"><b>{total_entries}</b><span>Division entries</span></div>
    <div class="fact"><b>12&#8202;mo</b><span>Aug &#8217;25 &#8211; Aug &#8217;26</span></div>
  </div>
</header>

<section>
  <h2>The roster</h2>
  <p class="lede">TruVolley is Volleyball Life's skill rating &#8212; a single number derived from
  match-by-match results against rated opposition. All thirteen carry 100&#8202;% confidence, so the
  ratings are directly comparable. Sorted strongest first.</p>
  <div class="panel">
    <table class="roster">
      <thead><tr>
        <th scope="col">Athlete</th><th scope="col">USAV region</th><th scope="col">Club</th>
        <th scope="col">TruVolley</th><th scope="col">Peak</th>
        <th scope="col">W&#8211;L</th><th scope="col">Events</th>
      </tr></thead>
      <tbody>
{chr(10).join(roster)}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>Players against shared tournaments</h2>
  <p class="lede">The {len(events)} events where at least three of the thirteen appeared, newest
  crowd first. Each cell reads <b>finish&#8202;/&#8202;field</b> &#8212; so <code>3/64</code> is third
  out of sixty-four teams. Hover any cell for the division, the field size and the partner.
  Hatched cells mean the athlete did not enter.</p>
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
    <span class="key"><span class="sw win"></span> Won the division</span>
    <span class="key"><span class="sw pod"></span> Podium (2nd&#8211;3rd)</span>
    <span class="key"><span class="sw t1"></span> Top 10&#8202;% of field</span>
    <span class="key"><span class="sw t2"></span> Top 25&#8202;%</span>
    <span class="key"><span class="sw t3"></span> Top half</span>
    <span class="key"><span class="sw t5"></span> Bottom half</span>
    <span class="key"><b>+</b> entered a second division at the same event</span>
  </div>
</div>

<div class="wrap">
<section class="notes">
  <h2>How to read it</h2>
  <ul>
    <li><b>Fields differ inside one event.</b> These athletes are split across age divisions, so at
    the AVP Juniors National Championships the 18U bracket held 64 teams while 16U held 72 &#8212;
    the denominators differ by design, and comparing across a row means comparing across divisions.</li>
    <li><b>Five-a-side club events are in here too.</b> The BVCA Orange County dates and Club&#8202;v&#8202;Club
    are team competitions, not pairs, so a finish reflects a squad of five or more rather than a duo.</li>
    <li><b>Where an athlete entered two divisions</b> at one event, the table shows her better finish
    and marks the cell with a <b>+</b>.{(" " + "Full second entries: <ul>" + foot_items + "</ul>") if foot_items else ""}</li>
    <li><b>Ties are shared.</b> Beach draws award equal finishes to teams eliminated in the same
    round, which is why blocks of 5th, 9th and 17th recur.</li>
    <li><b>Sanctioning bodies</b> are tagged on each column: AVPA (AVP&#8202;/&#8202;AVP Juniors),
    USAV, AAU, BVCA and p1440.</li>
  </ul>
</section>
<footer>
  Roster from USA Volleyball's 2026 Beach NTDP Summer Training Series listing. Results, field sizes
  and TruVolley ratings from Volleyball Life, retrieved 9 August 2026. Field size is the count of
  teams registered in that division.
</footer>
</div>
"""

open("bntdp.html", "w").write(HTML)
print("wrote bntdp.html", len(HTML), "bytes; multi-division marks:", len(FOOT))
