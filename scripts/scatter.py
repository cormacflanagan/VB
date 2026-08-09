"""Rating-against-workload scatter, emitted as inline SVG.

One series, so no legend — the title names what is plotted. Identity on the notable
points comes from direct labels, never from colour. The roster table above the chart
is the table view. Hover text rides a <title> child of each mark, so the figure needs
no script.
"""
import html


def _fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return 0.0, my, 0.0
    b = sxy / sxx
    a = my - b * mx
    r = sxy / (sxx ** 0.5 * syy ** 0.5)
    return b, a, r


VBL = "https://volleyballlife.com"


def scatter(players, label_names=(), w=860, h=430):
    pts = [(p["comps"], p["tv"], p["name"], p.get("id"))
           for p in players if p.get("tv") is not None]
    if len(pts) < 3:
        return ""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    b, a, r = _fit(xs, ys)

    ml, mr, mt, mb = 62, 26, 16, 52
    pw, ph = w - ml - mr, h - mt - mb
    x0, x1 = 0, max(xs) + 2
    y0, y1 = min(ys) - 0.12, max(ys) + 0.12
    sx = lambda v: ml + (v - x0) / (x1 - x0) * pw
    sy = lambda v: mt + ph - (v - y0) / (y1 - y0) * ph

    def ticks(lo, hi, n):
        step = (hi - lo) / n
        mag = 10 ** (len(str(int(step))) - 1) if step >= 1 else 0.1
        step = max(mag, round(step / mag) * mag)
        t, v = [], (int(lo / step) + (1 if lo > 0 else 0)) * step
        while v <= hi:
            t.append(round(v, 3))
            v += step
        return t

    out = [f'<svg class="fig" viewBox="0 0 {w} {h}" role="img" width="100%" '
           f'aria-label="Scatter plot of TruVolley rating against number of doubles '
           f'competitions played, with a linear fit.">']
    # gridlines + axes
    for v in ticks(y0, y1, 5):
        y = sy(v)
        out.append(f'<line class="grid" x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}"/>')
        out.append(f'<text class="tick ty" x="{ml-10}" y="{y+4:.1f}">{v:.1f}</text>')
    for v in ticks(x0, x1, 6):
        x = sx(v)
        out.append(f'<line class="grid" x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{mt+ph}"/>')
        out.append(f'<text class="tick tx" x="{x:.1f}" y="{mt+ph+22}">{int(v)}</text>')
    out.append(f'<line class="axis" x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}"/>')
    out.append(f'<line class="axis" x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}"/>')
    out.append(f'<text class="axlab" x="{ml+pw/2:.0f}" y="{h-8}">Doubles competitions played '
               f'(12 months to 9 Aug 2026)</text>')
    out.append(f'<text class="axlab" transform="translate(15,{mt+ph/2:.0f}) rotate(-90)" '
               f'x="0" y="0">TruVolley rating</text>')

    # fit line, drawn under the marks and in ink rather than a second hue
    fx0, fx1 = x0, x1
    out.append(f'<line class="fit" x1="{sx(fx0):.1f}" y1="{sy(a+b*fx0):.1f}" '
               f'x2="{sx(fx1):.1f}" y2="{sy(a+b*fx1):.1f}"/>')
    lxv = x0 + (x1 - x0) * 0.16
    out.append(f'<text class="fitlab" x="{sx(lxv):.0f}" y="{sy(a + b * lxv) - 9:.0f}">'
               f'linear fit</text>')

    labels = set(label_names)
    for cx, cy, nm, pid in sorted(pts, key=lambda p: p[2] in labels):
        X, Y = sx(cx), sy(cy)
        cls = "dot hi" if nm in labels else "dot"
        mark = (f'<circle class="{cls}" cx="{X:.1f}" cy="{Y:.1f}" r="5.5">'
                f'<title>{html.escape(nm)} — TruVolley {cy:.3f}, {cx} competition'
                f'{"" if cx == 1 else "s"}</title></circle>')
        out.append(f'<a href="{VBL}/player/{pid}" target="_blank" rel="noopener">{mark}</a>'
                   if pid else mark)
    # direct labels last so they sit above the marks; nudge any that would collide
    placed = []
    for cx, cy, nm, pid in sorted((p for p in pts if p[2] in labels), key=lambda p: sy(p[1])):
        X, Y = sx(cx), sy(cy)
        anchor = "end" if X > ml + pw * 0.72 else "start"
        dx = -10 if anchor == "end" else 10
        ly = Y + 4
        for px, py in placed:
            if abs(px - X) < 150 and abs(py - ly) < 15:
                ly = py + 15
        placed.append((X, ly))
        lab = (f'<text class="ptlab" text-anchor="{anchor}" x="{X+dx:.1f}" '
               f'y="{ly:.1f}">{html.escape(nm)}</text>')
        out.append(f'<a href="{VBL}/player/{pid}" target="_blank" rel="noopener">{lab}</a>'
                   if pid else lab)
    out.append("</svg>")
    return "".join(out), b, r


FIG_CSS = """
.figwrap { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  padding:18px 20px 10px; overflow-x:auto; }
.fig { display:block; min-width:620px; --mark:#00A385; --fitink:var(--muted); }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .fig { --mark:#00AB87; }
}
:root[data-theme="dark"] .fig { --mark:#00AB87; }
.fig .grid { stroke:var(--hair); stroke-width:1; }
.fig .axis { stroke:var(--line); stroke-width:1; }
.fig .tick { fill:var(--faint); font-size:11px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-variant-numeric:tabular-nums; }
.fig .ty { text-anchor:end; }
.fig .tx { text-anchor:middle; }
.fig .axlab { fill:var(--muted); font-size:11.5px; text-anchor:middle;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; letter-spacing:.02em; }
.fig .fit { stroke:var(--fitink); stroke-width:2; stroke-dasharray:7 5; opacity:.75; }
.fig .fitlab { fill:var(--muted); font-size:11px; text-anchor:middle;
  paint-order:stroke; stroke:var(--surface); stroke-width:3px;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
.fig .dot { fill:var(--mark); stroke:var(--surface); stroke-width:2; }
.fig .dot.hi { fill:var(--surface); stroke:var(--mark); stroke-width:3; }
.fig a { cursor:pointer; }
.fig a:hover .dot { fill:var(--ink); }
.fig a:hover .dot.hi { stroke:var(--ink); }
.fig a:hover .ptlab { fill:var(--mark); }
.fig .ptlab { fill:var(--ink); font-size:11.5px; font-weight:600;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  paint-order:stroke; stroke:var(--surface); stroke-width:3px; }
.figcap { color:var(--faint); font-size:12px; margin:10px 0 0; max-width:76ch; }
"""
