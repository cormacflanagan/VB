"""The 2027 planning page as a workbook.

  python3 scripts/plan2027_xlsx.py     ->  docs/plan-2027.xlsx

Same numbers as docs/plan-2027.html, not a second computation of them: the page is built
first and hands back everything it drew, so the two can never disagree. Five sheets --
the calendar, the weekend pairs, the pro-am circuit, the Beach Pro Tour tiers, and a key
that holds her ratings and the definitions the rest of the book refers to by cell.

Anything derived inside the book is a formula rather than a pasted result, so editing her
rating on the Key sheet moves the contested shares and the match odds with it.
"""
import datetime, html, os, re, sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan2027_page as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "plan-2027.xlsx")

FONT = "Arial"
INK = "1A1A1A"
ACCENT = "0F6B5C"
RULE = Side(style="thin", color="D8D6D1")


def txt(s):
    """Page strings carry HTML entities; a cell wants the character."""
    return html.unescape(re.sub(r"<[^>]+>", "", str(s))).strip()


def head(ws, row, labels, widths):
    assert len(labels) == len(widths), (len(labels), len(widths))
    for i, (lab, w) in enumerate(zip(labels, widths), 1):
        c = ws.cell(row=row, column=i, value=lab)
        c.font = Font(name=FONT, bold=True, size=10, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=ACCENT)
        c.alignment = Alignment(vertical="center", wrap_text=True)
        c.border = Border(bottom=RULE)
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[row].height = 30


