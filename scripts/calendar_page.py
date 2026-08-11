"""Render the class calendar: every event the group contested, in date order.

Turnout is a magnitude, so the heat is a single-hue sequential ramp (light to dark,
monotonic in lightness), and the three tier columns share one scale — each cell is
shaded by the share of that tier present, so 12 of 15 reads darker than 21 of 30.
"""
import datetime, html, json, re, sys

VBL = "https://volleyballlife.com"
CBVA_URL = "https://cbva.com"
MIN_TURNOUT = 4
FOCUS = "17U"
TIERS = (("t60", 60, "Top 60"), ("t30", 30, "Top 30"), ("t15", 15, "Top 15"))

# a home venue is worth listing whatever the turnout, because the cost of entering is
# an hour in the car rather than a flight; these are matched against CBVA's venue string
LOCAL = ("santa cruz",)
LOCAL_LABEL = "Santa Cruz"
# the divisions a 17U girl can enter there: the women's ladder, and the girls' 18U draw
LOCAL_DIV = re.compile(r"women|girl'?s\s*18u", re.I)
NOT_LOCAL_DIV = re.compile(r"\bmen'?s|boy'?s", re.I)


# the national-team pathway: selection events, not ordinary tournaments. Turnout here is
# not "who chose to come" but "who was picked or qualified", so it is counted against the
# published NTDP rosters as well as against the class.
PATHWAY = re.compile(r"national team trials|isf trials|youth olympic games trials"
                     r"|beach national championship|ntdp", re.I)
NTDP_GROUPS = (("18U", "Girls U18", 13), ("17U", "Girls U17", 20))


def ntdp_attendance():
    """How many of each published NTDP roster played each event, keyed by tournament id."""
    out = {}
    for g, _, _ in NTDP_GROUPS:
        try:
            d = json.load(open(f"{g}_clean.json"))
        except FileNotFoundError:
            continue
        for name, rows in d["entries"].items():
            for e in rows:
                out.setdefault(str(e["tid"]), {}).setdefault(g, set()).add(name)
    return out


# CBVA runs much of the Southern California circuit but Volleyball Life sanctions it
# "AVPA", so membership comes from CBVA's own listing (scripts/cbva.py), not the name.
try:
    CBVA = json.load(open("cbva_links.json"))
except FileNotFoundError:
    CBVA = {}


def esc(s):
    return html.escape(str(s), quote=True)


def local_events(fname):
    """Every CBVA tournament at the home venue, with only the divisions she could enter.

    Read straight from CBVA rather than from our own data, so a local date shows up even
    when nobody in the class travelled to it &#8212; which is most of them, and is exactly
    why the turnout-ranked calendar hides them.
    """
    try:
        cb = json.load(open(fname))["tournaments"]
    except FileNotFoundError:
        return []
    out = []
    for t in cb.values():
        if not any(v in t["venue"].lower() for v in LOCAL):
            continue
        divs = [d for d in t["divisions"]
                if LOCAL_DIV.search(d["name"]) and not NOT_LOCAL_DIV.search(d["name"])]
        if divs:
            out.append(dict(t, divisions=divs))
    out.sort(key=lambda t: t["date"])
    return out


def local_rows(rows, played, turnout=True):
    out = []
    for t in rows:
        dd = dfmt(t["date"])
        # CBVA sometimes runs a series label straight into the venue: "Cal Cup Tour StopMain"
        venue = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", t["venue"])
        divs = " ".join(
            f'<a class="ldiv" href="{CBVA_URL}/tournaments/{t["id"]}/{d["id"]}" target="_blank" '
            f'rel="noopener">{esc(re.sub(r"^.*?Bid Event ", "", d["name"]))}</a>'
            for d in t["divisions"])
        n = played.get(t["id"])
        out.append(f"""      <tr>
        <td class="num dim nw">{dd.strftime('%-d %b %Y')} <span class="dow">{dd.strftime('%a')}</span></td>
        <td class="evc"><a class="lnk" href="{CBVA_URL}/tournaments/{t['id']}" target="_blank"
          rel="noopener">{esc(venue)}</a></td>
        <td class="ldivs">{divs}</td>{
        f'<td class="num">{n}</td>' if turnout and n else
        '<td class="num dim">&#8212;</td>' if turnout else ''}
      </tr>""")
    return "".join(out)


