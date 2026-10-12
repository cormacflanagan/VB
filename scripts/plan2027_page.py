"""Haisley's 2027 competition options in California and Arizona.

  python3 scripts/plan2027_page.py    ->  docs/plan-2027.html

One chronological planning page. Every draw she could enter in the two states she can
reach, with the field it drew last time and the number of matches it gave, so the calendar
can be built on what each date is actually worth rather than on its name.

Two kinds of row, and the page never blurs them:

  CONFIRMED  the 2027 edition is already posted on Volleyball Life, with its date.
  EXPECTED   the series has run in the same week for two or three years and 2027 is not
             posted yet. The date is the prior edition's, moved to the nearest matching
             weekend, and is marked as an estimate.

Field strength is measured against a pair rating of 9.50 -- hers with the partners she
actually enters with -- and against her own 9.68 for the count of individual players above
her. Ratings are the snapshot in data/opens_tv.json.
"""
import datetime, html, json, os, re, statistics as st, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calendar_page import CSS
from opens_page import (ALL_CA, EXTRA_CA, REGION, PAIR, esc, heat, load, rows as jrows)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
VB = os.path.join(DATA, "vb")
OUT = os.path.join(HERE, "..", "docs", "plan-2027.html")
VBL = "https://volleyballlife.com"
HER = 9.678
HER_BAND = "U18"          # born 2010; in 2027 the USAV chart reads U18 = 2010
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Tiers, worst to best for her. The page sorts nothing by these -- it is a calendar -- but
# they carry the judgement, so each is defined by a number rather than a feeling.
TIERS = {
    "selection": ("t-sel", "Selection", "A national-team or ISF trial. The only rows that "
                                        "can put her on a team."),
    "national": ("t-nat", "National 18U", "A national junior championship: the deepest "
                                          "fields she is age-eligible for, and the longest days."),
    "circuit": ("t-cir", "Circuit 18U", "The p1440 / IBVL / BVNE junior circuit. Regular, "
                                        "shallower, useful for reps and ranking points."),
    "open": ("t-opn", "Women's open", "An adult draw. Harder opponents than a junior "
                                      "circuit date, four matches rather than six."),
    "reach": ("t-rch", "Out of reach", "Professional or qualification-only. A median above "
                                       "10.3 and a median of two matches before the exit."),
}


def vbl_corpus():
    T = {t["id"]: t for t in jrows("tournaments.jsonl", VB)}
    D = {d["tdId"]: d for d in jrows("divisions.jsonl", VB)}
    return T, D


def entrants(tdids):
    """Player ids per division, from both halves of the team corpus."""
    import gzip
    out = defaultdict(set)
    for path, op in ((os.path.join(VB, "teams.jsonl.gz"), gzip.open),
                     (os.path.join(VB, "teams.jsonl"), open)):
        if not os.path.exists(path):
            continue
        with op(path, "rt") as fh:
            for l in fh:
                x = json.loads(l)
                if x["tdId"] in tdids and not x.get("drop"):
                    out[x["tdId"]].update(x["p"])
    return out


def games(tdids):
    import gzip
    per = defaultdict(Counter)
    with gzip.open(os.path.join(VB, "matches.jsonl.gz"), "rt") as fh:
        for l in fh:
            m = json.loads(l)
            if m["tdId"] in tdids:
                for s in ("a", "b"):
                    per[m["tdId"]][tuple(sorted(m[s]))] += 1
    return per


def stats(tdid, ents, gms, tv):
    r = [tv[str(p)]["tv"] for p in ents.get(tdid, ()) if tv.get(str(p), {}).get("tv")]
    g = sorted(gms.get(tdid, {}).values())
    return {"rated": len(r), "med": st.median(r) if r else None,
            "above": sum(1 for z in r if z > HER),
            "games": st.median(g) if g else None}


