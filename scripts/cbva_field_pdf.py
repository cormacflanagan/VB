"""One CBVA division's field and pools, ranked by TruVolley, as a PDF.

  python3 scripts/cbva_field_pdf.py 16788        -> docs/cbva-<tdId>-field.pdf

CBVA seeds on its own ladder, which counts CBVA results and nothing else, so a player
whose record is mostly elsewhere is seeded as though she were a beginner -- and because
the ladder sorts a pair by its *weaker* half, one unrated partner drops the whole team to
the bottom of the draw. This sheet puts the same field in rating order instead, so the
seeding and the strength can be read side by side.

Ratings are Volleyball Life's TruVolley, fetched live. CBVA player ids are a separate
namespace resolved through data/cbva/link.json; anything that does not resolve is shown
with CBVA's own level instead of a number rather than being guessed at.
"""
import datetime, json, os, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concurrent.futures import ThreadPoolExecutor

from cbva_api import trpc
from vbcrawl import get

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
DOCS = os.path.join(HERE, "..", "docs")

INK = colors.HexColor("#111B19")
BODY = colors.HexColor("#2C3A37")
MUTED = colors.HexColor("#5F6E6A")
FAINT = colors.HexColor("#8B9995")
LINE = colors.HexColor("#D5DCD9")
ACCENT = colors.HexColor("#0B6E68")
WASH = colors.HexColor("#EAEDEB")
HILITE = colors.HexColor("#D9E7E5")

# Players whose Volleyball Life id the partnership inference cannot reach but whose home
# town and competition record identify them beyond doubt. Kept here rather than written
# into link.json because the evidence is circumstantial, and the sheet marks them.
SOFT = {64720: 158263, 65042: 124677, 65438: 1918}


def field(tdid, highlight=""):
    """Teams, pools and ratings for one division."""
    link = json.load(open(os.path.join(DATA, "cbva", "link.json")))["link"]
    entries = trpc("tournaments.getTeams", {"tournamentDivisionId": tdid}) or []
    pools = trpc("tournaments.getPools", {"tournamentDivisionId": tdid}) or []
    teams = {}
    for e in entries:
        ps = []
        for p in (e["team"]["players"] or []):
            pr = p["profile"]
            cid = pr["id"]
            v = link.get(str(cid))
            ps.append({"name": f'{pr.get("preferredName") or pr.get("firstName")} '
                               f'{pr.get("lastName")}'.strip(),
                       "level": (pr.get("level") or {}).get("name"),
                       "vid": (v["vblId"] if v else None) or SOFT.get(cid),
                       "soft": cid in SOFT and not v})
        teams[e["id"]] = {"seed": e.get("seed"), "players": ps,
                          "status": e.get("status")}

    want = sorted({p["vid"] for t in teams.values() for p in t["players"] if p["vid"]})
    tv = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i, r in ex.map(lambda i: (i, get(f"/playerprofile/{i}/truvolley") or {}), want):
            tv[i] = r.get("truVolley")
    for t in teams.values():
        for p in t["players"]:
            p["tv"] = tv.get(p["vid"]) if p["vid"] else None
        rated = [p["tv"] for p in t["players"] if p["tv"]]
        t["pair"] = sum(rated) / 2 if len(rated) == 2 else None
        t["soft"] = any(p["soft"] for p in t["players"])
        t["mine"] = any(highlight and highlight.lower() in p["name"].lower()
                        for p in t["players"])
    return teams, pools


def meta(tdid):
    """Venue, date and level, from the local index."""
    for line in open(os.path.join(DATA, "cbva", "divisions.jsonl")):
        d = json.loads(line)
        if d["tdId"] == tdid:
            for tl in open(os.path.join(DATA, "cbva", "tournaments.jsonl")):
                t = json.loads(tl)
                if t["id"] == d["tid"]:
                    return d, t
            return d, {}
    return {}, {}


def cell(p):
    """A player's rating, or CBVA's level when there is no rating to show."""
    if p["tv"]:
        return f'{p["tv"]:.2f}' + ("∗" if p["soft"] else "")
    return f'[{p["level"] or "none"}]'


def pair_cell(t):
    if t["pair"] is None:
        return "—"
    return f'{t["pair"]:.2f}' + ("∗" if t["soft"] else "")


def table(rows, widths, hi=()):
    tb = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), BODY),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (-3, 0), (-1, -1), "RIGHT"),
    ]
    for r in hi:
        style += [("BACKGROUND", (0, r), (-1, r), HILITE),
                  ("FONT", (0, r), (-1, r), "Helvetica-Bold", 8.5),
                  ("TEXTCOLOR", (0, r), (-1, r), INK)]
    tb.setStyle(TableStyle(style))
    return tb


