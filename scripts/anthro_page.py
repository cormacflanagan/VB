"""Render the Olympic height/weight page from data/olympedia_bv.json.

  python3 scripts/anthro_page.py   ->  docs/anthro.html

Two charts, both inline SVG so the page needs no script and no network:

  1. Height against weight for every woman in the Olympic beach volleyball record with
     both measurements, senior and Youth Olympic kept as separate series, with the
     +/-3 cm band around Haisley's height marked.
  2. The weight distribution inside that band, senior above the axis and youth below,
     both normalised to share-of-group because the two samples are different sizes.

Measurements are integers, so a lot of athletes land on the same lattice point. Points
carry a small deterministic jitter (from the athlete id, so it is stable between runs)
purely to separate them; the axis readout and every number in the prose come from the
unjittered values.
"""
import json, math, os, statistics as st

HERE = os.path.dirname(__file__) or "."
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "docs", "anthro.html")
SRC = "https://www.olympedia.org"

LB = 1 / 0.45359237
HER_CM, HER_LB = 175.26, 146.0          # 5 ft 9 in
HER_KG = HER_LB / LB
BAND = (172, 178)                       # +/-3 cm, the widest window that stays "her height"
BIN = 2                                 # kg


def lb(kg):
    return kg * LB


def ftin(cm):
    inches = round(cm / 2.54)
    return f"{inches // 12}&#8242;{inches % 12}&#8243;"


def pct_of(vals, x):
    """Percentile of x in vals, splitting ties (Haisley sits between lattice points)."""
    n = len(vals)
    return 100 * (sum(1 for v in vals if v < x) + 0.5 * sum(1 for v in vals if v == x)) / n


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    b = sxy / sxx
    return b, my - b * mx, sxy / math.sqrt(sxx * syy)


def ord_(n):
    n = int(round(n))
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def jitter(pid, k):
    """Deterministic +/-0.3 wobble so co-located integer measurements stay countable."""
    return ((pid * (7919 if k else 6997)) % 1000 / 1000 - 0.5) * 0.6


# ---------------------------------------------------------------- charts