# The 2027 calendar. `ref` is the most recent comparable edition, which supplies the field
# strength and the match count; `on` is the 2027 date where Volleyball Life already carries
# it, and otherwise the prior edition's date moved into 2027, flagged as an estimate.
#   (date, confirmed?, event, place, state, division, tier, ref tdId)
PLAN = [
    ("2027-01-09", True,  "p1440 1X Ranking Event", "Arizona Athletic Grounds, Phoenix", "AZ", "18U", "circuit", None),
    ("2027-01-10", True,  "IBVL Winter Classic (Girls p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", 97612),
    ("2027-01-16", True,  "Futures Tour 2X: Arizona", "Arizona Athletic Grounds, Phoenix", "AZ", "18U", "circuit", 117699),
    ("2027-01-23", True,  "IBVL Winter Nationals (Girls)", "Hermosa Beach Pier", "CA", "18U", "circuit", 124255),
    ("2027-01-23", False, "USAV U18 Beach National Team Trials", "Manhattan Beach Pier", "CA", "18U", "selection", 125823),
    ("2027-02-06", True,  "Kauai Bikini Open", "North Beach, Santa Monica", "CA", "18U", "circuit", 117945),
    ("2027-02-07", True,  "IBVL Winter Nationals (School Event) &#8212; ISF trial", "Hermosa Beach Pier", "CA", "18U", "selection", 124255),
    ("2027-02-13", True,  "p1440 1X Ranking Event", "Arizona Athletic Grounds, Phoenix", "AZ", "18U", "circuit", None),
    ("2027-02-27", False, "Highline Sponsorship Open ($5K)", "Ocean Park North, Santa Monica", "CA", "Open", "reach", None),
    ("2027-02-27", True,  "Futures Tour 3X: Spring Championships", "California", "CA", "18U", "national", 117695),
    ("2027-03-07", True,  "California IBVL Winter Series Championships (p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", 121642),
    ("2027-03-21", True,  "Marine Open (Girls p1440)", "Manhattan Beach Lifeguard HQ", "CA", "18U", "circuit", 121649),
    ("2027-04-03", True,  "Futures Tour 2X: California", "North Beach, Santa Monica", "CA", "18U", "circuit", None),
    ("2027-04-18", True,  "West Coast Championships (p1440 2X)", "Hermosa Beach Pier", "CA", "18U", "circuit", 121655),
    ("2027-06-05", True,  "Kauai Bikini Open", "North Beach, Santa Monica", "CA", "18U", "circuit", 119863),
    ("2027-06-14", False, "USAV U19 / U21 Worlds Trials &#8212; if the cycle runs", "Hermosa Beach Pier", "CA", "Open", "selection", None),
    ("2027-06-28", False, "BVCA Pairs West Coast Championships", "Newland, Huntington Beach", "CA", "18U", "circuit", 130318),
    ("2027-07-06", False, "BVCA Individual Pairs National Championship", "Hermosa Beach", "CA", "18U", "national", 139559),
    ("2027-07-14", True,  "34th AAU Hermosa Beach National Pairs Championships", "Hermosa Beach Pier", "CA", "18U", "national", 117393),
    ("2027-07-21", False, "AVP Juniors National Championships", "Hermosa Beach Pier", "CA", "18U", "national", 126054),
    ("2027-08-22", False, "Super Girl Pro Invitational", "Oceanside Pier", "CA", "18U", "circuit", 148168),
    ("2027-11-06", False, "AVP Juniors West Coast Championships", "Manhattan Beach", "CA", "18U", "national", 97147),
]

# The CBVA women's open circuit does not publish a year ahead, so it is projected from the
# venues that have run an open in the same month in at least two of the last three seasons.
CBVA_MIN_SEASONS = 2


