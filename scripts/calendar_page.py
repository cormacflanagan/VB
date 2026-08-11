"""Render the class calendar: every event the group contested, in date order.

Turnout is a magnitude, so the heat is a single-hue sequential ramp (light to dark,
monotonic in lightness), and the three tier columns share one scale — each cell is
shaded by the share of that tier present, so 12 of 15 reads darker than 21 of 30.
"""
import datetime, html, json, sys

VBL = "https://volleyballlife.com"
MIN_TURNOUT = 2
TIERS = (("t60", 60, "Top 60"), ("t30", 30, "Top 30"), ("t15", 15, "Top 15"))


def esc(s):
    return html.escape(str(s), quote=True)


def dfmt(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return datetime.date(y, m, d)


def heat(n, size):
    if not n:
        return 0
    share = n / size
    for i, edge in enumerate((0.08, 0.17, 0.30, 0.45, 0.62)):
        if share <= edge:
            return i + 1
    return 6


def build(group):
    D = json.load(open(f"calendar_{group}.json"))
    events = [e for e in D["events"] if e["t60"] >= MIN_TURNOUT]
    dropped = len(D["events"]) - len(events)
    wfrom, wto = D["window"]

    # month groups, in calendar order
    months, cur = [], None
    for e in events:
        key = e["date"][:7]
        if key != cur:
            cur = key
            months.append((key, []))
        months[-1][1].append(e)

    peak = {k: max(x["t60"] for x in v) for k, v in months}
    mx = max(peak.values())

    bars = []
    for k, v in months:
        h = peak[k] / mx * 100
        lab = datetime.date(int(k[:4]), int(k[5:7]), 1).strftime("%b")
        top = max(v, key=lambda x: x["t60"])
        bars.append(
            f'<div class="mb" title="{esc(lab)} {k[:4]} &#183; busiest: {esc(top["name"])} '
            f'({top["t60"]} of 60)"><span class="mbar" style="height:{h:.0f}%"></span>'
            f'<span class="mbn">{peak[k]}</span><span class="mbl">{lab}</span></div>')

    rows = []
    for k, v in months:
        d0 = datetime.date(int(k[:4]), int(k[5:7]), 1)
        rows.append(f'<tr class="mrow"><th colspan="7" scope="rowgroup">'
                    f'{d0.strftime("%B %Y")}<span class="mcount">{len(v)} event'
                    f'{"s" if len(v) != 1 else ""}</span></th></tr>')
        for e in v:
            dd = dfmt(e["date"])
            span = ""
            if e.get("endDate") and e["endDate"] != e["date"]:
                span = f'&#8211;{dfmt(e["endDate"]).day}'
            cells = "".join(
                f'<td class="ht h{heat(e[k2], size)}" title="{e[k2]} of the {label.lower()}">'
                f'{e[k2] or "&#183;"}</td>' for k2, size, label in TIERS)
            divs = ", ".join(f'{esc(d["name"])} <i>&#215;{d["n"]}</i>'
                             for d in e["divisions"][:3])
            nxt = ""
            if e.get("next"):
                nd = dfmt(e["next"]["date"])
                nxt = (f'<a class="lnk nx" href="{VBL}/tournament/{e["next"]["id"]}" '
                       f'target="_blank" rel="noopener">{nd.strftime("%-d %b %Y")}</a>')
            rows.append(f"""      <tr>
        <td class="dt num">{dd.strftime("%-d")}{span} <span class="dow">{dd.strftime("%a")}</span></td>
        <td class="evc"><a class="lnk" href="{VBL}/tournament/{e['tid']}" target="_blank"
          rel="noopener">{esc(e['name'])}</a><span class="dv">{divs}</span></td>
        <td class="loc">{esc(e['location']) if e['location'] else '&#8212;'}</td>
        <td><span class="sanc">{esc(e['sanction'])}</span></td>
{cells}
        <td class="nxc">{nxt or '<span class="dim">&#8212;</span>'}</td>
      </tr>""")

    returning = sorted((e for e in events if e.get("next")),
                       key=lambda e: e["next"]["date"])
    ret = "".join(
        f"""      <tr>
        <td class="num dim nw">{dfmt(e['next']['date']).strftime('%-d %b %Y')}</td>
        <td><a class="lnk" href="{VBL}/tournament/{e['next']['id']}" target="_blank"
          rel="noopener">{esc(e['next']['name'])}</a></td>
        <td class="loc">{esc(e['location']) if e['location'] else '&#8212;'}</td>
        <td class="num"><b>{e['t60']}</b><span class="dim"> / {e['t30']} / {e['t15']}</span></td>
      </tr>""" for e in returning)

    top_events = sorted(events, key=lambda e: -e["t60"])[:3]
    return f"""<title>Class of {group} &#183; Tournament calendar</title>
<style>
:root {{
  --ground:#EFF1EE; --surface:#FAFBFA; --raise:#FFFFFF;
  --ink:#111B19; --body:#2C3A37; --muted:#5F6E6A; --faint:#8B9995;
  --line:#D5DCD9; --hair:#E4E9E7; --wash:#EAEDEB;
  --accent:#0B6E68; --accent-soft:#D9E7E5; --gold:#9A6B12; --gold-soft:#F3E4C4;
  --h1:#EDF5F3; --h2:#CDE8E2; --h3:#A2D6CC; --h4:#6FC0B3; --h5:#2FA694; --h6:#00806F;
  --hink1:var(--body); --hink5:#FFFFFF; --hink6:#FFFFFF;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#0B1211; --surface:#121B19; --raise:#182322;
    --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
    --line:#243330; --hair:#1C2827; --wash:#161F1E;
    --accent:#57C3B6; --accent-soft:#123733; --gold:#DCA84A; --gold-soft:#382B12;
    --h1:#152220; --h2:#183A34; --h3:#1B5248; --h4:#1D6B5D; --h5:#1E8574; --h6:#2AA08C;
    --hink1:var(--body); --hink5:#F2FBF8; --hink6:#06201B;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#0B1211; --surface:#121B19; --raise:#182322;
  --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
  --line:#243330; --hair:#1C2827; --wash:#161F1E;
  --accent:#57C3B6; --accent-soft:#123733; --gold:#DCA84A; --gold-soft:#382B12;
  --h1:#152220; --h2:#183A34; --h3:#1B5248; --h4:#1D6B5D; --h5:#1E8574; --h6:#2AA08C;
  --hink1:var(--body); --hink5:#F2FBF8; --hink6:#06201B;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; font-size:15px;
  line-height:1.6; -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:none; margin:0; padding:0 clamp(18px,2.4vw,44px); }}
header {{ padding:60px 0 32px; border-bottom:1px solid var(--line); }}
.eyebrow {{ font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin:0 0 18px; }}
h1 {{ font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(32px,5vw,50px); line-height:1.06; letter-spacing:-.02em; color:var(--ink);
  margin:0 0 16px; font-weight:600; text-wrap:balance; max-width:22ch; }}
h1 em {{ font-style:italic; color:var(--accent); }}
.standfirst {{ font-size:17px; color:var(--muted); max-width:68ch; margin:0; }}
h2 {{ font-family:"Iowan Old Style",Georgia,"Times New Roman",serif; font-size:24px;
  color:var(--ink); font-weight:600; margin:0 0 6px; }}
.lede {{ color:var(--muted); margin:0 0 20px; max-width:72ch; font-size:14.5px; }}
section {{ padding:44px 0 0; }}
.facts {{ display:flex; flex-wrap:wrap; margin:30px 0 0; max-width:1300px;
  border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:hidden; }}
.fact {{ flex:1 1 140px; padding:14px 18px; border-right:1px solid var(--hair); }}
.fact:last-child {{ border-right:0; }}
.fact b {{ display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }}
.fact span {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }}

/* season shape */
.months {{ display:flex; gap:6px; align-items:flex-end; height:150px; max-width:900px;
  border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:16px 16px 8px; }}
.mb {{ flex:1; display:flex; flex-direction:column; justify-content:flex-end;
  align-items:center; height:100%; gap:4px; }}
.mbar {{ width:100%; max-width:46px; background:var(--h5); border-radius:3px 3px 0 0;
  min-height:2px; }}
.mbn {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px;
  color:var(--ink); font-weight:650; font-variant-numeric:tabular-nums; }}
.mbl {{ font-size:10.5px; color:var(--faint); letter-spacing:.04em; }}

.panel {{ border:1px solid var(--line); border-radius:3px; background:var(--surface);
  overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; }}
thead th {{ font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint);
  font-weight:650; background:var(--wash); border-bottom:1px solid var(--line);
  padding:10px 12px; text-align:left; white-space:nowrap; position:sticky; top:0; z-index:2; }}
td {{ padding:9px 12px; border-bottom:1px solid var(--hair); vertical-align:top; }}
tbody tr:hover td {{ background:var(--raise); }}
.mrow th {{ background:var(--wash); border-top:1px solid var(--line);
  border-bottom:1px solid var(--line); padding:9px 12px; text-align:left;
  font-family:"Iowan Old Style",Georgia,serif; font-size:15px; color:var(--ink);
  font-weight:600; letter-spacing:.01em; position:sticky; top:37px; z-index:1; }}
.mcount {{ font-family:system-ui,sans-serif; font-size:11px; font-weight:500;
  color:var(--faint); letter-spacing:.06em; text-transform:uppercase; margin-left:10px; }}
.num {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13px; }}
.dt {{ white-space:nowrap; color:var(--ink); font-weight:600; width:74px; }}
.dow {{ color:var(--faint); font-weight:400; font-size:11px; }}
.evc {{ min-width:250px; max-width:420px; }}
.evc .lnk {{ color:var(--ink); font-weight:600; font-size:13.5px; text-decoration:none; }}
.evc .lnk:hover {{ color:var(--accent); text-decoration:underline; text-underline-offset:2px; }}
.dv {{ display:block; font-size:11.5px; color:var(--faint); margin-top:2px; }}
.dv i {{ font-style:normal; color:var(--muted); font-weight:650;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10.5px; }}
.loc {{ font-size:12.5px; color:var(--muted); max-width:200px; }}
.sanc {{ font-size:9.5px; letter-spacing:.07em; text-transform:uppercase; color:var(--muted);
  border:1px solid var(--line); border-radius:2px; padding:2px 5px; white-space:nowrap; }}
.ht {{ width:52px; text-align:center; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13.5px; font-weight:650; color:var(--hink1);
  border-left:2px solid var(--surface); }}
.h0 {{ color:var(--faint); font-weight:400; }}
.h1 {{ background:var(--h1); }} .h2 {{ background:var(--h2); }} .h3 {{ background:var(--h3); }}
.h4 {{ background:var(--h4); }}
.h5 {{ background:var(--h5); color:var(--hink5); }}
.h6 {{ background:var(--h6); color:var(--hink6); }}
.nxc {{ white-space:nowrap; font-size:12.5px; }}
.nx {{ color:var(--accent); font-weight:600; text-decoration:none; }}
.nx:hover {{ text-decoration:underline; text-underline-offset:2px; }}
.dim {{ color:var(--faint); }}
.nw {{ white-space:nowrap; }}
.lnk {{ color:inherit; }}
.legend {{ display:flex; flex-wrap:wrap; gap:8px 18px; align-items:center; margin:14px 0 0;
  font-size:12px; color:var(--muted); }}
.key {{ display:inline-flex; align-items:center; gap:6px; }}
.sw {{ width:26px; height:14px; border:1px solid var(--line); border-radius:2px; display:inline-block; }}
.ramp {{ display:inline-flex; }}
.ramp span {{ width:22px; height:14px; border:1px solid var(--line); border-left:0; }}
.ramp span:first-child {{ border-left:1px solid var(--line); }}
.notes ul {{ padding-left:19px; margin:10px 0 0; }}
.notes li {{ margin:7px 0; font-size:13.5px; color:var(--muted); max-width:78ch; }}
.notes b {{ color:var(--body); font-weight:600; }}
footer {{ border-top:1px solid var(--line); padding:20px 0 64px; margin-top:44px;
  font-size:12px; color:var(--faint); max-width:82ch; }}
a {{ color:var(--accent); }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; }} }}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">Girls beach volleyball &#183; Class of {group} &#183; Season calendar</p>
  <h1>Where the class of {group} <em>actually turns up</em></h1>
  <p class="standfirst">Every tournament the 60 highest-rated girls in the class of {group}
  contested in the twelve months to {dfmt(wto).strftime('%-d %B %Y')}, in calendar order, with
  how many of the top 60, top 30 and top 15 entered each one. Built for picking next season's
  schedule: the darker the row, the more of the class you would have been playing against.</p>
  <div class="facts">
    <div class="fact"><b>{len(events)}</b><span>Events shown</span></div>
    <div class="fact"><b>{max(e['t60'] for e in events)}</b><span>Biggest turnout</span></div>
    <div class="fact"><b>{len(returning)}</b><span>Already re-scheduled</span></div>
    <div class="fact"><b>{len(D['events'])}</b><span>Events entered in all</span></div>
    <div class="fact"><b>12&#8202;mo</b><span>to {dfmt(wto).strftime('%-d %b %Y')}</span></div>
  </div>
</header>

<section>
  <h2>The shape of the season</h2>
  <p class="lede">The biggest single turnout in each month &#8212; how many of the top 60 met at
  the busiest event of that month. The season builds to a July peak and goes quiet in autumn.</p>
  <div class="months">{"".join(bars)}</div>
</section>

<section>
  <h2>The calendar</h2>
  <p class="lede">Every event that drew at least {MIN_TURNOUT} of the top 60, oldest first.
  {dropped} further events drew a single player and are left out. Shading runs on the share of
  each tier present, so the three columns are directly comparable: 12 of the top 15 shades
  darker than 21 of the top 30. Event names link to Volleyball Life; the last column is next
  season's edition where one is already scheduled.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Tournament</th><th scope="col">Location</th>
        <th scope="col">Body</th>
        <th scope="col" style="text-align:center">Top 60</th>
        <th scope="col" style="text-align:center">Top 30</th>
        <th scope="col" style="text-align:center">Top 15</th>
        <th scope="col">Next edition</th>
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
  <h2>Already on next season's schedule</h2>
  <p class="lede">Only {len(returning)} of the {len(events)} events above have a
  {int(wto[:4])}&#8211;{int(wto[:4])+1} edition on Volleyball Life yet, and they are almost all
  in the autumn &#8212; the winter and summer majors simply have not been posted this far out.
  These are the ones you can enter today, with last season's turnout as a guide to the field
  you would be walking into.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Tournament</th><th scope="col">Location</th>
        <th scope="col">Last season 60&#8202;/&#8202;30&#8202;/&#8202;15</th>
      </tr></thead>
      <tbody>
{ret}
      </tbody>
    </table>
  </div>
</section>

<section class="notes">
  <h2>How to read it, and what it is not</h2>
  <ul>
    <li><b>Turnout counts athletes, not teams.</b> A number is how many of that tier entered the
    event at all, across every division it ran. The division breakdown under each name shows
    where they actually played, with the count beside it.</li>
    <li><b>Doubles only.</b> Club, 3v3 and 5v5 entries are excluded throughout, on the same rule
    the class reports use &#8212; a placing in those says little about an individual.</li>
    <li><b>This is a map of the class of {group}, who are a year ahead of the class of 2028.</b>
    At a grad-year event an athlete from the younger class enters a different division, so what
    transfers is <i>where the strong fields gather</i>, not the bracket itself. The three
    columns tell you how deep the older class's field was, which is the part worth chasing.</li>
    <li><b>An empty last column mostly means "not posted yet", not "not happening".</b> Only
    {len(returning)} of these {len(events)} events have a {int(wto[:4])}&#8211;{int(wto[:4])+1}
    edition listed so far: the big July fixtures &#8212; AVP Juniors Nationals, BVCA Pairs
    Nationals, the AAU Hermosa pairs &#8212; and the domestic Futures Tour stops are typically
    published a few months out. Matching is by name after stripping years and ordinals, so a
    renamed event will also miss.</li>
    <li><b>Locations come from the tournament record</b> and are blank where the organiser left
    them unset, which is common for one-day local events.</li>
  </ul>
</section>
<footer>
  Class of {group} top 60 by TruVolley, from a partner-graph crawl run to closure
  ({D['label']}). Results, turnout and locations from Volleyball Life, retrieved
  {dfmt(wto).strftime('%-d %B %Y')}. Window {dfmt(wfrom).strftime('%-d %b %Y')} to
  {dfmt(wto).strftime('%-d %b %Y')}.
</footer>
</div>
"""


if __name__ == "__main__":
    g = sys.argv[1] if len(sys.argv) > 1 else "2027"
    out = f"calendar-{g}.html"
    open(out, "w").write(build(g))
    print("wrote", out)