def scatter(sen, yth, w=1000, h=560):
    L, R, T, B = 70, 74, 30, 78
    x0, x1, y0, y1 = 160, 198, 52, 88
    px = lambda cm: L + (cm - x0) / (x1 - x0) * (w - L - R)
    py = lambda kg: h - B - (kg - y0) / (y1 - y0) * (h - T - B)
    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" '
         f'aria-label="Height against weight for Olympic beach volleyball women">']

    o.append(f'<rect x="{px(BAND[0]):.1f}" y="{T}" width="{px(BAND[1]) - px(BAND[0]):.1f}" '
             f'height="{h - T - B}" class="band"/>')
    o.append(f'<text x="{(px(BAND[0]) + px(BAND[1])) / 2:.1f}" y="{T + 14}" '
             f'class="bandlab" text-anchor="middle">HER BAND &#183; {BAND[0]}&#8211;{BAND[1]} CM</text>')

    for kg in range(55, 86, 5):                                    # horizontal grid + axes
        o.append(f'<line x1="{L}" y1="{py(kg):.1f}" x2="{w - R}" y2="{py(kg):.1f}" class="grid"/>')
        o.append(f'<text x="{L - 10}" y="{py(kg) + 4:.1f}" class="tick" text-anchor="end">{kg}</text>')
        o.append(f'<text x="{w - R + 10}" y="{py(kg) + 4:.1f}" class="tick tick2">'
                 f'{lb(kg):.0f}</text>')
    for cm in range(165, 196, 5):
        o.append(f'<line x1="{px(cm):.1f}" y1="{T}" x2="{px(cm):.1f}" y2="{h - B}" class="grid"/>')
        o.append(f'<text x="{px(cm):.1f}" y="{h - B + 20}" class="tick" text-anchor="middle">{cm}</text>')
        o.append(f'<text x="{px(cm):.1f}" y="{h - B + 36}" class="tick tick2" '
                 f'text-anchor="middle">{ftin(cm)}</text>')
    o.append(f'<text x="{L - 10}" y="{T - 10}" class="axlab" text-anchor="end">KG</text>')
    o.append(f'<text x="{w - R + 10}" y="{T - 10}" class="axlab">LB</text>')
    o.append(f'<text x="{(L + w - R) / 2:.0f}" y="{h - B + 58}" class="axlab" '
             f'text-anchor="middle">HEIGHT</text>')

    b, a, r = fit([p["cm"] for p in sen], [p["kg"] for p in sen])
    lo, hi = min(p["cm"] for p in sen), max(p["cm"] for p in sen)
    o.append(f'<line x1="{px(lo):.1f}" y1="{py(a + b * lo):.1f}" x2="{px(hi):.1f}" '
             f'y2="{py(a + b * hi):.1f}" class="fitline"/>')
    o.append(f'<text x="{px(hi) - 4:.1f}" y="{py(a + b * hi) - 10:.1f}" class="fitlab" '
             f'text-anchor="end">senior fit &#183; r = {r:.2f}</text>')

    for p in yth:
        o.append(f'<circle cx="{px(p["cm"] + jitter(p["id"], 0)):.1f}" '
                 f'cy="{py(p["kg"] + jitter(p["id"], 1)):.1f}" r="4" class="yth">'
                 f'<title>{p["name"]} &#183; {p["noc"]} &#183; {p["cm"]} cm, {p["kg"]} kg '
                 f'({lb(p["kg"]):.0f} lb) &#183; Youth Olympics {p["years"][0]}</title></circle>')
    for p in sen:
        o.append(f'<circle cx="{px(p["cm"] + jitter(p["id"], 0)):.1f}" '
                 f'cy="{py(p["kg"] + jitter(p["id"], 1)):.1f}" r="4" class="sen">'
                 f'<title>{p["name"]} &#183; {p["noc"]} &#183; {p["cm"]} cm, {p["kg"]} kg '
                 f'({lb(p["kg"]):.0f} lb) &#183; {", ".join(str(y) for y in p["years"])}</title></circle>')

    hx, hy = px(HER_CM), py(HER_KG)
    o.append(f'<line x1="{hx:.1f}" y1="{hy - 17:.1f}" x2="{hx:.1f}" y2="{hy + 17:.1f}" class="her"/>')
    o.append(f'<line x1="{hx - 17:.1f}" y1="{hy:.1f}" x2="{hx + 17:.1f}" y2="{hy:.1f}" class="her"/>')
    o.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="5.5" class="herdot"/>')
    # the label goes in the empty tall-and-light corner and points back, so it never has
    # to sit on top of the crowd around her own coordinates
    lx, ly = px(162.6), py(78.4)
    o.append(f'<polyline points="{lx + 6:.1f},{ly + 8:.1f} {lx + 6:.1f},{ly + 18:.1f} '
             f'{hx - 22:.1f},{hy - 12:.1f}" class="leader"/>')
    o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" class="herlab">Haisley</text>')
    o.append(f'<text x="{lx:.1f}" y="{ly + 14:.1f}" class="herlab herlab2">'
             f'5&#8242;9&#8243; &#183; 146 lb</text>')
    o.append("</svg>")
    return "\n".join(o)