def cbva_2027(tn, dv, tm, mt, link, tv):
    """The CBVA women's open circuit, projected month by month from the last three seasons."""
    def prate(p):
        e = link.get(str(p))
        return (tv.get(str(e["vblId"])) or {}).get("tv") if e else None

    byvm = defaultdict(list)
    for tdid, d in dv.items():
        if d["gender"] != "female" or d["size"] != 2 or d["date"] < "2023-09-01":
            continue
        if d["level"] not in ("open", "aaa"):
            continue
        t = tn.get(d["tid"]) or {}
        if t.get("city") not in ALL_CA:
            continue
        teams = [x for x in tm.get(tdid, []) if not x.get("withdrawn")]
        per = Counter()
        for m in mt.get(tdid, []):
            for s in ("a", "b"):
                per[tuple(sorted(m[s]))] += 1
        if not teams or not per:
            continue
        r, ab = [], 0
        for x in teams:
            v = [z for z in (prate(p) for p in x["p"]) if z]
            r += v
            if len(v) == 2 and sum(v) / 2 > PAIR:
                ab += 1
        byvm[(t["city"], t["venue"], int(d["date"][5:7]))].append(
            {"yr": d["date"][:4], "teams": len(teams), "r": r, "above": ab,
             "g": [per.get(tuple(sorted(x["p"])), 0) for x in teams]})

    out = []
    for (c, v, m), evs in byvm.items():
        if len({e["yr"] for e in evs}) < CBVA_MIN_SEASONS:
            continue
        r = [z for e in evs for z in e["r"]]
        g = [z for e in evs for z in e["g"] if z]
        out.append({"city": c, "venue": v, "month": m, "n": len(evs),
                    "seasons": len({e["yr"] for e in evs}),
                    "teams": st.mean([e["teams"] for e in evs]),
                    "med": st.median(r) if r else None,
                    "above": st.mean([e["above"] for e in evs]),
                    "players": sum(1 for z in r if z > HER) / len(evs),
                    "games": st.median(g) if g else None})
    out.sort(key=lambda x: (x["month"], -x["above"]))
    return out


EXTRA = """
.t-sel { background:var(--accent); color:#fff; }
.t-nat { background:var(--accent-soft); color:var(--accent); }
.t-cir { background:var(--wash); color:var(--muted); }
.t-opn { background:var(--gold-soft); color:var(--gold); }
.t-rch { background:var(--hair); color:var(--faint); }
.tag { display:inline-block; font-size:10px; letter-spacing:.07em; text-transform:uppercase;
  font-weight:650; padding:2px 7px; border-radius:3px; white-space:nowrap; }
.est { font-style:italic; color:var(--faint); }
.rank { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-variant-numeric:tabular-nums; }
.st { display:inline-block; width:22px; font-size:10.5px; color:var(--faint); font-weight:650; }
.keys { display:grid; gap:10px; grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
  margin:18px 0 0; }
.keyc { border:1px solid var(--line); border-radius:3px; background:var(--surface); padding:12px 14px; }
.keyc p { margin:7px 0 0; font-size:13px; color:var(--muted); max-width:46ch; }
"""