def body(ws, first, last, ncol):
    for r in range(first, last + 1):
        for c in range(1, ncol + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = Font(name=FONT, size=10, color=INK)
            cell.border = Border(bottom=RULE)
            cell.alignment = Alignment(vertical="center")


def table(ws, name, first, last, ncol):
    ref = f"A{first}:{get_column_letter(ncol)}{last}"
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(t)
    ws.freeze_panes = ws.cell(row=first + 1, column=1)


def note(ws, row, text, col=1):
    c = ws.cell(row=row, column=col, value=text)
    c.font = Font(name=FONT, size=9, italic=True, color="6B6964")
    c.alignment = Alignment(vertical="top", wrap_text=True)
    return c


def calendar_sheet(wb, D):
    ws = wb.create_sheet("Calendar")
    cols = ["Date", "Date is", "Days", "Event", "Venue", "State", "Draw", "Kind",
            "Her band", "Field median", "Above her", "Sets", "Contested",
            "Contested share", "Weekend pair", "Link"]
    head(ws, 1, cols, [13, 10, 6, 44, 34, 7, 7, 15, 9, 11, 10, 7, 10, 14, 15, 46])
    r = 2
    for it in D["items"]:
        when = it.get("when")
        pair = next((d for d in D["doubles"] if it in (d["a"], d["b"])), None)
        ws.cell(row=r, column=1,
                value=datetime.date.fromisoformat(when) if when
                else (it.get("proj") or ""))
        ws.cell(row=r, column=2,
                value="posted" if it.get("conf") else
                      ("projected" if not when else "estimated"))
        ws.cell(row=r, column=3, value=it.get("days"))
        ws.cell(row=r, column=4, value=txt(it["name"]))
        ws.cell(row=r, column=5, value=txt(it["place"]))
        ws.cell(row=r, column=6, value=it["state"])
        ws.cell(row=r, column=7, value=it["div"])
        ws.cell(row=r, column=8, value=P.TIERS[it["tier"]][1])
        ws.cell(row=r, column=9, value="yes" if it.get("own") else "")
        ws.cell(row=r, column=10, value=it.get("med"))
        ws.cell(row=r, column=11,
                value=None if it.get("above") is None else round(it["above"]))
        ws.cell(row=r, column=12, value=it.get("sets"))
        ws.cell(row=r, column=13, value=it.get("con"))
        # A share rather than a second number: it is what the two columns beside it mean.
        ws.cell(row=r, column=14, value=f'=IF(N(L{r})=0,"",M{r}/L{r})')
        ws.cell(row=r, column=15,
                value=f'{pair["sat"]:%-d %b} + {pair["sun"]:%-d %b}' if pair else "")
        ws.cell(row=r, column=16, value=link_of(it))
        r += 1
    last = r - 1
    body(ws, 2, last, len(cols))
    for row in ws.iter_rows(min_row=2, max_row=last):
        row[0].number_format = "ddd d mmm yyyy"
        for i in (9, 11, 12):
            row[i].number_format = "0.00" if i == 9 else "0.0"
        row[13].number_format = "0%"
        row[15].font = Font(name=FONT, size=9, color="0B6CB5", underline="single")
        for i in (2, 9, 10, 11, 12, 13):
            row[i].alignment = Alignment(horizontal="right", vertical="center")
    table(ws, "Calendar2027", 1, last, len(cols))
    note(ws, last + 2,
         "Date: a posted date is the organiser's; an estimated date is last year's edition "
         "moved into 2027; a projected date is a CBVA slot placed by its own history "
         "(exact 45% of the time, within a week 91%) -- the page shows those as a month "
         "rather than a day, because the day is a projection. Days is how long her own draw runs, "
         "counted from the dates her division actually played at the most recent edition, "
         "not how long the event around it runs. Field median, above her, sets and "
         "contested all describe that most recent edition, not the 2027 one.")
    ws.merge_cells(start_row=last + 2, start_column=1, end_row=last + 4, end_column=8)
    return last


def pairs_sheet(wb, D):
    ws = wb.create_sheet("Weekend pairs")
    cols = ["Saturday", "Saturday event", "Saturday venue", "Sunday", "Sunday event",
            "Sunday venue", "Miles", "Minutes", "Sat contested", "Sun contested",
            "Weekend total", "Dates"]
    head(ws, 1, cols, [11, 38, 30, 11, 38, 30, 7, 8, 12, 12, 12, 24])
    r = 2
    for d in D["doubles"]:
        a, b = d["a"], d["b"]
        ws.cell(row=r, column=1, value=d["sat"])
        ws.cell(row=r, column=2, value=txt(a["name"]))
        ws.cell(row=r, column=3, value=txt(a["place"]))
        ws.cell(row=r, column=4, value=d["sun"])
        ws.cell(row=r, column=5, value=txt(b["name"]))
        ws.cell(row=r, column=6, value=txt(b["place"]))
        ws.cell(row=r, column=7, value=d["leg"][0] if d["leg"] else None)
        ws.cell(row=r, column=8, value=d["leg"][1] if d["leg"] else None)
        ws.cell(row=r, column=9, value=a.get("con"))
        ws.cell(row=r, column=10, value=b.get("con"))
        ws.cell(row=r, column=11, value=f"=SUM(I{r}:J{r})")
        ws.cell(row=r, column=12,
                value="Both posted" if d["firm"] == 2 else
                      "One posted, one projected" if d["firm"] == 1 else "Both projected")
        r += 1
    last = r - 1
    body(ws, 2, last, len(cols))
    for row in ws.iter_rows(min_row=2, max_row=last):
        row[0].number_format = row[3].number_format = "ddd d mmm yyyy"
        for i in (8, 9, 10):
            row[i].number_format = "0.0"
    table(ws, "WeekendPairs", 1, last, len(cols))
    note(ws, last + 2,
         "Two one-day draws on the two days of one weekend, within reach of one hotel. A "
         "weekend total with a blank beside it is a floor: the corpus carries no bracket "
         "for the Kauai Bikini Open or the Marine Open, so their sets are unknown rather "
         "than zero. Miles and minutes are approximate road distances read off the map.")
    ws.merge_cells(start_row=last + 2, start_column=1, end_row=last + 4, end_column=6)


def proam_sheet(wb, D):
    ws = wb.create_sheet("Pro-am circuit")
    cols = ["Date", "Series", "Event", "Venue", "Days", "Teams", "Field median",
            "Above her", "Sets", "Contested", "Contested share", "Rated pairs", "Link"]
    head(ws, 1, cols, [11, 10, 44, 30, 6, 7, 11, 10, 7, 10, 14, 11, 46])
    r = 2
    for x in D["proam"]:
        t = D["stats"].get(x["td"]) or {}
        ws.cell(row=r, column=1, value=datetime.date.fromisoformat(x["date"]))
        ws.cell(row=r, column=2, value=x["label"])
        ws.cell(row=r, column=3, value=txt(x["name"]))
        ws.cell(row=r, column=4, value=txt(x["venue"]))
        ws.cell(row=r, column=5, value=x["days"])
        ws.cell(row=r, column=6, value=x["teams"])
        ws.cell(row=r, column=7, value=t.get("med"))
        ws.cell(row=r, column=8, value=t.get("above"))
        ws.cell(row=r, column=9, value=t.get("sets"))
        ws.cell(row=r, column=10, value=t.get("con"))
        ws.cell(row=r, column=11, value=f'=IF(N(I{r})=0,"",J{r}/I{r})')
        ws.cell(row=r, column=12, value=t.get("peers"))
        ws.cell(row=r, column=13, value=f'{P.VBL}/tournament/{x["tid"]}')
        r += 1
    last = r - 1
    body(ws, 2, last, len(cols))
    for row in ws.iter_rows(min_row=2, max_row=last):
        row[0].number_format = "ddd d mmm yyyy"
        row[6].number_format = "0.00"
        for i in (8, 9):
            row[i].number_format = "0.0"
        row[10].number_format = "0%"
        row[12].font = Font(name=FONT, size=9, color="0B6CB5", underline="single")
    table(ws, "ProAm", 1, last, len(cols))
    note(ws, last + 2,
         "Every Highline or AVP Next women's open draw in California since 2025. Rated "
         "pairs is how many pairs rated within her own band were in that draw, and it is "
         "the sample the sets and contested columns rest on: a figure resting on one or "
         "two pairs is one or two teams' afternoon, not a property of the event. The "
         "medians and the count above her rest on the whole entry list.")
    ws.merge_cells(start_row=last + 2, start_column=1, end_row=last + 4, end_column=7)


def tour_sheet(wb, D):
    ws = wb.create_sheet("Beach Pro Tour")
    cols = ["Tier", "Where", "US entrants rated", "Field median", "Weakest",
            "Below her", "Her match odds"]
    head(ws, 1, cols, [24, 52, 17, 12, 10, 11, 14])
    order = ["Mexico Elite16", "Mexico Challenge", "Elite16, worldwide",
             "Challenge, worldwide", "Futures, the Americas", "Futures, worldwide"]
    where = {
        "Mexico Elite16": "Tepic, Quintana Roo",
        "Mexico Challenge": "Tlaxcala, Nayarit, Yucatan, Veracruz, Guadalajara, La Paz",
        "Elite16, worldwide": "the sixteen-team top tier",
        "Challenge, worldwide": "the tier below it",
        "Futures, the Americas": "Pompano Beach FL, Halifax CAN - never Mexico",
        "Futures, worldwide": "mostly Europe and China",
    }
    r = 2
    for k in order:
        v = D["bpt"].get(k)
        if not v:
            continue
        ws.cell(row=r, column=1, value=k)
        ws.cell(row=r, column=2, value=where[k])
        ws.cell(row=r, column=3, value=v["n"])
        ws.cell(row=r, column=4, value=v["med"])
        ws.cell(row=r, column=5, value=v["lo"])
        ws.cell(row=r, column=6, value=v["under"] / v["n"])
        # The same logistic the page uses, pointed at her pair rating on Key (B5, not her
        # own rating in B4) so the column moves if that changes.
        ws.cell(row=r, column=7, value=f"=1/(1+EXP(D{r}-Key!$B$5))")
        r += 1
    last = r - 1
    body(ws, 2, last, len(cols))
    for row in ws.iter_rows(min_row=2, max_row=last):
        for i in (3, 4):
            row[i].number_format = "0.00"
        row[5].number_format = "0%"
        row[6].number_format = "0%"
    table(ws, "BeachProTour", 1, last, len(cols))
    note(ws, last + 2,
         "The star ratings belonged to the FIVB World Tour, whose last season was 2021; "
         "the Beach Pro Tour replaced it in 2022 with Futures, Challenge and Elite16, of "
         "which Futures is roughly where the old one-star sat. There has never been a "
         "Futures in Mexico. Ratings are the American entrants in each draw, because the "
         "US entry list is the one she would have to be on. Match odds are the logistic "
         "fitted to 7,000 rated CBVA women's matches, applied to her pair rating on Key.")
    ws.merge_cells(start_row=last + 2, start_column=1, end_row=last + 5, end_column=5)


def key_sheet(wb, D, ncal):
    ws = wb.create_sheet("Key", 0)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 15
    ws.column_dimensions["C"].width = 92
    t = ws.cell(row=1, column=1, value="Haisley 2027 · competition options")
    t.font = Font(name=FONT, bold=True, size=15, color=INK)
    ws.cell(row=2, column=1,
            value=f'Built {D["built"]:%-d %B %Y} from the Volleyball Life crawl and '
                  f'CBVA’s tournament database.').font = Font(
        name=FONT, size=10, italic=True, color="6B6964")

    rows = [
        ("Her TruVolley", P.HER, "Her own current rating."),
        ("Her pair rating", P.PAIR,
         "What a team of hers rates: she enters with partners rated 9.1-9.5, so the teams "
         "that outrank her team are the ones averaging above this. Edit this cell and the "
         "match-odds column on Beach Pro Tour moves with it."),
        ("Peer band", f"{P.LO:.2f}–{P.HI:.2f}",
         "The rating range counted as “a pair rated like hers” when measuring "
         "how many sets a draw actually gives."),
        ("Contested", f"within {P.NEAR:.2f}",
         "A set is contested when the opposing pair rates within this of her own. "
         "Everything else is a formality."),
        ("Calendar entries", ncal, "Rows on the Calendar sheet."),
        ("Weekend pairs", len(D["doubles"]),
         "Weekends holding two one-day draws within reach of one hotel."),
        ("Pro-am draws listed", len(D["proam"]),
         "Highline and AVP Next women's opens in California since 2025."),
        ("Players rated", D["tv"],
         "TruVolley ratings held for the entrants behind every field number in the book."),
    ]
    r = 4
    for lab, val, why in rows:
        a = ws.cell(row=r, column=1, value=lab)
        a.font = Font(name=FONT, bold=True, size=10, color=INK)
        b = ws.cell(row=r, column=2, value=val)
        b.font = Font(name=FONT, size=10, color="0000FF" if r in (4, 5) else INK)
        b.alignment = Alignment(horizontal="right")
        if isinstance(val, float):
            b.number_format = "0.00"
        c = ws.cell(row=r, column=3, value=why)
        c.font = Font(name=FONT, size=9, color="4A4844")
        c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 26
        r += 1

    r += 1
    h = ws.cell(row=r, column=1, value="What each kind of date is")
    h.font = Font(name=FONT, bold=True, size=11, color=ACCENT)
    r += 1
    for _, lab, why in D["tiers"].values():
        ws.cell(row=r, column=1, value=lab).font = Font(name=FONT, bold=True, size=10)
        c = ws.cell(row=r, column=3, value=txt(why))
        c.font = Font(name=FONT, size=9, color="4A4844")
        c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 24
        r += 1

    r += 1
    h = ws.cell(row=r, column=1, value="Two age charts, one year apart")
    h.font = Font(name=FONT, bold=True, size=11, color=ACCENT)
    r += 1
    for lab, why in (
        ("USA Volleyball", "NTDP rosters and national-team trials. She is U18 in 2027."),
        ("AVP Juniors, AAU, BVCA",
         "The junior championships, labelled a year younger. She is 17U in 2027, and the "
         "18U draws are playing up."),
        ("p1440 Futures Tour",
         "Runs 16U and 18U only. She ages out of 16U, so 18U is the only option."),
    ):
        ws.cell(row=r, column=1, value=lab).font = Font(name=FONT, bold=True, size=10)
        c = ws.cell(row=r, column=3, value=why)
        c.font = Font(name=FONT, size=9, color="4A4844")
        c.alignment = Alignment(vertical="top", wrap_text=True)
        ws.row_dimensions[r].height = 24
        r += 1

    r += 1
    note(ws, r, "The page this book was built from: "
                "https://cormacflanagan.github.io/VB/docs/plan-2027.html")


def link_of(it):
    if it.get("tid"):
        return f'{P.VBL}/tournament/{it["tid"]}'
    if it.get("cbva"):
        return f'{P.CBVA_URL}/venues/{it["cbva"]}'
    if it.get("was"):
        return f'{P.VBL}/tournament/{it["was"]}'
    return P.SITE.get(it["name"], "")


def main():
    P.build()               # the page computes everything; the book only lays it out
    D = P.DATA_OUT
    wb = Workbook()
    wb.remove(wb.active)
    ncal = calendar_sheet(wb, D)
    pairs_sheet(wb, D)
    proam_sheet(wb, D)
    tour_sheet(wb, D)
    key_sheet(wb, D, ncal - 1)
    wb.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