def dfmt(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return datetime.date(y, m, d)


def body(e):
    """Sanctioning tag, plus a link out to CBVA's own page where CBVA lists the event."""
    out = f'<span class="sanc">{esc(e["sanction"])}</span>'
    cb = CBVA.get(str(e["tid"]))
    if cb:
        out += (f'<a class="sanc cbva" href="{esc(cb["url"])}" target="_blank" '
                f'rel="noopener" title="This event on CBVA">CBVA</a>')
    return out


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
    # the unit is a competition, not an event: an 18U bracket and the 17U beside it are
    # separate fields, so each clears the turnout bar on its own or is dropped
    events = []
    for e in D["events"]:
        keep = [b for b in e["brackets"] if b["t60"] >= MIN_TURNOUT]
        if keep:
            events.append(dict(e, brackets=keep))
    rowcount = sum(len(e["brackets"]) for e in events)
    dropped = sum(len(e["brackets"]) for e in D["events"]) - rowcount
    wfrom, wto = D["window"]

    # the bracket a reader is planning for gets its own section, with no turnout bar: a
    # 17U draw existing at all is the fact worth knowing, whoever turned up to it
    focus = [(e, b) for e in D["events"] for b in e["brackets"] if b["bracket"] == FOCUS]
    focus.sort(key=lambda x: x[0]["date"])
    focus_ent = sum(sum(d["n"] for d in b["divisions"]) for _, b in focus)
    all_ent = sum(sum(d["n"] for d in b["divisions"])
                  for e in D["events"] for b in e["brackets"])

    # month groups, in calendar order
    months, cur = [], None
    for e in events:
        key = e["date"][:7]
        if key != cur:
            cur = key
            months.append((key, []))
        months[-1][1].append(e)

    def best(e):
        """Turnout of the event's strongest single bracket &#8212; one field, one number."""
        return max(b["t60"] for b in e["brackets"])

    peak = {k: max(best(x) for x in v) for k, v in months}
    mx = max(peak.values())

    bars = []
    for k, v in months:
        h = peak[k] / mx * 100
        lab = datetime.date(int(k[:4]), int(k[5:7]), 1).strftime("%b")
        top = max(v, key=best)
        tb = max(top["brackets"], key=lambda b: b["t60"])
        bars.append(
            f'<div class="mb" title="{esc(lab)} {k[:4]} &#183; busiest: {esc(top["name"])} '
            f'&#183; {esc(tb["bracket"])} ({tb["t60"]} of 60)">'
            f'<span class="mbar" style="height:{h:.0f}%"></span>'
            f'<span class="mbn">{peak[k]}</span><span class="mbl">{lab}</span></div>')

    rows = []
    for k, v in months:
        d0 = datetime.date(int(k[:4]), int(k[5:7]), 1)
        rows.append(f'<tr class="mrow"><th colspan="9" scope="rowgroup">'
                    f'{d0.strftime("%B %Y")}<span class="mcount">{len(v)} event'
                    f'{"s" if len(v) != 1 else ""}</span></th></tr>')
        for e in v:
            dd = dfmt(e["date"])
            span = ""
            if e.get("endDate") and e["endDate"] != e["date"]:
                span = f'&#8211;{dfmt(e["endDate"]).day}'
            nxt = ""
            if e.get("next"):
                nd = dfmt(e["next"]["date"])
                nxt = (f'<a class="lnk nx" href="{VBL}/tournament/{e["next"]["id"]}" '
                       f'target="_blank" rel="noopener">{nd.strftime("%-d %b %Y")}</a>')
            n = len(e["brackets"])
            rs = f' rowspan="{n}"' if n > 1 else ""
            for i, b in enumerate(e["brackets"]):
                cells = "".join(
                    f'<td class="ht h{heat(b[k2], size)}" '
                    f'title="{b[k2]} of the {label.lower()} played {esc(b["bracket"])}">'
                    f'{b[k2] or "&#183;"}</td>' for k2, size, label in TIERS)
                divs = ", ".join(f'{esc(d["name"])} <i>&#215;{d["n"]}</i>'
                                 for d in b["divisions"][:2])
                lead = "" if i else f"""
        <td class="dt num"{rs}>{dd.strftime("%-d")}{span} <span class="dow">{dd.strftime("%a")}</span></td>
        <td class="evc"{rs}><a class="lnk" href="{VBL}/tournament/{e['tid']}" target="_blank"
          rel="noopener">{esc(e['name'])}</a></td>"""
                tail = "" if i else f"""
        <td class="loc"{rs}>{esc(e['location']) if e['location'] else '&#8212;'}</td>
        <td class="bdy"{rs}>{body(e)}</td>
        <td class="nxc"{rs}>{nxt or '<span class="dim">&#8212;</span>'}</td>"""
                rows.append(f"""      <tr class="{'evs' if not i else 'evc2'}">{lead}
        <td class="brk"><b>{esc(b['bracket'])}</b><span class="dv">{divs}</span></td>
{cells}{tail}
      </tr>""")

    foc = "".join(
        f"""      <tr>
        <td class="num dim nw">{dfmt(e['date']).strftime('%-d %b %Y')}</td>
        <td class="evc"><a class="lnk" href="{VBL}/tournament/{e['tid']}" target="_blank"
          rel="noopener">{esc(e['name'])}</a><span class="dv">{
          ", ".join(esc(d['name']) for d in b['divisions'])}</span></td>
        <td class="loc">{esc(e['location']) if e['location'] else '&#8212;'}</td>
        <td class="bdy">{body(e)}</td>""" + "".join(
            f'<td class="ht h{heat(b[k2], size)}" title="{b[k2]} of the {label.lower()}">'
            f'{b[k2] or "&#183;"}</td>' for k2, size, label in TIERS) + f"""
        <td class="nxc">{
          f'<a class="lnk nx" href="{VBL}/tournament/' + str(e['next']['id']) + '" '
          f'target="_blank" rel="noopener">'
          + dfmt(e['next']['date']).strftime('%-d %b %Y') + '</a>'
          if e.get('next') else '<span class="dim">&#8212;</span>'}</td>
      </tr>""" for e, b in focus)

    att = ntdp_attendance()
    path = sorted((e for e in D["events"] if PATHWAY.search(e["name"])),
                  key=lambda e: e["date"])
    pathrows = "".join(
        f"""      <tr>
        <td class="num dim nw">{dfmt(e['date']).strftime('%-d %b %Y')}</td>
        <td class="evc"><a class="lnk" href="{VBL}/tournament/{e['tid']}" target="_blank"
          rel="noopener">{esc(e['name'])}</a><span class="dv">{esc(e['location'])
          if e['location'] else ''}</span></td>""" + "".join(
            f'<td class="ht h{heat(e[k2], size)}" title="{e[k2]} of the {label.lower()}">'
            f'{e[k2] or "&#183;"}</td>' for k2, size, label in TIERS) + "".join(
            f'<td class="ht h{heat(len(att.get(str(e["tid"]), {}).get(g, ())), n)}" '
            f'title="{len(att.get(str(e["tid"]), {}).get(g, ()))} of the {n} on the '
            f'{esc(lab)} roster">{len(att.get(str(e["tid"]), {}).get(g, ())) or "&#183;"}'
            f'</td>' for g, lab, n in NTDP_GROUPS) + """
      </tr>""" for e in path)

    # how many of the group turned up to each local date, keyed by CBVA's id
    played = {}
    for tid, cb in CBVA.items():
        e = next((x for x in D["events"] if str(x["tid"]) == tid), None)
        if e:
            played[cb["cbvaId"]] = max(played.get(cb["cbvaId"], 0), e["t60"])
    past_local = local_events("cbva.json")
    next_local = local_events("cbva_upcoming.json")
    local_played = sum(1 for t in past_local if played.get(t["id"]))

    def top_bracket(e):
        return max(e["brackets"], key=lambda b: b["t60"])

    returning = sorted((e for e in events if e.get("next")),
                       key=lambda e: e["next"]["date"])
    ret = "".join(
        f"""      <tr>
        <td class="num dim nw">{dfmt(e['next']['date']).strftime('%-d %b %Y')}</td>
        <td><a class="lnk" href="{VBL}/tournament/{e['next']['id']}" target="_blank"
          rel="noopener">{esc(e['next']['name'])}</a></td>
        <td class="loc">{esc(e['location']) if e['location'] else '&#8212;'}</td>
        <td class="brk"><b>{esc(top_bracket(e)['bracket'])}</b></td>
        <td class="num"><b>{top_bracket(e)['t60']}</b><span class="dim">
          / {top_bracket(e)['t30']} / {top_bracket(e)['t15']}</span></td>
      </tr>""" for e in returning)
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
.brk {{ white-space:nowrap; width:170px; }}
.brk .dv {{ white-space:normal; }}
.brk b {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px;
  color:var(--ink); font-weight:650; letter-spacing:.02em; }}