def build():
    tn, dv, tm, mt, link, tv = load()
    T, D = vbl_corpus()
    refs = {r[7] for r in PLAN if r[7]}
    ents, gms = entrants(refs), games(refs)
    S = {i: stats(i, ents, gms, tv) for i in refs}

    months, cur = [], None
    for date, conf, name, place, state, div, tier, ref in PLAN:
        k = date[:7]
        if k != cur:
            cur = k
            months.append((k, []))
        months[-1][1].append((date, conf, name, place, state, div, tier, ref))

    rows = []
    for k, v in months:
        d0 = datetime.date(int(k[:4]), int(k[5:7]), 1)
        rows.append(f'<tr class="mrow"><th colspan="8" scope="rowgroup">{d0.strftime("%B %Y")}'
                    f'<span class="mcount">{len(v)} date{"s" if len(v) != 1 else ""}</span></th></tr>')
        for date, conf, name, place, state, div, tier, ref in v:
            dd = datetime.date(*map(int, date.split("-")))
            cls, label, _ = TIERS[tier]
            s = S.get(ref) or {}
            fld = (f'<span class="rank">{s["above"]}</span>' if s.get("above") is not None
                   else '<span class="dim">&#8212;</span>')
            med = f'{s["med"]:.2f}' if s.get("med") else "&#8212;"
            gm = f'{s["games"]:.0f}' if s.get("games") else "&#8212;"
            when = (f'{dd.strftime("%-d %b")} <span class="dow">{dd.strftime("%a")}</span>'
                    if conf else
                    f'<span class="est">~{dd.strftime("%-d %b")}</span>')
            rows.append(f"""      <tr>
        <td class="dt num nw">{when}</td>
        <td class="evc"><b>{name}</b><span class="dv">{esc(place)}</span></td>
        <td class="bdy"><span class="st">{state}</span></td>
        <td class="rank">{div}</td>
        <td><span class="tag {cls}">{label}</span></td>
        <td class="num rank">{med}</td>
        <td class="num">{fld}</td>
        <td class="num rank">{gm}</td>
      </tr>""")

    cb = cbva_2027(tn, dv, tm, mt, link, tv)
    cbrows = "".join(
        f'<tr><td class="dt num nw">{MON[e["month"]-1]}</td>'
        f'<td class="evc"><b>{esc(e["venue"])}</b><span class="dv">{esc(e["city"])} &#183; '
        f'{esc(REGION.get(e["city"], ""))}</span></td>'
        f'<td class="num rank">{e["n"]}</td>'
        f'<td class="num rank">{e["teams"]:.0f}</td>'
        f'<td class="num rank">{e["med"]:.2f}</td>'
        f'<td class="ht h{heat(e["players"]/22)}">{e["players"]:.0f}</td>'
        f'<td class="num rank">{e["games"]:.0f}</td></tr>' for e in cb)

    nconf = sum(1 for r in PLAN if r[1])
    nsel = sum(1 for r in PLAN if r[6] == "selection")
    nnat = sum(1 for r in PLAN if r[6] == "national")
    keys = "".join(
        f'<div class="keyc"><span class="tag {c}">{lab}</span><p>{txt}</p></div>'
        for c, lab, txt in TIERS.values())
    today = datetime.date.today()

    return f"""<title>Haisley 2027 &#183; California and Arizona</title>
<style>{CSS}{EXTRA}</style>

<div class="wrap">
<header>
  <p class="eyebrow">Beach volleyball &#183; 2027 planning &#183; California and Arizona</p>
  <h1>Every draw worth entering in <em>2027</em></h1>
  <p class="standfirst">The competitions within reach in the two states she can drive or
  fly to in a day, in calendar order, each with the field it drew last time and the number
  of matches it gave. She is {HER_BAND} for the whole of 2027 &#8212; born 2010, and the
  USA Volleyball chart reads U18&#160;=&#160;2010 next year &#8212; so this is the first
  season she is the oldest birth year in her band rather than playing up into it.</p>
  <div class="facts">
    <div class="fact"><b>{len(PLAN)}</b><span>Dates listed</span></div>
    <div class="fact"><b>{nconf}</b><span>Already posted</span></div>
    <div class="fact"><b>{nsel}</b><span>Selection events</span></div>
    <div class="fact"><b>{nnat}</b><span>National 18U</span></div>
    <div class="fact"><b>{len(cb)}</b><span>CBVA open slots</span></div>
    <div class="fact"><b>9.68</b><span>Her TruVolley</span></div>
  </div>
</header>

<section>
  <h2>What counts, and what does not</h2>
  <p class="lede">Five kinds of date, and the difference between them is the whole plan.
  <b>Above her</b> throughout is the number of individual players in that draw rated better
  than her 9.68; <b>median</b> is the field's median TruVolley; <b>games</b> is what a
  typical team played.</p>
  <div class="keys">{keys}</div>
  <p class="lede" style="margin-top:18px">Four things are deliberately absent. The
  <b>recruiting showcases</b> &#8212; GNBV, the Western World Mega Collegiate Showcase
  &#8212; are off the list because she is committed to Santa&#160;Clara, and the field they
  draw backs that up: the 2026 Western World showcase carried nobody above her at a median
  of 7.26. The <b>CIFSS Pairs Championship</b> is a CIF Southern Section event and she is at
  a Central Coast Section school, so it is not open to her. <b>17U and 16U
  draws</b> are not listed: the 2026 AVP Juniors Nationals 17U field carried three players
  above her against the 18U draw's eighteen, and the West Coast 17U carried none. And the
  <b>AVP League qualifiers and NORCECA playoffs</b> appear only as <span class="tag t-rch">
  out of reach</span> &#8212; medians above 11.3 with most of the field over 10.5, and a
  median of one and a half matches before the exit.</p>
</section>

<section>
  <h2>The 2027 calendar</h2>
  <p class="lede">A plain date is already posted on Volleyball Life. An
  <span class="est">~italic date</span> is an estimate: the series has run in the same week
  for two or three seasons and the 2027 edition is not up yet. Field numbers come from the
  most recent edition of that event, not from the 2027 one, which has not happened.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Event</th><th scope="col">St</th>
        <th scope="col">Draw</th><th scope="col">Kind</th>
        <th scope="col" class="num">Median</th><th scope="col" class="num">Above her</th>
        <th scope="col" class="num">Games</th>
      </tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>The CBVA women&#8217;s open circuit</h2>
  <p class="lede">CBVA publishes about seven weeks ahead, so none of 2027 is dated yet. What
  is predictable is the shape: these are the venue-and-month slots that have carried a
  women&#8217;s open in at least {CBVA_MIN_SEASONS} of the last three seasons, with the
  field each has drawn. Expect roughly one of these a fortnight from March to November.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Month</th><th scope="col">Venue</th>
        <th scope="col" class="num">Editions</th><th scope="col" class="num">Teams</th>
        <th scope="col" class="num">Median</th><th scope="col" class="num">Above her</th>
        <th scope="col" class="num">Games</th>
      </tr></thead>
      <tbody>{cbrows}</tbody>
    </table>
  </div>
  <p class="lede" style="margin-top:14px">Santa&#160;Cruz is on this list and should not be
  on her schedule: it carries one or two players above her and she has won the last three.
  The ones worth the drive are Hermosa&#160;Pier, Huntington&#160;Pier, Beach&#160;Blvd and
  Santa&#160;Monica&#160;Pier.</p>
</section>

<section>
  <h2>The NTDP series</h2>
  <p class="lede">Four invitational residential camps a year, not competitions &#8212; no
  draw and no result &#8212; but they are the pool the January trials are selected from, and
  she has been on five consecutive rosters. The winter series runs on the <i>following</i>
  year's bands, so the Winter&#160;2026 camp is her first as a U18 rather than a U17, and it
  lands immediately before the January trials. USA Volleyball dates them a few months out;
  the 2026 winter series is still undated.</p>
</section>

<section class="notes">
  <h2>How to read it, and what it is not</h2>
  <ul>
    <li><b>An estimated date is an estimate.</b> Half of these rows are projected from a
    series that has run in the same week for two or three years. Organisers move dates;
    confirm before booking anything.</li>
    <li><b>The field numbers describe last year's draw, not next year's.</b> They are the
    best guide available to what a date is worth, but the 2027 entry list does not exist
    yet, and a selection event's field in particular turns over every season.</li>
    <li><b>Ratings are current TruVolley</b>, applied to fields up to two years old, so an
    older edition reads slightly stronger than it was. Unrated entrants are excluded from
    the medians, which skews them a little high.</li>
    <li><b>Age bands are birth-year ceilings.</b> U-N in year Y admits anyone born in
    Y&#8722;N+1 or later, so an 18U draw in 2027 admits 2010 and younger. She is the oldest
    year in it. In 2028 she ages out of U18 and that year's U19 becomes the equivalent
    position.</li>
    <li><b>Trials entry is not the same as trials eligibility.</b> Nineteen of the
    twenty-four entrants at the 2026 U18 trials came off the NTDP rosters she was also on,
    and athletes two years younger than her entered, so the route is open &#8212; but the
    published criteria should be confirmed with her NTDP contact rather than inferred from
    who turned up.</li>
    <li><b>Arizona is in and Nevada is not</b>, because the p1440 circuit runs Phoenix dates
    she can reach and because nothing in the record puts a draw worth her time in the other
    neighbouring states. Out-of-region national events &#8212; the Futures Tour stops in
    Florida, Texas and Washington &#8212; are left out for the same reason.</li>
  </ul>
</section>
<footer>
  Confirmed dates from the Volleyball Life tournament crawl; estimated dates projected from
  the 2024&#8211;2026 editions of the same series. Field strength and match counts computed
  from those editions' entry lists and published brackets, with TruVolley for
  {len(tv):,} players retrieved {today.strftime("%-d %B %Y")}. CBVA circuit from CBVA's own
  tournament database.
</footer>
</div>
"""


if __name__ == "__main__":
    open(OUT, "w").write(build())
    print("wrote", OUT)