def histogram(sen, yth, w=1000, h=420):
    """Back-to-back: senior up, youth down, each normalised to its own group size."""
    L, R, T, B = 82, 66, 54, 54
    lo, hi = 54, 80
    mid = T + (h - T - B) * 0.56                      # senior gets the larger half
    px = lambda kg: L + (kg - lo) / (hi - lo) * (w - L - R)
    bins = list(range(lo, hi, BIN))

    def bucket(g):
        c = {b: 0 for b in bins}
        for p in g:
            b = lo + ((p["kg"] - lo) // BIN) * BIN
            c[max(lo, min(hi - BIN, b))] += 1
        return {b: (n, 100 * n / len(g)) for b, n in c.items()}

    s, y = bucket(sen), bucket(yth)
    top = max(max(v[1] for v in s.values()), max(v[1] for v in y.values()))
    up = (mid - T - 30) / top            # leave a lane above and below for the box strips
    down = (h - B - mid - 30) / top
    bw = (w - L - R) / len(bins) - 3

    o = [f'<svg viewBox="0 0 {w} {h}" class="fig" role="img" '
         f'aria-label="Weight distribution inside the {BAND[0]} to {BAND[1]} cm band">']
    for kg in range(lo, hi + 1, 4):
        o.append(f'<line x1="{px(kg):.1f}" y1="{T}" x2="{px(kg):.1f}" y2="{h - B}" class="grid"/>')
    for b in bins:
        n, sh = s[b]
        if n:
            o.append(f'<rect x="{px(b) + 1.5:.1f}" y="{mid - sh * up:.1f}" width="{bw:.1f}" '
                     f'height="{sh * up:.1f}" class="bsen"><title>{b}&#8211;{b + BIN} kg '
                     f'({lb(b):.0f}&#8211;{lb(b + BIN):.0f} lb): {n} of {len(sen)} senior'
                     f'</title></rect>')
        n, sh = y[b]
        if n:
            o.append(f'<rect x="{px(b) + 1.5:.1f}" y="{mid:.1f}" width="{bw:.1f}" '
                     f'height="{sh * down:.1f}" class="byth"><title>{b}&#8211;{b + BIN} kg '
                     f'({lb(b):.0f}&#8211;{lb(b + BIN):.0f} lb): {n} of {len(yth)} youth'
                     f'</title></rect>')
    o.append(f'<line x1="{L}" y1="{mid:.1f}" x2="{w - R}" y2="{mid:.1f}" class="axis"/>')

    for tag, g, yy, cls in (("SENIOR", sen, T + 13, "bxs"), ("YOUTH", yth, h - B - 13, "bxy")):
        kgs = sorted(p["kg"] for p in g)
        q1, med, q3 = st.quantiles(kgs, n=4)
        o.append(f'<line x1="{px(q1):.1f}" y1="{yy:.1f}" x2="{px(q3):.1f}" y2="{yy:.1f}" '
                 f'class="box {cls}"/>')
        o.append(f'<circle cx="{px(med):.1f}" cy="{yy:.1f}" r="4" class="{cls} med"/>')
        o.append(f'<text x="{px(q3) + 12:.1f}" y="{yy + 4:.1f}" class="boxlab">'
                 f'{tag} &#183; median {med:.0f} kg ({lb(med):.0f} lb) &#183; '
                 f'middle half {q1:.0f}&#8211;{q3:.0f} kg</text>')

    # the marker gets its own lane above the plot, so the label never lands on a bar
    hx = px(HER_KG)
    o.append(f'<line x1="{hx:.1f}" y1="{T - 26:.0f}" x2="{hx:.1f}" y2="{h - B}" class="herline"/>')
    o.append(f'<text x="{hx:.1f}" y="{T - 32:.0f}" class="herlab" text-anchor="middle">'
             f'Haisley &#183; 146 lb</text>')

    for kg in range(lo, hi + 1, 4):
        o.append(f'<text x="{px(kg):.1f}" y="{h - B + 20}" class="tick" '
                 f'text-anchor="middle">{kg}</text>')
        o.append(f'<text x="{px(kg):.1f}" y="{h - B + 36}" class="tick tick2" '
                 f'text-anchor="middle">{lb(kg):.0f}</text>')
    o.append(f'<text x="{L - 16}" y="{h - B + 20}" class="axlab" text-anchor="end">KG</text>')
    o.append(f'<text x="{L - 16}" y="{h - B + 36}" class="axlab tick2" text-anchor="end">LB</text>')
    o.append("</svg>")
    return "\n".join(o)


# ---------------------------------------------------------------- page

CSS = """
:root {
  --ground:#EFF1EE; --surface:#FAFBFA; --raise:#FFFFFF;
  --ink:#111B19; --body:#2C3A37; --muted:#5F6E6A; --faint:#8B9995;
  --line:#D5DCD9; --hair:#E4E9E7; --wash:#EAEDEB;
  --accent:#0B6E68; --accent-soft:#D9E7E5; --gold:#9A6B12; --gold-soft:#F3E4C4;
  --her:#B02A4A; --her-soft:#F6DEE3; --bandfill:#E3E9E6;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#0B1211; --surface:#121B19; --raise:#182322;
    --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
    --line:#243330; --hair:#1C2827; --wash:#161F1E;
    --accent:#57C3B6; --accent-soft:#123733; --gold:#DCA84A; --gold-soft:#382B12;
    --her:#F2708C; --her-soft:#3A1420; --bandfill:#16211F;
  }
}
:root[data-theme="dark"] {
  --ground:#0B1211; --surface:#121B19; --raise:#182322;
  --ink:#E9EFEC; --body:#C6D2CE; --muted:#93A29E; --faint:#6E7D79;
  --line:#243330; --hair:#1C2827; --wash:#161F1E;
  --accent:#57C3B6; --accent-soft:#123733; --gold:#DCA84A; --gold-soft:#382B12;
  --her:#F2708C; --her-soft:#3A1420; --bandfill:#16211F;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--ground); color:var(--body);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; font-size:15px;
  line-height:1.6; -webkit-font-smoothing:antialiased; }
.wrap { max-width:1180px; margin:0 auto; padding:0 clamp(18px,2.4vw,44px) 70px; }
header { padding:60px 0 32px; border-bottom:1px solid var(--line); }
.eyebrow { font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin:0 0 18px; }
h1 { font-family:"Iowan Old Style",Georgia,"Times New Roman",serif;
  font-size:clamp(32px,5vw,50px); line-height:1.06; letter-spacing:-.02em; color:var(--ink);
  margin:0 0 16px; font-weight:600; text-wrap:balance; max-width:26ch; }
h1 em { font-style:italic; color:var(--accent); }
.standfirst { font-size:17px; color:var(--muted); max-width:66ch; margin:0; }
h2 { font-family:"Iowan Old Style",Georgia,"Times New Roman",serif; font-size:24px;
  color:var(--ink); font-weight:600; margin:0 0 6px; text-wrap:balance; }
h3 { font-family:"Iowan Old Style",Georgia,serif; font-size:17px; color:var(--ink);
  font-weight:600; margin:26px 0 6px; }
.lede { color:var(--muted); margin:0 0 22px; max-width:70ch; font-size:14.5px; }
section { padding:46px 0 0; }
p { max-width:70ch; }
a { color:var(--accent); }

.facts { display:flex; flex-wrap:wrap; margin:30px 0 0;
  border:1px solid var(--line); border-radius:3px; background:var(--surface); overflow:hidden; }
.fact { flex:1 1 150px; padding:14px 18px; border-right:1px solid var(--hair); }
.fact:last-child { border-right:0; }
.fact b { display:block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:23px; color:var(--ink); font-weight:600; font-variant-numeric:tabular-nums; }
.fact b small { font-size:13px; font-weight:500; color:var(--muted); }
.fact span { font-size:11px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint); }

.figbox { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:14px 12px 8px; margin:0 0 12px; overflow-x:auto; }
.fig { width:100%; min-width:660px; height:auto; display:block; }
.grid { stroke:var(--hair); stroke-width:1; }
.axis { stroke:var(--line); stroke-width:1.4; }
.band { fill:var(--bandfill); }
.bandlab { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10px;
  letter-spacing:.1em; fill:var(--faint); }
.tick { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px;
  fill:var(--muted); font-variant-numeric:tabular-nums; }
.tick2 { fill:var(--faint); font-size:10px; }
.axlab { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10px;
  letter-spacing:.11em; fill:var(--faint); }
.sen { fill:var(--accent); fill-opacity:.5; stroke:var(--accent); stroke-opacity:.75;
  stroke-width:.8; }
.yth { fill:none; stroke:var(--gold); stroke-width:1.6; }
.fitline { stroke:var(--ink); stroke-width:1.3; stroke-dasharray:5 4; opacity:.55; }
.fitlab { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10.5px;
  fill:var(--muted); }
.her, .herline { stroke:var(--her); stroke-width:2; }
.leader { fill:none; stroke:var(--her); stroke-width:1; opacity:.55; }
.herline { stroke-dasharray:3 3; }
.herdot { fill:var(--her); }
.herlab { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:12px;
  fill:var(--her); font-weight:650; paint-order:stroke fill; stroke:var(--surface);
  stroke-width:3.5px; stroke-linejoin:round; }
.herlab2 { font-size:10.5px; font-weight:500; opacity:.85; }
.bsen { fill:var(--accent); fill-opacity:.72; }
.byth { fill:var(--gold); fill-opacity:.6; }
.box { stroke-width:3; }
.bxs { stroke:var(--accent); fill:var(--accent); }
.bxy { stroke:var(--gold); fill:var(--gold); }
.boxlab { font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10.5px;
  fill:var(--muted); }
.key { display:flex; flex-wrap:wrap; gap:20px; font-size:12px; color:var(--muted);
  margin:0 0 30px; padding:0 4px; }
.key i { display:inline-block; width:11px; height:11px; border-radius:50%;
  vertical-align:-1px; margin-right:6px; }
.k1 i { background:var(--accent); opacity:.72; }
.k2 i { border:2px solid var(--gold); box-sizing:border-box; }
.k3 i { background:var(--her); }
.cap { font-size:12px; color:var(--faint); max-width:78ch; margin:0 0 4px; }

table { border-collapse:collapse; width:100%; font-size:13.5px; background:var(--surface); }
th, td { padding:6px 10px; border-bottom:1px solid var(--hair); text-align:left;
  vertical-align:top; }
th { font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; color:var(--faint);
  font-weight:650; border-bottom:1px solid var(--line); position:sticky; top:0;
  background:var(--surface); }
td.n, th.n { text-align:right; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-variant-numeric:tabular-nums; }
tr.hers td { background:var(--her-soft); color:var(--ink); font-weight:600; }
.tbox { border:1px solid var(--line); border-radius:3px; overflow:auto; max-height:560px; }
.tbox.narrow { max-width:740px; max-height:none; }
.tbox.mid { max-width:920px; }
td.yr, th.yr { text-align:left; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  font-size:12px; color:var(--muted); white-space:nowrap; }
th.grp, td.grp { width:74px; }
.grp { font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--faint); }
.nm { color:var(--ink); font-weight:550; }

ul { max-width:70ch; padding-left:20px; }
li { margin:0 0 10px; }
.warn { border-left:3px solid var(--her); background:var(--her-soft); padding:14px 18px;
  border-radius:0 3px 3px 0; margin:22px 0 0; max-width:74ch; }
.warn b { color:var(--ink); }
footer { margin-top:56px; padding-top:20px; border-top:1px solid var(--line);
  font-size:12px; color:var(--faint); max-width:80ch; }
"""


def rows(band, tag):
    """(kg, html) so the two fields can be merged into one weight-ordered table."""
    out = []
    for p in band:
        games = ", ".join(str(y) for y in p["years"])
        cm, kg, name, noc = p["cm"], p["kg"], p["name"], p["noc"]
        out.append((kg, f'<tr><td class="nm">{name}</td><td>{noc}</td>'
                        f'<td class="grp">{tag}</td><td class="yr">{games}</td>'
                        f'<td class="n">{cm}</td><td class="n">{ftin(cm)}</td>'
                        f'<td class="n">{kg}</td><td class="n">{lb(kg):.0f}</td>'
                        f'<td class="n">{kg / (cm / 100) ** 2:.1f}</td></tr>'))
    return out


def build():
    d = json.load(open(f"{DATA}/olympedia_bv.json"))
    A = d["athletes"]
    women = [p for p in A if p["sex"] == "Female" and p["cm"] and p["kg"]]
    sen = [p for p in women if p["senior"]]
    yth = [p for p in women if p["youth"] and not p["senior"]]
    bs = [p for p in sen if BAND[0] <= p["cm"] <= BAND[1]]
    by = [p for p in yth if BAND[0] <= p["cm"] <= BAND[1]]
    ks = sorted(p["kg"] for p in bs)
    ky = sorted(p["kg"] for p in by)
    q1, med, q3 = st.quantiles(ks, n=4)
    yq1, ymed, yq3 = st.quantiles(ky, n=4)
    her_pct, her_ypct = pct_of(ks, HER_KG), pct_of(ky, HER_KG)
    b, a, r = fit([p["cm"] for p in sen], [p["kg"] for p in sen])
    pred = a + b * HER_CM
    bmis = sorted(p["kg"] / (p["cm"] / 100) ** 2 for p in bs)
    bq1, bmed, bq3 = st.quantiles(bmis, n=4)
    her_bmi = HER_KG / (HER_CM / 100) ** 2

    traj = []
    for wk, pounds in ((0, 146), (6, 149), (13, 152), (26, 159), (52, 172)):
        k = pounds / LB
        tr = '<tr class="hers">' if wk == 0 else "<tr>"
        when = "today" if wk == 0 else f"+{wk} weeks"
        traj.append(f'{tr}<td>{when}</td>'
                    f'<td class="n">{pounds}</td><td class="n">{k:.1f}</td>'
                    f'<td class="n">{k / (HER_CM / 100) ** 2:.1f}</td>'
                    f'<td class="n">{pct_of(ks, k):.0f}</td>'
                    f'<td class="n">{pct_of(ky, k):.0f}</td></tr>')

    tallest = sorted(sen, key=lambda p: -p["cm"])[0]
    tall_cm, tall_name, tall_noc = tallest["cm"], tallest["name"], tallest["noc"]
    yrs = sorted({y for p in sen for y in p["years"]})
    y0, y1 = yrs[0], yrs[-1]
    mean_cm = st.mean([p["cm"] for p in sen])
    n_women = len([p for p in A if p["sex"] == "Female"])
    no_meas = n_women - len(women)
    her_row = (HER_KG, f'<tr class="hers"><td class="nm">Haisley Flanagan</td>'
                       f'<td>&#8212;</td><td class="grp">&#8212;</td>'
                       f'<td class="yr">&#8212;</td><td class="n">{HER_CM:.0f}</td>'
                       f'<td class="n">{ftin(HER_CM)}</td><td class="n">{HER_KG:.1f}</td>'
                       f'<td class="n">{HER_LB:.0f}</td><td class="n">{her_bmi:.1f}</td></tr>')
    table = "".join(r for _, r in sorted(rows(bs, "Senior") + rows(by, "Youth") + [her_row],
                                        key=lambda t: t[0]))
    year_gain = lb(b * 2.54)
    lo_lb, hi_lb = lb(min(ks)), lb(max(ks))
    a_year = 172

    return f"""<title>Weight at Her Height</title>
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="eyebrow">Olympedia &#183; beach volleyball &#183; {y0}&#8211;{y1}</p>
  <h1>What do Olympic women who are <em>5&#8242;9&#8243;</em> weigh?</h1>
  <p class="standfirst">Every woman in the Olympic beach volleyball record with a published
  height and weight &#8212; {len(women)} of them &#8212; plotted, then narrowed to the
  {len(bs)} senior Olympians standing within three centimetres of Haisley's height.
  At 146 lb she is at their median.</p>
</header>

<div class="facts">
  <div class="fact"><b>{len(bs)}</b><span>Senior women, {BAND[0]}&#8211;{BAND[1]} cm</span></div>
  <div class="fact"><b>{lb(med):.0f} <small>lb</small></b><span>Their median weight</span></div>
  <div class="fact"><b>{lb(q1):.0f}&#8211;{lb(q3):.0f}</b><span>Middle half, lb</span></div>
  <div class="fact"><b>{ord_(her_pct)[:-2]}<small>{ord_(her_pct)[-2:]}</small></b>
    <span>Haisley's percentile</span></div>
  <div class="fact"><b>{lo_lb:.0f}&#8211;{hi_lb:.0f}</b><span>Full range, lb</span></div>
  <div class="fact"><b>{her_bmi:.1f}</b><span>Her BMI &#183; band median {bmed:.1f}</span></div>
</div>

<section>
  <h2>The whole field</h2>
  <p class="lede">Height against weight for every woman who has played Olympic beach
  volleyball and has both numbers published. The shaded column is the
  {BAND[0]}&#8211;{BAND[1]} cm band &#8212; Haisley's height, give or take an inch.</p>
  <div class="figbox">{scatter(sen, yth)}</div>
  <div class="key">
    <span class="k1"><i></i>Senior Olympics, {len(sen)} women</span>
    <span class="k2"><i></i>Youth Olympics (ages 16&#8211;18), {len(yth)} women</span>
    <span class="k3"><i></i>Haisley, 5&#8242;9&#8243; and 146 lb</span>
  </div>
  <p>Weight tracks height closely in this population &#8212; the senior fit is
  <b>{b:.2f} kg per centimetre</b> with a correlation of {r:.2f}, so a player one inch
  taller is expected about {year_gain:.1f} lb heavier. Read straight off that line, the
  expected weight at 5&#8242;9&#8243; is <b>{lb(pred):.0f} lb</b>. Haisley is at
  {HER_LB:.0f}.</p>
  <p>What the chart also shows is how far below the middle of the field her height sits.
  The senior women average {mean_cm:.0f} cm ({ftin(round(mean_cm))}) and run up to
  {tall_cm} cm &#8212; {tall_name} of {tall_noc}. Every point to the right of her band is
  a player she would have to hit over.</p>
</section>

<section>
  <h2>Inside the band</h2>
  <p class="lede">The {len(bs)} senior women and {len(by)} Youth Olympians who stand
  {BAND[0]}&#8211;{BAND[1]} cm, by weight. Bars are share of their own group, because the
  two samples are different sizes; the bar under each axis is the middle half, with the
  median marked.</p>
  <div class="figbox">{histogram(bs, by)}</div>
  <p class="cap">Bins are {BIN} kg wide. Every athlete is counted once, at the weight
  published for her.</p>
  <p>Among senior Olympians her height the median is <b>{lb(med):.0f} lb</b>
  ({med:.0f} kg) and the middle half runs {lb(q1):.0f} to {lb(q3):.0f} lb. Haisley at
  {HER_LB:.0f} lb sits at the <b>{ord_(her_pct)} percentile</b> &#8212; the centre of the
  distribution, not the edge of it. On BMI the same thing holds: her {her_bmi:.1f} against
  a band median of {bmed:.1f} and a middle half of {bq1:.1f} to {bq3:.1f}.</p>
  <p>Against the age-matched group the reading changes. Youth Olympic women her height
  &#8212; 16 to 18 years old, the same age as she is &#8212; have a median of
  <b>{lb(ymed):.0f} lb</b> ({ymed:.0f} kg), and she is at the
  <b>{ord_(her_ypct)} percentile</b> of them. She is already carrying a senior athlete's
  weight at a junior athlete's age.</p>
</section>

<section>
  <h2>Where half a pound a week goes</h2>
  <p class="lede">Haisley's percentile in each group if the current rate of gain
  continues unchanged.</p>
  <div class="tbox narrow"><table>
    <tr><th>From today</th><th class="n">Lb</th><th class="n">Kg</th><th class="n">BMI</th>
    <th class="n">Senior %ile</th><th class="n">Youth %ile</th></tr>
    {"".join(traj)}
  </table></div>
  <p style="margin-top:18px">The heaviest senior Olympian in the band weighed
  {max(ks)} kg ({hi_lb:.0f} lb). A year of gain at half a pound a week reaches
  {a_year} lb, which is past her &#8212; there is no woman in the Olympic record at this
  height carrying that weight. Three months gets to roughly the top of the middle half;
  six months is past it.</p>
  <div class="warn"><b>This is a distribution, not a target.</b> Elite adults are where
  these players ended up after years of adult training, not a weight a 16-year-old should
  be steered toward. What the chart supports is a narrow claim: the gap that a
  weight-gain phase exists to close is closed. It says nothing about how to taper, and
  nothing about body composition &#8212; a scale cannot separate muscle from the rest, and
  that distinction is the whole question. That belongs with a sports dietitian who works
  with adolescent athletes.</div>
</section>

<section>
  <h2>The {len(bs) + len(by)} women in the band</h2>
  <p class="lede">Everyone {BAND[0]}&#8211;{BAND[1]} cm with a published weight, lightest
  first, with Haisley in her place among them.</p>
  <div class="tbox mid"><table>
    <tr><th>Athlete</th><th>NOC</th><th class="grp">Field</th><th class="yr">Games</th>
    <th class="n">Cm</th><th class="n">Ht</th><th class="n">Kg</th><th class="n">Lb</th>
    <th class="n">BMI</th></tr>
    {table}
  </table></div>
</section>

<section>
  <h2>How this was built, and what it cannot tell you</h2>
  <ul>
    <li><b>Source.</b> <a href="{SRC}">Olympedia</a>, scraped edition by edition: the
    beach volleyball tournament at every Summer Games from {y0} to {y1} and at the
    Youth Olympic Games of 2014 and 2018, then each competitor's biography page. That is
    {len(A)} athletes in all, {n_women} of them women, of whom {len(women)} have both a
    height and a weight on file.</li>
    <li><b>The measurements are self-reported and undated.</b> They come from the entry
    form an athlete's federation filed for a given Games and are not revised afterwards,
    so a player who competed in four Olympics carries one number for all four. Expect them
    to be flattering and a little stale. They are consistent enough for a distribution and
    too soft for any single comparison.</li>
    <li><b>Missing data is not random.</b> {no_meas} women in the record have no
    measurements published, weighted toward smaller federations and the earlier Games.
    Nothing here corrects for that.</li>
    <li><b>Olympians are the extreme tail.</b> This is the top of the professional game,
    not the population Haisley competes against now or will at college. It answers "what
    does this body type look like at the very top", not "what should a junior weigh".</li>
    <li><b>The Youth Olympic sample is small.</b> {len(by)} women in the band. It is the
    only age-matched Olympic-grade comparison available, and it should be read as an
    indication rather than a measurement.</li>
    <li><b>Points are jittered.</b> Heights and weights are published as whole numbers, so
    many athletes share a coordinate. Each point is nudged by up to 0.3 units, derived from
    the athlete's own id so it never moves between runs, purely so overlapping players stay
    countable. Every number quoted in the text uses the unjittered values.</li>
  </ul>
</section>

<footer>
  {len(women)} women with published height and weight, from {len(A)} Olympic beach
  volleyball athletes scraped from Olympedia. Haisley's figures &#8212; 5&#8242;9&#8243;
  and 146 lb &#8212; as supplied. Nothing on this page is medical advice.
</footer>
</div>
"""


if __name__ == "__main__":
    open(OUT, "w").write(build())
    print("wrote", OUT)