.evs td {{ border-top:1px solid var(--line); }}
.evc2 .brk {{ padding-left:12px; }}
.dow {{ color:var(--faint); font-weight:400; font-size:11px; }}
.evc {{ min-width:250px; max-width:420px; }}
.evc .lnk {{ color:var(--ink); font-weight:600; font-size:13.5px; text-decoration:none; }}
.evc .lnk:hover {{ color:var(--accent); text-decoration:underline; text-underline-offset:2px; }}
.dv {{ display:block; font-size:11.5px; color:var(--faint); margin-top:2px; }}
.dv i {{ font-style:normal; color:var(--muted); font-weight:650;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10.5px; }}
.loc {{ font-size:12.5px; color:var(--muted); max-width:200px; }}
.sanc {{ font-size:9.5px; letter-spacing:.07em; text-transform:uppercase; color:var(--muted);
  border:1px solid var(--line); border-radius:2px; padding:2px 5px; white-space:nowrap;
  display:inline-block; }}
.bdy {{ white-space:nowrap; }}
h3 {{ font-family:"Iowan Old Style",Georgia,serif; font-size:17px; color:var(--ink);
  font-weight:600; margin:0 0 10px; }}
.ldivs {{ display:flex; flex-wrap:wrap; gap:5px; max-width:460px; }}
.ldiv {{ font-size:11px; color:var(--accent); background:var(--accent-soft);
  border-radius:2px; padding:2px 7px; text-decoration:none; white-space:nowrap; }}
