"""Head-to-head crosstable and rivalry list.

The crosstable is a round-robin style grid: rows are athletes in rating order, columns
are the same athletes by their rank number, and each cell is the row player's record
against that column player. Colour is diverging — one pole for the row player ahead,
the other for behind, neutral for level and for pairs who have never met.
"""
import html
from collections import defaultdict

VBL = "https://volleyballlife.com"


def esc(s):
    return html.escape(str(s), quote=True)


def summarise(h2h):
    rec = defaultdict(lambda: {"w": 0, "l": 0, "opp": 0})
    for p in h2h["pairs"]:
        rec[p["a"]]["w"] += p["aWins"]; rec[p["a"]]["l"] += p["bWins"]; rec[p["a"]]["opp"] += 1
        rec[p["b"]]["w"] += p["bWins"]; rec[p["b"]]["l"] += p["aWins"]; rec[p["b"]]["opp"] += 1
    return rec


def crosstable(players, h2h):
    order = [p["name"] for p in players]
    rank = {n: i + 1 for i, n in enumerate(order)}
    ids = {p["name"]: p.get("id") for p in players}
    cell = {}
    for p in h2h["pairs"]:
        a, b = p["a"], p["b"]
        if a not in rank or b not in rank:
            continue
        last = p["games"][-1] if p["games"] else None
        cell[(a, b)] = (p["aWins"], p["bWins"], last)
        cell[(b, a)] = (p["bWins"], p["aWins"], last)

    out = ['<div class="ct-wrap"><table class="ct">', "<thead><tr>",
           '<th class="ct-corner">Athlete</th>']
    for n in order:
        out.append(f'<th class="ct-h" title="{esc(n)}"><span>{rank[n]}</span></th>')
    out.append("</tr></thead><tbody>")
    for n in order:
        pid = ids.get(n)
        nm = (f'<a class="lnk" href="{VBL}/player/{pid}" target="_blank" rel="noopener">'
              f'{esc(n)}</a>') if pid else esc(n)
        out.append(f'<tr><th class="ct-row"><span class="ct-rank">{rank[n]}</span>{nm}</th>')
        for m in order:
            if m == n:
                out.append('<td class="ct-c self"></td>')
                continue
            v = cell.get((n, m))
            if not v:
                out.append('<td class="ct-c none"></td>')
                continue
            w, l, last = v
            k = "up" if w > l else "dn" if l > w else "lv"
            tip = f"{n} {w}–{l} {m}"
            if last:
                tip += f" · last met {last['date']} at {last['event']}"
            out.append(f'<td class="ct-c {k}" title="{esc(tip)}">{w}&#8211;{l}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def rivalries(players, h2h, limit=20):
    rank = {p["name"]: i + 1 for i, p in enumerate(players)}
    ids = {p["name"]: p.get("id") for p in players}
    rows = []

    def lnk(n):
        pid = ids.get(n)
        return (f'<a class="lnk" href="{VBL}/player/{pid}" target="_blank" rel="noopener">'
                f'{esc(n)}</a>') if pid else esc(n)

    ranked = sorted(h2h["pairs"],
                    key=lambda p: (-(p["aWins"] + p["bWins"]),
                                   rank.get(p["a"], 99) + rank.get(p["b"], 99)))
    for p in ranked[:limit]:
        n = p["aWins"] + p["bWins"]
        g = p["games"][-1] if p["games"] else None
        score = f'{p["aWins"]}&#8211;{p["bWins"]}'
        lead = "up" if p["aWins"] > p["bWins"] else "dn" if p["bWins"] > p["aWins"] else "lv"
        last = "&#8212;"
        if g:
            # g["sets"] are from p["a"]'s side; show them from the winner's side
            pts = g["sets"] if g["won"] else [(b, a) for a, b in g["sets"]]
            sets = ", ".join(f"{x}&#8211;{y}" for x, y in pts) or "&#8212;"
            who = p["a"] if g["won"] else p["b"]
            last = (f'<span class="ct-last">{esc(g["date"])} &#183; {esc(g["event"][:38])}'
                    f'<br><span class="dv">{esc(who)} won {sets}</span></span>')
        rows.append(f"""      <tr>
        <td class="num dim">{n}</td>
        <td>{lnk(p['a'])} <span class="dv">#{rank.get(p['a'],'')}</span></td>
        <td class="num sc {lead}">{score}</td>
        <td>{lnk(p['b'])} <span class="dv">#{rank.get(p['b'],'')}</span></td>
        <td>{last}</td>
      </tr>""")
    return "\n".join(rows)


CT_CSS = """
.ct-wrap { border:1px solid var(--line); border-radius:3px; background:var(--surface);
  overflow:auto; max-height:78vh; }
.ct { border-collapse:separate; border-spacing:0; }
.ct th, .ct td { border-bottom:1px solid var(--hair); border-right:1px solid var(--hair); }
.ct-corner { position:sticky; left:0; top:0; z-index:4; background:var(--wash);
  width:210px; min-width:210px; padding:10px 14px; text-align:left; vertical-align:bottom;
  font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--faint);
  font-weight:650; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }
.ct-h { position:sticky; top:0; z-index:2; background:var(--wash); width:40px; min-width:40px;
  padding:8px 2px; border-bottom:1px solid var(--line);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:10.5px;
  color:var(--muted); font-weight:650; font-variant-numeric:tabular-nums; }
.ct-row { position:sticky; left:0; z-index:3; background:var(--surface); width:210px;
  min-width:210px; padding:7px 12px 7px 10px; text-align:left; font-weight:500;
  font-size:12.5px; color:var(--ink); white-space:nowrap;
  border-right:1px solid var(--line); }
.ct-rank { display:inline-block; min-width:22px; color:var(--faint);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11px; }
.ct-c { width:40px; min-width:40px; text-align:center; padding:6px 2px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11.5px;
  font-variant-numeric:tabular-nums; color:var(--body); }
.ct-c.up { background:var(--accent-soft); color:var(--accent); font-weight:650; }
.ct-c.dn { background:var(--gold-soft); color:var(--gold); font-weight:650; }
.ct-c.lv { background:color-mix(in srgb,var(--wash) 70%,transparent); }
.ct-c.none { background:transparent; }
.ct-c.self { background:repeating-linear-gradient(-45deg,transparent,transparent 4px,
  var(--hair) 4px,var(--hair) 5px); }
.ct tbody tr:hover .ct-c { box-shadow:inset 0 0 0 99px rgba(127,127,127,.05); }
.sc.up { color:var(--accent); font-weight:700; }
.sc.dn { color:var(--gold); font-weight:700; }
.sc.lv { color:var(--muted); font-weight:700; }
.ct-last { font-size:12px; color:var(--muted); }
"""
