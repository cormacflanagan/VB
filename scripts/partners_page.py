"""Who partners with whom, inside a group — matrix plus per-player partner counts.

Competitions-played-together is a magnitude, so the matrix uses a single-hue sequential
ramp. The per-player table counts *every* partner, inside the group or not, because the
most-used partner is frequently someone outside the cut — which is exactly why a row can
be blank across the matrix and still belong to a settled pair.
"""
import html, json, sys
from collections import Counter, defaultdict

VBL = "https://volleyballlife.com"


def esc(s):
    return html.escape(str(s), quote=True)


def step(n):
    if not n:
        return 0
    return 1 if n == 1 else 2 if n == 2 else 3 if n == 3 else 4 if n <= 5 else 5 if n <= 7 else 6


def build(group):
    site = json.load(open(f"{group}_site.json"))
    clean = json.load(open(f"{group}_clean.json"))
    players = site["players"]
    order = [p["name"] for p in players]
    rank = {n: i + 1 for i, n in enumerate(order)}
    ids = {p["name"]: p.get("id") for p in players}
    grp = set(order)

    pair = defaultdict(set)
    allp = defaultdict(Counter)
    for n, rows in clean["entries"].items():
        for e in rows:
            for q in e["partners"]:
                allp[n][q] += 1
                if q in grp:
                    pair[tuple(sorted((n, q)))].add((e["tid"], e["tdId"]))
    cnt = {k: len(v) for k, v in pair.items()}

    def lnk(nm):
        pid = ids.get(nm)
        return (f'<a class="lnk" href="{VBL}/player/{pid}" target="_blank" rel="noopener">'
                f'{esc(nm)}</a>') if pid else esc(nm)

    # ---- matrix ----
    mrows = []
    for a in order:
        cells = []
        for b in order:
            if a == b:
                cells.append('<td class="pc self"></td>')
                continue
            n = cnt.get(tuple(sorted((a, b))), 0)
            if not n:
                cells.append('<td class="pc none"></td>')
                continue
            cells.append(f'<td class="pc s{step(n)}" title="{esc(a)} and {esc(b)} played '
                         f'{n} competition{"s" if n != 1 else ""} together">{n}</td>')
        mrows.append(f'<tr><th class="pr"><span class="rk">{rank[a]}</span>{lnk(a)}</th>'
                     + "".join(cells) + "</tr>")
    heads = "".join(f'<th class="ph" title="{esc(n)}">{rank[n]}</th>' for n in order)

    # ---- per-player ----
    prows = []
    for p in players:
        n = p["name"]
        c = allp[n]
        comps = len(clean["entries"][n])
        distinct = len(c)
        ingrp = sum(1 for q in c if q in grp)
        top, tn = (c.most_common(1)[0] if c else ("—", 0))
        share = (tn / comps * 100) if comps else 0
        outside = "" if top in grp else '<i class="out" title="not in this group">&#9679;</i>'
        prows.append(f"""      <tr>
        <th scope="row"><span class="rk">{rank[n]}</span>{lnk(n)}</th>
        <td class="num">{comps}</td>
        <td class="num big">{distinct or '&#8212;'}</td>
        <td class="num dim">{ingrp}</td>
        <td>{lnk(top) if top in grp else esc(top)}{outside}
          <span class="dim">&#215;{tn}</span></td>
        <td class="num nw">{share:.0f}%
          <span class="bar"><span style="width:{share:.0f}%"></span></span></td>
      </tr>""")

    # ---- most frequent pairings, in and out of group ----
    top_in = sorted(cnt.items(), key=lambda kv: -kv[1])[:12]
    ir = "".join(
        f"""      <tr><td class="num big">{v}</td><td>{lnk(a)} <span class="dim">#{rank[a]}</span></td>
        <td>{lnk(b)} <span class="dim">#{rank[b]}</span></td></tr>"""
        for (a, b), v in top_in)
    ext = Counter()
    for n, c in allp.items():
        for q, v in c.items():
            if q not in grp:
                ext[(n, q)] = max(ext[(n, q)], v)
    top_out = sorted(ext.items(), key=lambda kv: -kv[1])[:12]
    er = "".join(
        f"""      <tr><td class="num big">{v}</td><td>{lnk(a)} <span class="dim">#{rank[a]}</span></td>
        <td>{esc(b)}</td></tr>""" for (a, b), v in top_out)

    tot_comps = sum(len(v) for v in clean["entries"].values())
    solo = [p["name"] for p in players if len(allp[p["name"]]) == 1]
    label = site["label"]
    N = len(order)
    return f"""<title>{esc(label)} &#183; Partnerships</title>
<style>
:root {{
  --ground:#EFF1EE; --surface:#FAFBFA; --raise:#FFFFFF;
  --ink:#111B19; --body:#2C3A37; --muted:#5F6E6A; --faint:#8B9995;
  --line:#D5DCD9; --hair:#E4E9E7; --wash:#EAEDEB; --accent:#0B6E68; --accent-soft:#D9E7E5;
  --s1:#EDF5F3; --s2:#CDE8E2; --s3:#A2D6CC; --s4:#6FC0B3; --s5:#2FA694; --s6:#00806F;
  --sink:var(--body); --sink5:#FFFFFF; --sink6:#FFFFFF;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#0B1211; --surface:#121B19; --raise:#182322;
    --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
    --line:#243330; --hair:#1C2827; --wash:#161F1E; --accent:#57C3B6; --accent-soft:#123733;
    --s1:#152220; --s2:#183A34; --s3:#1B5248; --s4:#1D6B5D; --s5:#1E8574; --s6:#2AA08C;
    --sink:var(--body); --sink5:#F2FBF8; --sink6:#06201B;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#0B1211; --surface:#121B19; --raise:#182322;
  --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
  --line:#243330; --hair:#1C2827; --wash:#161F1E; --accent:#57C3B6; --accent-soft:#123733;
  --s1:#152220; --s2:#183A34; --s3:#1B5248; --s4:#1D6B5D; --s5:#1E8574; --s6:#2AA08C;
  --sink:var(--body); --sink5:#F2FBF8; --sink6:#06201B;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; font-size:15px;
  line-height:1.6; -webkit-font-smoothing:antialiased; }}
.wrap {{ max-width:none; margin:0; padding:0 clamp(18px,2.4vw,44px); }}
header {{ padding:60px 0 30px; border-bottom:1px solid var(--line); }}
.eyebrow {{ font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--accent);
  font-weight:650; margin:0 0 18px; }}
h1 {{ font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(32px,5vw,50px); line-height:1.06; letter-spacing:-.02em; color:var(--ink);
  margin:0 0 16px; font-weight:600; text-wrap:balance; max-width:20ch; }}
h1 em {{ font-style:italic; color:var(--accent); }}
.standfirst {{ font-size:17px; color:var(--muted); max-width:66ch; margin:0; }}
h2 {{ font-family:"Iowan Old Style",Georgia,"Times New Roman",serif; font-size:24px;
  color:var(--ink); font-weight:600; margin:0 0 6px; }}
.lede {{ color:var(--muted); margin:0 0 20px; max-width:72ch; font-size:14.5px; }}
section {{ padding:44px 0 0; }}
.facts {{ display:flex; flex-wrap:wrap; margin:28px 0 0; max-width:1300px;
  border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:hidden; }}
.fact {{ flex:1 1 150px; padding:14px 18px; border-right:1px solid var(--hair); }}
.fact:last-child {{ border-right:0; }}
.fact b {{ display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }}
.fact span {{ font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }}
.panel {{ border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:auto; }}
table {{ border-collapse:separate; border-spacing:0; width:100%; }}
thead th {{ font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint);
  font-weight:650; background:var(--wash); border-bottom:1px solid var(--line);
  padding:10px 12px; text-align:left; white-space:nowrap; }}
td, tbody th {{ padding:8px 12px; border-bottom:1px solid var(--hair); text-align:left; }}
tbody tr:hover td {{ background:var(--raise); }}
.num {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; font-size:13px; }}
.big {{ font-size:15px; font-weight:700; color:var(--ink); }}
.dim {{ color:var(--faint); }}
.nw {{ white-space:nowrap; }}
.rk {{ display:inline-block; min-width:24px; color:var(--faint);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; }}
.lnk {{ color:var(--ink); text-decoration:none; font-weight:600; font-size:13.5px; }}
.lnk:hover {{ color:var(--accent); text-decoration:underline; text-underline-offset:2px; }}
.out {{ font-style:normal; color:var(--accent); font-size:8px; vertical-align:super;
  margin-left:3px; }}
.bar {{ display:inline-block; width:70px; height:5px; background:var(--wash);
  border:1px solid var(--hair); border-radius:2px; overflow:hidden; margin-left:8px;
  vertical-align:middle; }}
.bar span {{ display:block; height:100%; background:var(--accent); }}
/* matrix */
.mx-wrap {{ border:1px solid var(--line); border-radius:3px; background:var(--surface);
  overflow:auto; max-height:80vh; }}
.mx th, .mx td {{ border-bottom:1px solid var(--hair); border-right:1px solid var(--hair); }}
.mx .corner {{ position:sticky; left:0; top:0; z-index:4; background:var(--wash); width:216px;
  min-width:216px; padding:10px 14px; vertical-align:bottom; font-size:10.5px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--faint); font-weight:650;
  border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
.ph {{ position:sticky; top:0; z-index:2; background:var(--wash); width:42px; min-width:42px;
  padding:8px 2px; text-align:center; border-bottom:1px solid var(--line);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10.5px;
  color:var(--muted); font-weight:650; }}
.pr {{ position:sticky; left:0; z-index:3; background:var(--surface); width:216px;
  min-width:216px; padding:7px 12px; white-space:nowrap; font-weight:500;
  border-right:1px solid var(--line); }}
.pc {{ width:42px; min-width:42px; text-align:center; padding:6px 2px; color:var(--sink);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12.5px;
  font-weight:650; font-variant-numeric:tabular-nums; }}
.pc.s1 {{ background:var(--s1); }} .pc.s2 {{ background:var(--s2); }}
.pc.s3 {{ background:var(--s3); }} .pc.s4 {{ background:var(--s4); }}
.pc.s5 {{ background:var(--s5); color:var(--sink5); }}
.pc.s6 {{ background:var(--s6); color:var(--sink6); }}
.pc.none {{ background:transparent; }}
.pc.self {{ background:repeating-linear-gradient(-45deg,transparent,transparent 4px,
  var(--hair) 4px,var(--hair) 5px); }}
.mx tbody tr:hover .pc {{ box-shadow:inset 0 0 0 99px rgba(127,127,127,.05); }}
.legend {{ display:flex; flex-wrap:wrap; gap:8px 18px; align-items:center; margin:14px 0 0;
  font-size:12px; color:var(--muted); }}
.ramp {{ display:inline-flex; }}
.ramp span {{ width:22px; height:14px; border:1px solid var(--line); border-left:0; }}
.ramp span:first-child {{ border-left:1px solid var(--line); }}
.cols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(340px,1fr)); gap:26px;
  max-width:1200px; }}
.notes ul {{ padding-left:19px; margin:10px 0 0; }}
.notes li {{ margin:7px 0; font-size:13.5px; color:var(--muted); max-width:78ch; }}
.notes b {{ color:var(--body); font-weight:600; }}
footer {{ border-top:1px solid var(--line); padding:20px 0 64px; margin-top:44px;
  font-size:12px; color:var(--faint); max-width:82ch; }}
a {{ color:var(--accent); }}
:focus-visible {{ outline:2px solid var(--accent); outline-offset:2px; }}
</style>

<div class="wrap">
<header>
  <p class="eyebrow">{esc(label)} &#183; Partnerships</p>
  <h1>Who plays <em>with</em> whom</h1>
  <p class="standfirst">Partnerships among the {N} highest-rated girls in the class of 2028, over
  the twelve months to 11 August 2026. The matrix counts competitions two of them entered as a
  pair; the table counts how many different partners each has had, inside this group or out.</p>
  <div class="facts">
    <div class="fact"><b>{len(cnt)}</b><span>Pairings inside the {N}</span></div>
    <div class="fact"><b>{N * (N - 1) // 2}</b><span>Possible pairings</span></div>
    <div class="fact"><b>{max(cnt.values())}</b><span>Most events together</span></div>
    <div class="fact"><b>{len({q for c in allp.values() for q in c})}</b><span>Distinct partners in all</span></div>
    <div class="fact"><b>{tot_comps}</b><span>Doubles entries</span></div>
  </div>
</header>

<section>
  <h2>Partner counts</h2>
  <p class="lede">Sorted by rating. <b>Partners</b> is how many different girls she has played
  a competition with; <b>in group</b> is how many of those are among these {N}. The last column
  is the share of her competitions spent with her single most-used partner &#8212; a rough
  measure of how settled she is. A {'&#9679;'} marks a most-used partner from outside the group.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Athlete</th><th scope="col">Comps</th><th scope="col">Partners</th>
        <th scope="col">In group</th><th scope="col">Most-used partner</th>
        <th scope="col">Share with her</th>
      </tr></thead>
      <tbody>
{chr(10).join(prows)}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>The partnership matrix</h2>
  <p class="lede">Competitions entered together, for the {len(cnt)} pairings that have happened
  at all out of {N * (N - 1) // 2} possible. Rows are athletes in rating order, columns the same
  athletes by rank number. Blank means they have never partnered.</p>
  <div class="mx-wrap">
    <table class="mx">
      <thead><tr><th class="corner">Athlete</th>{heads}</tr></thead>
      <tbody>
{chr(10).join(mrows)}
      </tbody>
    </table>
  </div>
  <div class="legend">
    <span class="key">Competitions together:</span>
    <span class="key"><span class="ramp"><span style="background:var(--s1)"></span>
      <span style="background:var(--s2)"></span><span style="background:var(--s3)"></span>
      <span style="background:var(--s4)"></span><span style="background:var(--s5)"></span>
      <span style="background:var(--s6)"></span></span> 1 &#8594; 8</span>
    <span class="key">blank &#8212; never partnered</span>
  </div>
</section>

<section>
  <h2>The most-used pairings</h2>
  <div class="cols">
    <div>
      <p class="lede">Inside the group.</p>
      <div class="panel"><table>
        <thead><tr><th scope="col">Comps</th><th scope="col">Athlete</th>
          <th scope="col">Partner</th></tr></thead>
        <tbody>
{ir}
        </tbody></table></div>
    </div>
    <div>
      <p class="lede">With partners from outside the group &#8212; the pairings the matrix
      cannot show.</p>
      <div class="panel"><table>
        <thead><tr><th scope="col">Comps</th><th scope="col">Athlete</th>
          <th scope="col">Partner (outside)</th></tr></thead>
        <tbody>
{er}
        </tbody></table></div>
    </div>
  </div>
</section>

<section class="notes">
  <h2>How to read it</h2>
  <ul>
    <li><b>A blank row is not a loner.</b> Only {len(cnt)} of the {N * (N - 1) // 2} possible
    pairings inside this group have ever happened, because most of these girls partner with
    someone outside the top 30. Kendal Walker has no in-group partnership at all, yet has
    played 14 competitions with one partner &#8212; the second table is where those live.</li>
    <li><b>A competition, not a match.</b> Each count is one event-division entered together,
    the same unit the class reports use, so a weekend played as a pair counts once however
    many matches it ran to.</li>
    <li><b>Doubles only.</b> Club, 3v3 and 5v5 entries are excluded throughout, so these are
    genuine two-player partnerships.</li>
    <li><b>Partner counts include everyone</b>, rated or not, inside this group or outside it.
    That is the honest denominator for "how settled is she" &#8212;
    {esc(", ".join(solo))} played the whole year with a single partner.</li>
  </ul>
</section>
<footer>
  {esc(label)}, cut on TruVolley as of 11 August 2026. Partnerships and results from
  Volleyball Life, doubles only, twelve months to 11 August 2026.
</footer>
</div>
"""


if __name__ == "__main__":
    g = sys.argv[1] if len(sys.argv) > 1 else "2028_top30"
    out = f"partners-{g}.html"
    open(out, "w").write(build(g))
    print("wrote", out)