.ldiv:hover {{ text-decoration:underline; text-underline-offset:2px; }}
.cbva {{ color:var(--accent); border-color:var(--accent-soft); text-decoration:none;
  font-weight:650; margin-left:5px; }}
.cbva:hover {{ background:var(--accent-soft); }}
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
  contested in the twelve months to {dfmt(wto).strftime('%-d %B %Y')}, in calendar order, split
  by age bracket, with how many of the top 60, top 30 and top 15 entered each field. Built for
  picking next season's schedule: the darker the row, the more of the class you would have been
  playing against.</p>
  <div class="facts">
    <div class="fact"><b>{rowcount}</b><span>Brackets shown</span></div>
    <div class="fact"><b>{len(events)}</b><span>Across events</span></div>
    <div class="fact"><b>{max(best(e) for e in events)}</b><span>Biggest single field</span></div>
    <div class="fact"><b>{len(returning)}</b><span>Already re-scheduled</span></div>
    <div class="fact"><b>{len(D['events'])}</b><span>Events entered in all</span></div>
    <div class="fact"><b>12&#8202;mo</b><span>to {dfmt(wto).strftime('%-d %b %Y')}</span></div>
  </div>
</header>

<section>
  <h2>The shape of the season</h2>
  <p class="lede">The biggest single field in each month &#8212; how many of the top 60 met in
  one bracket at the busiest event of that month. The season builds to a July peak and goes
  quiet in autumn.</p>
  <div class="months">{"".join(bars)}</div>