def build(tdid, highlight="Haisley"):
    teams, pools = field(tdid, highlight)
    d, t = meta(tdid)
    out = os.path.join(DOCS, f"cbva-{tdid}-field.pdf")
    doc = SimpleDocTemplate(out, pagesize=LETTER,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=15 * mm, bottomMargin=14 * mm,
                            title=f'CBVA {t.get("venue","")} {d.get("date","")} field',
                            author="volleyball analytics")
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=15,
                        textColor=INK, alignment=TA_LEFT, spaceAfter=2, leading=18)
    EY = ParagraphStyle("EY", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=7.5,
                        textColor=ACCENT, spaceAfter=6, leading=10)
    H2 = ParagraphStyle("H2", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=10.5,
                        textColor=INK, spaceBefore=11, spaceAfter=4, leading=13)
    P = ParagraphStyle("P", parent=ss["Normal"], fontName="Helvetica", fontSize=8.8,
                       textColor=BODY, leading=12.5, spaceAfter=5)
    SM = ParagraphStyle("SM", parent=P, fontSize=7.6, textColor=MUTED, leading=10.5)

    date = d.get("date", "")
    pretty = (datetime.date.fromisoformat(date).strftime("%A %-d %B %Y") if date else "")
    story = [
        Paragraph(f'CBVA &#183; {(d.get("level") or "").upper()} &#183; WOMEN&#8217;S DOUBLES',
                  EY),
        Paragraph(f'{t.get("venue","")}, {t.get("city","")}', H1),
        Paragraph(pretty, P),
    ]

    rated = [x["pair"] for x in teams.values() if x["pair"]]
    best = min(teams.values(), key=lambda x: -(x["pair"] or 0))
    gap = ""
    if best["pair"] and best["seed"]:
        n = sorted((x["pair"] or 0) for x in teams.values())[::-1]
        gap = (f' The strongest pair on this measure, '
               f'{" / ".join(q["name"] for q in best["players"])} at {best["pair"]:.2f}, '
               f'is seeded {best["seed"]} of {len(teams)}.')
    story.append(Paragraph(
        f'{len(teams)} teams in {len(pools)} pools. {len(rated)} of {len(teams)} are rated '
        f'on both players; the field median pair is {st.median(rated):.2f}. Every table '
        f'below is ordered by <b>TruVolley</b>, Volleyball Life&#8217;s rating, which counts '
        f'results everywhere. CBVA&#8217;s own seeding counts CBVA results only and sorts a '
        f'pair by its weaker half, so the two orders differ sharply.' + gap, P))

    # ---- pools
    story.append(Paragraph("The pools", H2))
    order = sorted(pools, key=lambda p: str(p.get("name")))
    for pl in order:
        rows = sorted((teams[e["teamId"]] for e in pl["teams"]),
                      key=lambda x: -(x["pair"] or 0))
        poolseed = {e["teamId"]: e["seed"] for e in pl["teams"]}
        back = {id(x): k for k, x in teams.items()}
        med = [x["pair"] for x in rows if x["pair"]]
        body = [["", "Team", "In pool", "Overall", "Pair", "Players"]]
        hi = []
        for i, x in enumerate(rows, 1):
            key = next(k for k, v in teams.items() if v is x)
            if x["mine"]:
                hi.append(i)
            names = " / ".join(p["name"] for p in x["players"])
            indiv = " / ".join(cell(p) for p in x["players"])
            body.append([str(i), names, str(poolseed.get(key, "")),
                         str(x["seed"] or ""), pair_cell(x), indiv])
        story.append(Paragraph(
            f'<b>Pool {pl.get("name")}</b> &#183; {pl.get("court") or "court tba"} &#183; '
            f'median {st.median(med):.2f}' if med else f'<b>Pool {pl.get("name")}</b>', P))
        story.append(table(body, [16, 190, 38, 38, 40, 96], hi))
        story.append(Spacer(1, 7))

    # ---- the whole field
    story.append(PageBreak())
    story.append(Paragraph("The whole field, strongest first", H2))
    allrows = sorted(teams.values(), key=lambda x: (-(x["pair"] or 0), x["seed"] or 99))
    body = [["", "Team", "CBVA seed", "Pair TruVolley", "Players"]]
    hi = []
    for i, x in enumerate(allrows, 1):
        if x["mine"]:
            hi.append(i)
        body.append([str(i), " / ".join(p["name"] for p in x["players"]),
                     str(x["seed"] or ""), pair_cell(x),
                     " / ".join(cell(p) for p in x["players"])])
    story.append(table(body, [16, 220, 52, 66, 104], hi))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        'A number in brackets is CBVA&#8217;s own level, shown where the player has no '
        'Volleyball Life profile to rate. A star marks a rating taken from a profile '
        'matched by home town rather than by shared results, so treat it as likely rather '
        'than certain. A pair rating is the average of its two players; it says nothing '
        'about how long they have played together.', SM))
    story.append(Paragraph(
        f'Ratings fetched {datetime.date.today().strftime("%-d %B %Y")}. Entries and pools '
        f'from CBVA; ratings from Volleyball Life.', SM))
    doc.build(story)
    return out, teams, pools


if __name__ == "__main__":
    td = int(sys.argv[1]) if len(sys.argv) > 1 else 16788
    who = sys.argv[2] if len(sys.argv) > 2 else "Haisley"
    path, teams, pools = build(td, who)
    print(f"wrote {path}: {len(teams)} teams, {len(pools)} pools")