</section>

<section>
  <h2>The national-team pathway</h2>
  <p class="lede">The dates that decide selection, and who was actually in them. The last two
  columns count the athletes later named to the {NTDP_GROUPS[0][1]} and {NTDP_GROUPS[1][1]}
  NTDP rosters &#8212; {NTDP_GROUPS[0][2]} and {NTDP_GROUPS[1][2]} girls &#8212; so they read as
  the share of the selected group that was in the room, not as ordinary turnout. Shading is on
  the same share-of-tier scale as the calendar below.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Event</th>
        <th scope="col" style="text-align:center">Top 60</th>
        <th scope="col" style="text-align:center">Top 30</th>
        <th scope="col" style="text-align:center">Top 15</th>
        <th scope="col" style="text-align:center">NTDP U18</th>
        <th scope="col" style="text-align:center">NTDP U17</th>
      </tr></thead>
      <tbody>
{pathrows}
      </tbody>
    </table>
  </div>
  <p class="lede" style="margin-top:14px">Two dates carry the selection: the <b>U18 Beach
  National Team Trials</b> at the end of January and the <b>Youth Olympic Games Trials</b> in
  June, which between them held 12 and 11 of the eventual U18 roster of
  {NTDP_GROUPS[0][2]}. Everything else on this list is a national title or a qualifier rather
  than a selection event, and the NTDP columns show it &#8212; one or two names apiece.</p>
</section>

<section>
  <h2>Local &#8212; {LOCAL_LABEL}</h2>
  <p class="lede">The rest of this page ranks fields by how much of the class turns up, which
  buries the home venue: of the {len(past_local)} {LOCAL_LABEL} dates last season with a
  women's or girls' 18U draw, {local_played} drew anyone from the top 60. That is a fact about
  travel, not about the volleyball &#8212; and it cuts the other way when the drive is an hour.
  These come straight from CBVA's own listing rather than from the class's record, so a date
  appears whether or not anyone in the class went. Men's and boys' draws are dropped; on the
  juniors dates the same event also runs 12U, 14U and 16U.</p>
  <h3>Already scheduled</h3>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Venue</th>
        <th scope="col">Draws she can enter</th>
      </tr></thead>
      <tbody>
{local_rows(next_local, played, turnout=False)}
      </tbody>
    </table>
  </div>
  <p class="lede" style="margin:12px 0 26px">CBVA posts roughly a season at a time, so this list
  runs out in the autumn; the juniors Cal&#8202;Cup bid series ran June and July last year and
  has not been posted yet.</p>
  <h3>Last season, for the pattern</h3>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Venue</th>
        <th scope="col">Draws offered</th>
        <th scope="col">Class of {group}</th>
      </tr></thead>
      <tbody>
{local_rows(past_local, played)}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>Where the {FOCUS} draw actually exists</h2>
  <p class="lede">This class <em>was</em> last season's {FOCUS} age group, so these are the
  fields a {FOCUS} player meets. The striking thing is how few of them there are: of the
  {len(D['events'])} events the class entered, <b>{len(focus)} ran a {FOCUS} bracket at all</b>
  &#8212; {focus_ent} of their {all_ent} entries. Everywhere else the choice was to play up into
  18U. No turnout bar is applied here; a {FOCUS} draw existing is the fact worth knowing.</p>
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
{foc}
      </tbody>
    </table>
  </div>
  <p class="lede" style="margin-top:14px">Three series carry it: AVP Juniors (all three
  championships), the AAU Hermosa pairs, and BVCA's West Coast pairs &#8212; plus one recruiting
  showcase that drew the bracket by graduating class. Everything else on the calendar below
  offers 18U or the adult women's open and nothing in between, which is why the class's {FOCUS}
  record is thin: the draw was not there to enter, not avoided.</p>
</section>

<section>
  <h2>The calendar</h2>
  <p class="lede">One row per <i>bracket</i>, not per event: the 18U field and the 17U field
  running beside it are separate competitions, so each is counted and judged on its own. Every
  bracket that drew at least {MIN_TURNOUT} of the top 60 is here, oldest first; {dropped}
  further brackets drew fewer and are left out. Shading runs on the share of
  each tier present, so the three columns are directly comparable: 12 of the top 15 shades
  darker than 21 of the top 30. Event names link to Volleyball Life; the last column is next
  season's edition where one is already scheduled.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Tournament</th><th scope="col">Bracket</th>
        <th scope="col" style="text-align:center">Top 60</th>
        <th scope="col" style="text-align:center">Top 30</th>
        <th scope="col" style="text-align:center">Top 15</th>
        <th scope="col">Location</th><th scope="col">Body</th>
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
  {int(wto[:4])}&#8211;{int(wto[:4])+1} edition on Volleyball Life yet &#8212; most of the
  calendar simply has not been posted this far out, so a blank here means unscheduled, not
  discontinued. These are the ones you can enter today, with last season's turnout as a guide
  to the field you would be walking into. The bracket named is the one this class filled last
  season; they move up a year for the next edition, so read it as where the depth was, not
  where they will be drawn.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Tournament</th><th scope="col">Location</th>
        <th scope="col">Bracket</th>
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
    <li><b>Turnout counts athletes, not teams.</b> A number is how many of that tier entered
    that bracket; a girl who played both the 18U and the 17U is counted in both rows, which is
    the point of splitting them.</li>
    <li><b>Brackets are folded onto the age they are actually played at.</b> Organisers label
    one field a dozen ways &#8212; "Girls 18U", "U18 Girls", "Girls 18:U (Grad Year 2026-2027)"
    and "Class of '26 &amp; Younger" are the same competition. An explicit age wins; failing
    that the youngest graduating year admitted sets the ceiling. The raw division names sit
    under each bracket label, with the count beside them. <b>Women's</b> is the adult open
    draw, which several of this class enter and which is a materially harder field than the
    juniors bracket at the same event.</li>
    <li><b>Doubles only.</b> Club, 3v3 and 5v5 entries are excluded throughout, on the same rule
    the class reports use &#8212; a placing in those says little about an individual.</li>
    <li><b>This is a map of the class of {group}, who are a year ahead of the class of 2028.</b>
    At a grad-year event an athlete from the younger class enters a different division, so what
    transfers is <i>where the strong fields gather</i>, not the bracket itself. The three
    columns tell you how deep the older class's field was, which is the part worth chasing.</li>
    <li><b>An empty last column mostly means "not posted yet", not "not happening".</b> Only
    {len(returning)} of these {len(events)} events have a {int(wto[:4])}&#8211;{int(wto[:4])+1}
    edition listed so far. AVP Juniors Nationals, BVCA Pairs Nationals and the Futures Tour
    stops are typically published a few months out, so they will appear closer to the date.
    Matching is by name after stripping years and ordinals, so a renamed event will also
    miss.</li>
    <li><b>CBVA events link out to CBVA.</b> CBVA runs much of the Southern California
    circuit, but Volleyball Life records the sanction as "AVPA", so the name and the sanction
    field cannot tell you which events are theirs. The tag is set by matching our events against
    CBVA's own tournament listing on date and venue, so an event carries it only when CBVA
    lists it; the link goes to that event's CBVA page, and to the specific division where the
    two agree on its name.</li>
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
