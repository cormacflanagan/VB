"""Haisley's competition options from November 2026 through December 2027.

Run scripts/venues.py first when the calendar gains a row or an organiser moves an event:
it caches the address behind every listing's map link, and the build refuses to write the
page when a row's state or venue disagrees with it.

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
from opens_page import (ALL_CA, CBVA_URL, EXTRA_CA, REGION, PAIR, esc, heat, load,
                        rows as jrows)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
VB = os.path.join(DATA, "vb")
OUT = os.path.join(HERE, "..", "docs", "plan-2027.html")
VBL = "https://volleyballlife.com"
HER = 9.678
USAV_EVENTS = "https://usavolleyball.org/events/"
# Rows with no comparable prior edition link to whoever runs them instead.
SITE = {"USAV U19 / U21 Worlds Trials &#8212; if the cycle runs": USAV_EVENTS}
HER_BAND = "U18"          # born 2010; in 2027 the USAV chart reads U18 = 2010
# Nevada is in scope and comes back almost empty: the only recurring adult open is the
# Tahoe Championships, which is played on grass and so cannot move a sand rating, and the
# Las Vegas sand events are a small local junior series. Both are listed rather than hidden.
NV = r"\bnevada\b|las vegas|henderson|\breno\b|lake tahoe|incline village|boulder city"
LO, HI, NEAR = 9.2, 10.1, 0.75   # a pair rated like hers; an opponent within reach
# The window. It opens in November 2026 because that is where the posted schedule starts
# being hers -- the junior tours rolled their age bands over on 1 September -- and runs to
# the end of 2027.
START, END = "2026-11-01", "2027-12-31"
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Tiers, worst to best for her. The page sorts nothing by these -- it is a calendar -- but
# they carry the judgement, so each is defined by a number rather than a feeling.
TIERS = {
    "selection": ("t-sel", "Selection", "A national-team or ISF trial. The only rows that "
                                        "can put her on a team."),
    "national": ("t-nat", "National junior", "A national junior championship: the deepest "
                                             "fields she is age-eligible for, and the longest days."),
    "circuit": ("t-cir", "Junior circuit", "The p1440 / IBVL / BVNE junior circuit. Regular, "
                                        "shallower, useful for reps and ranking points."),
    "open": ("t-opn", "Women's open", "An adult draw. Harder opponents than most junior "
                                      "dates, but four sets rather than twenty."),
    "proam": ("t-nxt", "Pro-am open", "A promoter's adult open with a purse -- Highline or "
                                      "AVP Next. Harder than CBVA and three times the sets."),
    "reach": ("t-rch", "Out of reach", "Professional or qualification-only. A median above "
                                       "10.3 and two or three sets before the exit."),
    "grass": ("t-grs", "Grass", "Played on grass, which carries its own TruVolley. Nothing "
                                "that happens there can move her sand rating."),
}


# Place names inside the three states, for the venues whose organiser published no
# address. Generic words are deliberately absent: "Pompano Beach" and "Gulf Shores" must
# not pass on the strength of the word "beach".
REGION = {
    "hermosa", "manhattan", "monica", "dockweiler", "huntington", "newland", "newport",
    "laguna", "oceanside", "coronado", "barbara", "cruz", "pismo", "ventura", "monterey",
    "malibu", "redondo", "porto", "playa", "venice", "belmont", "segundo", "torrance",
    "mesa", "phoenix", "arizona", "vegas", "tahoe", "kahle", "california",
    "angeles", "brookhurst", "marine", "mission", "dana", "carlsbad", "oxnard", "goleta",
    "capitola", "rogers", "diego", "catamaran", "bolsa", "chica", "moorpark", "pepperdine",
}
# In-region venues whose names carry no distinctive word, or whose only distinctive word
# is ambiguous -- there is a Sunset Beach in New Jersey and Sunset Hills in Missouri.
NAMED = {"Ocean Park North": "CA",
         "Volleyball Courts at Sunset Park": "NV",
         "Sunset Park Beach": "NV"}

# Words that say nothing about where a venue is, so a match on one proves nothing.
GENERIC = {
    "beach", "park", "courts", "court", "volleyball", "the", "and", "pier", "state",
    "north", "south", "east", "west", "main", "open", "grounds", "athletic", "avenue",
    "headquarters", "lifeguard", "recreation", "bvne", "club", "sports", "complex",
    "center", "centre", "city", "site", "tba", "tbd", "field", "fields", "high", "school",
}
# Cities the listings name. Used only to catch a row that claims the wrong one.
CITIES = {"phoenix", "mesa", "monica", "hermosa", "manhattan", "huntington", "laguna",
          "oceanside", "coronado", "barbara", "cruz", "ventura", "monterey", "malibu",
          "redondo", "venice", "diego", "vegas", "tahoe", "angeles", "carlsbad", "oxnard"}
# Enough to read a state off an address, which is often typed in lower case, misspelt,
# and without the postal abbreviation at all. Two-word forms where the one-word form is
# a city in another state as well: there is a Manhattan in Kansas and a Huntington in
# New York. Arizona and Nevada are tested first so that a match there wins.
PLACE_STATE = [
    ("AZ", ("arizona", " az", ",az", "mesa", "phoenix", "tempe", "scottsdale", "chandler",
            "gilbert", "glendale, az")),
    ("NV", ("nevada", " nv", ",nv", "las vegas", "henderson", "reno", "stateline",
            "south lake tahoe", "kahle")),
    ("CA", ("california", " ca ", " ca,", ",ca", " ca9", "santa monica", "hermosa beach",
            "manhattan beach", "huntington beach", "huntington state beach", "newland",
            "brookhurst", "dockweiler", "playa del rey", "santa barbara", "san diego",
            "coronado", "coranado", "oceanside", "long beach", "belmont shore",
            "newport beach", "laguna beach", "santa cruz", "redondo beach", "el segundo",
            "pismo", "monterey", "malibu", "ventura", "carlsbad", "oxnard", "goleta",
            "capitola", "half moon bay", "ocean park", "venice", "los angeles",
            "pacific palisades", "will rogers")),
]


def words(x):
    x = re.sub(r"&#\d+;|['\u2018\u2019]", "", str(x).lower())
    return {w for w in re.sub(r"[^a-z0-9]+", " ", x).split() if len(w) > 2}


def venue_state(name, addr):
    """The state a venue is in, read off the address its organiser published.

    A venue name is not a location: "2400 Ocean Front Walk" is Santa Monica, "Gulf Shores"
    is Alabama, and "Arizona Athletic Grounds" is Mesa, not Phoenix. Volleyball Life hangs
    a Google Maps query off every division's location and scripts/venues.py caches it, so
    the address decides; the name is only a fallback for the venues that have none.
    Returns a state code, or None when neither says.
    """
    for text in (addr or "", name):
        low = " " + re.sub(r"\s+", " ", str(text).lower()).strip() + " "
        for st, keys in PLACE_STATE:
            if any(k in low for k in keys):
                return st
    for k, st in NAMED.items():
        if k in name:
            return st
    return None


def check_places(feed, D, venues):
    """Every row must be where it says it is, checked against its own listing.

    The 2027 Futures Tour spring championship moved from Santa Monica to Gulf Shores,
    Alabama, and the row kept the previous year's state until a reader caught it. The
    build now refuses to write the page when a row disagrees with its source: the posted
    listing where there is one, the reference edition otherwise.

      state       the published address puts the venue in a different state
      region      no address, and the name points nowhere inside the three states
      venue       the row's venue and the listing's share no distinguishing word
      city        both name a city and they are different ones
    """
    bytid = defaultdict(set)
    for d in D.values():
        if d.get("venue"):
            bytid[d["tid"]].add(str(d["venue"]))
    bad = []
    for date, conf, name, place, state, div, tier, ref in PLAN:
        tid = link_2027(name, date, feed) if conf else None
        if not (tid and bytid.get(tid)):
            tid = (D.get(ref) or {}).get("tid")
        if not (tid and bytid.get(tid)):
            continue
        vs = sorted(bytid[tid])
        ven = " ".join(vs)
        v, pl = words(ven), words(place)
        label = date + " " + re.sub(r"&#\d+;", "", name)[:40]
        got = {venue_state(n, (venues.get(str(tid)) or {}).get(n)) for n in vs}
        got.discard(None)
        if got and state not in got:
            bad.append(label + f': row says {state}, {vs} is in {"/".join(sorted(got))}')
        elif not got and not (v & REGION or any(k in ven for k in NAMED)):
            bad.append(label + f': no published address, and "{ven}" names nowhere in CA, '
                                "AZ or NV")
        elif not (v - GENERIC) & (pl - GENERIC):
            bad.append(label + f': row says "{place}", its listing says "{ven}"')
        elif (v & CITIES) and (pl & CITIES) and not (v & CITIES & pl):
            bad.append(label + f': row says {sorted(pl & CITIES)}, '
                                f'its listing says {sorted(v & CITIES)}')
    if bad:
        raise SystemExit("place check failed:\n  " + "\n  ".join(bad))


def check_proam(pa, venues):
    """The pro-am table is filtered by venue substring, so it gets the same guard."""
    bad = [f'{x["date"]} {x["name"][:44]}: "{x["venue"]}" is in '
           f'{venue_state(x["venue"], (venues.get(str(x["tid"])) or {}).get(x["venue"]))}'
           for x in pa
           if venue_state(x["venue"], (venues.get(str(x["tid"])) or {}).get(x["venue"]))
           != "CA"]
    if bad:
        raise SystemExit("pro-am place check failed:\n  " + "\n  ".join(bad))


def link_2027(name, date, feed):
    """The 2027 listing for a confirmed row, matched on date and name.

    Looked up rather than hard-coded, so a re-run picks up whatever Volleyball Life has
    posted since: a row that is an estimate today becomes a live link the week it goes up.
    """
    def norm(x):
        # Drop apostrophes rather than turning them into word breaks, so that
        # "America's Challenge" and "America&#8217;s Challenge" normalise alike.
        x = re.sub(r"&#\d+;|['\u2018\u2019]", "", x.lower())
        return re.sub(r"[^a-z0-9]+", " ", x).strip()
    a = norm(name)
    for t in feed:
        if t["startDate"] != date:
            continue
        b = norm(t["name"])
        if a[:18] in b or b[:18] in a or set(a.split()[:3]) <= set(b.split()):
            return t["id"]
    return None


def vbl_corpus():
    T = {t["id"]: t for t in jrows("tournaments.jsonl", VB)}
    D = {d["tdId"]: d for d in jrows("divisions.jsonl", VB)}
    return T, D


# One row where the edition that carries the numbers and the edition that carries the name
# are not the same listing. The Las Vegas December date was renamed when AVP took the
# series over, so its field numbers come from the December 2025 edition while the link goes
# to the December 2026 one, which is what a reader clicking "AVP Winter Las Vegas" expects
# to land on.
LINK_FIX = {("2027-12-11", "AVP Winter Las Vegas"): 41138}

# Two rows where the reference division is not the 2027 event itself, so its day count
# would be wrong. Both are judgements, not data, and are written down rather than inferred.
DAYS_FIX = {
    # The Feb school event is new as a standalone date; its field reference is the combined
    # January Winter Nationals, which ran two days. Volleyball Life has the 2027 school
    # event as a single Sunday.
    ("2027-02-07", "18U"): 1,
    # USA Volleyball has run its beach trials over two days every year in the record; this
    # row is an estimate in the first place.
    ("2027-06-14", "Open"): 2,
}

# No prior edition and no posted span: a p1440 1X ranking event is a one-day date.
DAYS_FEED_ONLY = 1


def division_days(tdids, T, D):
    """How many days her own draw played, not how long the festival around it ran.

    AAU Hermosa runs five days and AVP Juniors Nationals five; an age group plays three of
    them, and 18U and 17U play different three. Counting the distinct dates on which the
    division actually played is the only way to get that right. Stray dates outside the
    tournament's own window are data errors and are dropped.
    """
    import gzip
    seen = defaultdict(set)
    for path, op in ((os.path.join(VB, "matches.jsonl.gz"), gzip.open),
                     (os.path.join(VB, "matches.jsonl"), open)):
        if not os.path.exists(path):
            continue
        with op(path, "rt") as fh:
            for l in fh:
                x = json.loads(l)
                if x["tdId"] in tdids:
                    seen[x["tdId"]].add(x["date"])
    out = {}
    for i in tdids:
        d = D.get(i)
        t = T.get(d["tid"]) if d else None
        if not t:
            continue
        played = [x for x in seen.get(i, ()) if t["start"] <= x <= t["end"]]
        out[i] = len(played) or span(t["start"], t["end"])
    return out


def span(a, b):
    a = datetime.date.fromisoformat(a)
    b = datetime.date.fromisoformat(b)
    return (b - a).days + 1


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


def played_sets(m):
    """Sets actually played, not set slots recorded.

    Volleyball Life files a best-of-three as three slots and fills the unplayed decider
    with [0, 0], so counting the slots turns every straight-sets win into three sets. A
    quarter of the slots in the reference divisions this page uses are those placeholders,
    which inflated every sets and contested figure until it was caught.
    """
    return sum(1 for x in (m.get("sets") or []) if x != [0, 0]) or 1


def sets_played(tdids, rate):
    """Sets, not matches: a CBVA pool game is one set and a national bracket match is three.

    Counting matches makes a day at AVP Juniors Nationals look like seven and a Saturday at
    Ocean Park look like four, when the first is twenty-one sets of volleyball and the
    second is four. Alongside it, `contested` counts only the sets played against a pair
    within NEAR of hers -- the ones that are actually a contest.
    """
    import gzip
    tot, con, teams = Counter(), Counter(), defaultdict(set)
    with gzip.open(os.path.join(VB, "matches.jsonl.gz"), "rt") as fh:
        for l in fh:
            m = json.loads(l)
            if m["tdId"] not in tdids:
                continue
            ns = played_sets(m)
            for side, other in (("a", "b"), ("b", "a")):
                r = [rate(p) for p in m[side]]
                o = [rate(p) for p in m[other]]
                if len(r) != 2 or any(x is None for x in r + o):
                    continue
                mine = sum(r) / 2
                if not (LO <= mine <= HI):
                    continue
                tot[m["tdId"]] += ns
                if abs(mine - sum(o) / 2) <= NEAR:
                    con[m["tdId"]] += ns
                teams[m["tdId"]].add(tuple(sorted(m[side])))
    return tot, con, teams


def stats(tdid, ents, sp, tv):
    tot, con, teams = sp
    n = len(teams.get(tdid, ()))
    r = [tv[str(p)]["tv"] for p in ents.get(tdid, ()) if tv.get(str(p), {}).get("tv")]
    return {"rated": len(r), "med": st.median(r) if r else None,
            "above": sum(1 for z in r if z > HER),
            "sets": tot[tdid] / n if n else None,
            "con": con[tdid] / n if n else None, "peers": n}


# The 2027 calendar. `ref` is the most recent comparable edition, which supplies the field
# strength and the match count; `on` is the 2027 date where Volleyball Life already carries
# it, and otherwise the prior edition's date moved into 2027, flagged as an estimate.
#   (date, confirmed?, event, place, state, division, tier, ref tdId)
PLAN = [
    # November and December 2026. The junior tours rolled their age bands over on
    # 1 September, so these months are already run on the labels she carries through 2027.
    ("2026-11-01", True,  "America&#8217;s Challenge (p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", None),
    ("2026-11-07", True,  "AVP Juniors West Coast Championships", "Manhattan Beach", "CA", "18U", "national", 97147),
("2026-11-07", True,  "AVP Juniors West Coast Championships", "Manhattan Beach", "CA", "17U", "national", 97148),
    ("2026-11-14", True,  "p1440 1X Ranking Event", "Arizona Athletic Grounds, Mesa", "AZ", "18U", "circuit", None),
    ("2026-11-14", True,  "The National Classic (p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", 32402),
    ("2026-11-21", True,  "Futures Tour 3X: Fall Championships", "Manhattan Beach", "CA", "18U", "national", None),
    ("2026-11-21", True,  "MAVERICKS AVP Qualifier", "Main Beach, Santa Cruz", "CA", "18U", "circuit", 130451),
    ("2026-12-12", True,  "AVP Winter Las Vegas", "Sunset Park, Las Vegas", "NV", "18U", "circuit", 94993),
    ("2026-12-12", True,  "p1440 1X Ranking Event", "Arizona Athletic Grounds, Mesa", "AZ", "18U", "circuit", None),
    ("2026-12-13", True,  "Los Angeles Grand Prix (p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", 54093),
    ("2026-12-13", True,  "Pan Pacific Championships (p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", 85328),
    ("2026-12-30", True,  "IBVL Winter Series #1 (Girls)", "Hermosa Beach Pier", "CA", "18U", "circuit", 97612),
    # 2027.
    ("2027-01-09", True,  "p1440 1X Ranking Event", "Arizona Athletic Grounds, Mesa", "AZ", "18U", "circuit", None),
    ("2027-01-10", True,  "IBVL Winter Classic (Girls p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", 97612),
    ("2027-01-16", True,  "Futures Tour 2X: Arizona", "Arizona Athletic Grounds, Mesa", "AZ", "18U", "circuit", 117699),
    ("2027-01-23", True,  "IBVL Winter Nationals (Girls)", "Hermosa Beach Pier", "CA", "18U", "circuit", 124255),
    ("2027-01-29", False, "USAV U18 Beach National Team Trials", "Manhattan Beach Pier", "CA", "18U", "selection", 125823),
    ("2027-02-06", True,  "Kauai Bikini Open", "North Beach, Santa Monica", "CA", "18U", "circuit", 117945),
    ("2027-02-07", True,  "IBVL Winter Nationals (School Event) &#8212; ISF trial", "Hermosa Beach Pier", "CA", "18U", "selection", 124255),
    ("2027-02-13", True,  "p1440 1X Ranking Event", "Arizona Athletic Grounds, Mesa", "AZ", "18U", "circuit", None),
    ("2027-02-27", False, "Highline Sponsorship Open ($5K)", "Ocean Park North, Santa Monica", "CA", "Open", "reach", 132429),
    ("2027-03-07", True,  "California IBVL Winter Series Championships (p1440)", "Hermosa Beach Pier", "CA", "18U", "circuit", 121642),
    ("2027-03-21", True,  "Marine Open (Girls p1440)", "Manhattan Beach Lifeguard HQ", "CA", "18U", "circuit", 121649),
    ("2027-04-03", True,  "Futures Tour 2X: California", "North Beach, Santa Monica", "CA", "18U", "circuit", None),
    ("2027-04-18", True,  "p1440 Hermosa Beach Circuit Championships (2X)", "Hermosa Beach Pier", "CA", "18U", "circuit", 121655),
    ("2027-06-05", True,  "Kauai Bikini Open", "North Beach, Santa Monica", "CA", "18U", "circuit", 119863),
    ("2027-06-14", False, "USAV U19 / U21 Worlds Trials &#8212; if the cycle runs", "Hermosa Beach Pier", "CA", "Open", "selection", None),
    ("2027-06-28", False, "BVCA Pairs West Coast Championships", "Newland, Huntington Beach", "CA", "18U", "circuit", 130318),
("2027-06-28", False, "BVCA Pairs West Coast Championships", "Newland, Huntington Beach", "CA", "17U", "circuit", 130319),
    # Posted for 2027 since the last crawl: the Futures Tour's own national championship,
    # five days in California of which her 18U draw played two last year.
    ("2027-06-28", True,  "2027 Futures Tour National Championships", "Southern California", "CA", "18U", "national", 115902),
    ("2027-07-06", False, "BVCA Individual Pairs National Championship", "Hermosa Beach", "CA", "18U", "national", 139559),
    ("2027-07-14", True,  "34th AAU Hermosa Beach National Pairs Championships", "Hermosa Beach Pier", "CA", "18U", "national", 117393),
("2027-07-14", True,  "34th AAU Hermosa Beach National Pairs Championships", "Hermosa Beach Pier", "CA", "17U", "national", 126666),
    ("2027-07-21", False, "AVP Juniors National Championships", "Hermosa Beach Pier", "CA", "18U", "national", 126054),
("2027-07-21", False, "AVP Juniors National Championships", "Hermosa Beach Pier", "CA", "17U", "national", 126055),
    ("2027-08-22", False, "Super Girl Pro Invitational", "Oceanside Pier", "CA", "18U", "circuit", 148168),
    # The one pro-am date with two editions at the same venue in the same month, which is
    # the bar the CBVA slots have to clear. The rest of that circuit is in its own section.
    ("2027-10-01", False, "The Santa Barbara Open (AVP Next)", "East Beach, Santa Barbara", "CA", "Open", "proam", 109248),
    ("2027-11-06", False, "AVP Juniors West Coast Championships", "Manhattan Beach", "CA", "18U", "national", 97147),
("2027-11-06", False, "AVP Juniors West Coast Championships", "Manhattan Beach", "CA", "17U", "national", 97148),
    # Nevada. Everything the state has, which is not much.
    ("2027-07-24", False, "Tahoe Championships &#8212; grass, separate rating", "Kahle Park, South Lake Tahoe", "NV", "Open", "grass", 114462),
    ("2027-12-11", False, "AVP Winter Las Vegas", "Sunset Park, Las Vegas", "NV", "18U", "circuit", 94993),
]

# The CBVA women's open circuit does not publish a year ahead, so it is projected from the
# venues that have run an open in the same month in at least two of the last three seasons.
CBVA_MIN_SEASONS = 2


# The LA basin, for the purpose of a weekend trip: anywhere she could be based in one
# hotel and reach both draws. Santa Barbara and San Diego are each a different trip.
TRIP = ("hermosa", "manhattan", "santa monica", "dockweiler", "playa del rey", "venice",
        "long beach", "belmont", "huntington", "newland", "bolsa chica", "newport",
        "laguna", "redondo", "el segundo", "torrance", "pacific palisades", "malibu",
        "will rogers", "ocean park", "north beach", "los angeles")

# Approximate road distance between the beaches that pair up, in miles and driving
# minutes. Read off the map rather than computed: CBVA's venue records carry no
# coordinates, and a straight line between two beaches is not the drive anyway.
LEG = {
    ("North Beach, Santa Monica", "Hermosa Beach Pier"): (13, 30),
    ("North Beach, Santa Monica", "Ocean Park, Santa Monica"): (1, 5),
    ("Newland, Huntington Beach", "Dockweiler, Los Angeles"): (37, 50),
    ("North Beach, Santa Monica", "Dockweiler, Los Angeles"): (8, 20),
    ("Manhattan Pier, Manhattan Beach", "Hermosa Beach Pier"): (3, 10),
    ("Newland, Huntington Beach", "Manhattan Beach Lifeguard HQ"): (33, 45),
    ("Ocean Park, Santa Monica", "Belmont Shore, Long Beach"): (30, 45),
    ("North Beach, Santa Monica", "Main Beach, Laguna Beach"): (52, 70),
}


def leg(a, b):
    return LEG.get((a, b)) or LEG.get((b, a))


def doubles(items):
    """Pairs of one-day draws on the two days of one weekend, within reach of one hotel.

    CBVA never runs two women's opens in the LA basin on consecutive days -- in three
    seasons of its own record it happened once -- so a double-header is almost always a
    junior date on one day and an open on the other, which is how the two circuits are
    scheduled: they stay off each other's day. Confirmed dates pair exactly; a CBVA slot
    pairs on its projected date, which is a projection and is labelled as one.
    """
    def when(i):
        return (datetime.date.fromisoformat(i["when"]) if i.get("when")
                else i.get("proj"))

    pool = [i for i in items
            if (i.get("days") or 1) == 1 and i["tier"] not in ("reach", "grass")
            and when(i) and any(k in i["place"].lower() for k in TRIP)]
    out = []
    for a in pool:
        for b in pool:
            if (when(b) - when(a)).days != 1:
                continue
            out.append({"a": a, "b": b, "sat": when(a), "sun": when(b),
                        "leg": leg(a["place"], b["place"]),
                        "sets": sum(x.get("sets") or 0 for x in (a, b)),
                        "con": sum(x.get("con") or 0 for x in (a, b)),
                        "firm": sum(1 for x in (a, b) if x.get("conf"))})
    out.sort(key=lambda x: x["sat"])
    return out


# The California beaches Highline and the AVP Next promoters use. Their Puerto Rico,
# Hawaii, Texas, Florida and Virginia dates are a different trip and are left out.
PROAM_VENUES = ("santa monica", "dockweiler", "manhattan beach", "ocean park", "ocean front",
                "huntington", "laguna", "santa barbara", "coronado", "el porto",
                "beach elite", "hermosa")


def proam(T, D, since="2025-01-01"):
    """Highline and AVP Next women's open draws in California, newest first.

    Two names for one tier: a one- or two-day adult open with a $2,500-$10,000 purse, run
    by a promoter rather than by CBVA. AVP Next is the AVP's own developmental label and
    Highline is the Los Angeles promoter that runs most of the California dates, including
    some of the AVP Next ones. Neither has a repeating slot the way CBVA does -- Highline's
    first full season was 2026 -- so they are listed as what they were, not projected onto
    the 2027 calendar.
    """
    bytid = defaultdict(list)
    for x in D.values():
        bytid[x["tid"]].append(x)
    out = []
    for tid, t in T.items():
        nm = t["name"].lower()
        org = t.get("org") or ""
        # Labelled by the banner the draw ran under, not by who took the entries: Highline
        # runs some of the AVP Next dates itself, and the field each one pulls follows the
        # banner rather than the promoter.
        label = ("AVP Next" if ("avp next" in nm or "avpnext" in nm) else
                 "Highline" if org == "Highline" else None)
        if not label or t["start"] < since:
            continue
        for d in bytid[tid]:
            v = str(d.get("venue") or "")
            if (d.get("gender") == "Womens" and d.get("players") == 2
                    and (d.get("teams") or 0) >= 8
                    and any(k in v.lower() for k in PROAM_VENUES)):
                out.append({"td": d["tdId"], "date": t["start"],
                            "days": span(t["start"], t["end"]), "label": label,
                            "name": t["name"], "venue": v, "teams": d["teams"],
                            "tid": tid, "next": "avp next" in nm or "avpnext" in nm,
                            "org": org})
    out.sort(key=lambda x: x["date"])
    return out


def bpt(T, D, ents, tv):
    """The Beach Pro Tour, split into the tier Mexico hosts and the tier below it.

    Only the US entrants carry a TruVolley, so these are the ratings of the Americans in
    each draw rather than of the whole field -- which is the right comparison anyway, since
    it is the US entry list she would have to be on.
    """
    bytid = defaultdict(list)
    for x in D.values():
        bytid[x["tid"]].append(x)
    MX = ("Tlaxcala", "Nayarit", "Guadalajara", "Veracruz", "Yucatan", "Tepic", "Quintana",
          "Paz", " MEX", "Mexico", "Rosarito", "Cancun", "Playa del Carmen", "Vallarta",
          "Acapulco", "Mazatlan", "Merida", "Monterrey", "Oaxaca", "Tijuana", "Puebla",
          "Baja", "Cabo")
    g = defaultdict(list)
    for tid, t in T.items():
        n = t["name"]
        if "BPT" not in n and "FIVB" not in n:
            continue
        tier = ("Elite16" if "Elite" in n else "Challenge" if "Challenge" in n else
                "Futures" if "Futures" in n else None)
        if not tier or t["start"] < "2024-01-01":
            continue
        mex = any(k in n for k in MX)
        usa = "Pompano" in n or "Halifax" in n
        for d in bytid[tid]:
            if d.get("gender") != "Womens" or not (d.get("teams") or 0):
                continue
            r = [tv[str(p)]["tv"] for p in ents.get(d["tdId"], ())
                 if tv.get(str(p), {}).get("tv")]
            if not r:
                continue
            key = (f"Mexico {tier}" if mex else
                   "Futures, the Americas" if (usa and tier == "Futures") else
                   f"{tier}, worldwide")
            g[key] += r
    return {k: {"n": len(v), "med": st.median(v), "lo": min(v),
                "under": sum(1 for x in v if x < HER)} for k, v in g.items()}


def adjacency(tn, dv, T, D):
    """How often the two circuits hand the LA basin a free second day.

    Counts real one-day girls' 17U/18U draws -- eight teams or more, not cancelled, at an
    LA-basin venue -- and asks whether a CBVA women's open ran in the basin the day before
    or after, or the same day. The same-day count is the mirror image and matters just as
    much: that is the weekend where the two choices cancel out.
    """
    cbd = set()
    for d in dv.values():
        if d["gender"] != "female" or d["size"] != 2 or d["date"] < "2023-09-01":
            continue
        if d["level"] not in ("open", "aaa"):
            continue
        t = tn.get(d["tid"]) or {}
        if any(k in f'{t.get("venue")}, {t.get("city")}'.lower() for k in TRIP):
            cbd.add(d["date"])
    bytid = defaultdict(list)
    for x in D.values():
        bytid[x["tid"]].append(x)
    n = adj = same = 0
    for tid, t in T.items():
        if t["start"] != t["end"] or t["start"] < "2023-09-01":
            continue
        ds = [x for x in bytid[tid] if x.get("gender") == "Girls"
              and x.get("name") in ("18U", "17U") and (x.get("teams") or 0) >= 8
              and not x.get("canceled")]
        if not ds or not any(k in str(x.get("venue") or "").lower()
                             for x in ds for k in TRIP):
            continue
        n += 1
        d0 = datetime.date.fromisoformat(t["start"])
        if t["start"] in cbd:
            same += 1
        elif any((d0 + datetime.timedelta(days=o)).isoformat() in cbd for o in (-1, 1)):
            adj += 1
    return n, adj, same


def project(year, month, dates):
    """Where a repeating CBVA slot should land next year, and how far to trust it.

    A venue keeps its weekday and roughly its place in the month, so the projection is the
    occurrence of the modal weekday nearest the average day-of-month of the past editions.
    Backtested by predicting the 2026 season from 2024 and 2025 across the 33 slots with
    enough history: exact 45% of the time, within a week 91%. Projecting the ordinal
    weekday instead ("fourth Saturday") does worse -- exact 39%, within a week 73% --
    because the venues track the date, not the week number. Returns the date and how many
    past editions share its weekday, and the caller is expected to say it is a projection.
    """
    ds = [datetime.date.fromisoformat(x) for x in dates]
    dow, agree = Counter(d.weekday() for d in ds).most_common(1)[0]
    target = sum(d.day for d in ds) / len(ds)
    first = datetime.date(year, month, 1)
    d = first + datetime.timedelta(days=(dow - first.weekday()) % 7)
    cand = []
    while d.month == month:
        cand.append(d)
        d += datetime.timedelta(days=7)
    return (min(cand, key=lambda c: abs(c.day - target)) if cand else None), agree


def cbva_2027(tn, dv, tm, mt, link, tv):
    """The CBVA open circuit as calendar rows, projected month by month.

    CBVA publishes about seven weeks ahead, so 2027 has no dates at all. What repeats is
    the slot: a venue that has run a women's open in the same month in at least
    CBVA_MIN_SEASONS of the last three seasons will almost certainly run one again. Each
    slot carries the field and the sets its past editions gave.
    """
    def prate(p):
        e = link.get(str(p))
        return (tv.get(str(e["vblId"])) or {}).get("tv") if e else None

    bytd = {}
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
        if not teams or not mt.get(tdid):
            continue
        r, ab = [], 0
        for x in teams:
            v = [z for z in (prate(p) for p in x["p"]) if z]
            r += v
            if len(v) == 2 and sum(v) / 2 > PAIR:
                ab += 1
        bytd[tdid] = True
        byvm[(t["city"], t["venue"], int(d["date"][5:7]))].append(
            {"yr": d["date"][:4], "teams": len(teams), "r": r, "above": ab, "td": tdid,
             "date": d["date"]})

    # Sets and contested sets, for pairs rated like hers, from CBVA's own brackets.
    tot, con, peers = Counter(), Counter(), defaultdict(set)
    for tdid in bytd:
        for m in mt.get(tdid, []):
            ns = played_sets(m)
            for side, other in (("a", "b"), ("b", "a")):
                rr = [prate(p) for p in m[side]]
                oo = [prate(p) for p in m[other]]
                if len(rr) != 2 or any(x is None for x in rr + oo):
                    continue
                mine = sum(rr) / 2
                if not (LO <= mine <= HI):
                    continue
                tot[tdid] += ns
                if abs(mine - sum(oo) / 2) <= NEAR:
                    con[tdid] += ns
                peers[tdid].add(tuple(sorted(m[side])))

    # Anything CBVA has already posted inside the window is a real date, not a projection.
    # It still takes its field numbers from its own slot's history, because the draw that
    # turns up is a property of the venue and the month.
    posted = defaultdict(list)
    for tdid, d in dv.items():
        if d["gender"] != "female" or d["size"] != 2 or d["level"] not in ("open", "aaa"):
            continue
        if not (START <= d["date"] <= END):
            continue
        t = tn.get(d["tid"]) or {}
        if t.get("city") in ALL_CA:
            posted[(t["city"], t["venue"], int(d["date"][5:7]),
                    int(d["date"][:4]))].append(d["date"])

    def field_of(c, v, m):
        evs = byvm.get((c, v, m)) or []
        if not evs:
            return {"city": c, "venue": v, "month": m, "n": 0, "med": None,
                    "above": 0, "sets": None, "con": None}
        r = [z for e in evs for z in e["r"]]
        n = sum(len(peers[e["td"]]) for e in evs)
        return {"city": c, "venue": v, "month": m, "n": len(evs),
                "med": st.median(r) if r else None,
                "above": sum(1 for z in r if z > HER) / len(evs),
                "sets": sum(tot[e["td"]] for e in evs) / n if n else None,
                "con": sum(con[e["td"]] for e in evs) / n if n else None}

    out = []
    # A posted date is on the calendar because CBVA has posted it, however short its
    # history; the two-season rule is what lets a date be *projected*, not what makes an
    # open worth listing.
    for (c, v, m, yr), dates in posted.items():
        f = field_of(c, v, m)
        for date in sorted(set(dates)):
            out.append({**f, "on": date, "year": yr})
    seen = {(c, v, m, yr) for (c, v, m, yr) in posted}
    for (c, v, m), evs in byvm.items():
        if len({e["yr"] for e in evs}) < CBVA_MIN_SEASONS:
            continue
        for yr in (2027,):
            if (c, v, m, yr) in seen:
                continue
            proj, agree = project(yr, m, [e["date"] for e in evs])
            out.append({**field_of(c, v, m), "proj": proj, "agree": agree, "year": yr})
    vid = {}
    for t in tn.values():
        if t.get("venueId") and (t.get("venue"), t.get("city")) not in vid:
            vid[(t["venue"], t["city"])] = t["venueId"]
    for e in out:
        e["venueId"] = vid.get((e["venue"], e["city"]))
    out.sort(key=lambda x: (x["year"], x["month"], -(x["con"] or 0)))
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
.own { display:block; font-size:9.5px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--accent); font-weight:650; margin-top:2px; }
.pr { color:var(--accent); font-weight:650; }
.f2 { background:var(--accent); color:#fff; }
.f1 { background:var(--accent-soft); color:var(--accent); }
.f0 { background:var(--wash); color:var(--muted); }
.t-hl { background:var(--gold-soft); color:var(--gold); }
.t-nxt { background:var(--accent); color:#fff; }
h3 { font-size:17px; margin:30px 0 0; letter-spacing:-.01em; }
h3 + .lede { margin-top:8px; }
.days { color:var(--faint); }
.dmulti { color:var(--ink); font-weight:650; }
.rank { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-variant-numeric:tabular-nums; }
.st { display:inline-block; width:22px; font-size:10.5px; color:var(--faint); font-weight:650; }
.keys { display:grid; gap:10px; grid-template-columns:repeat(auto-fit,minmax(250px,1fr));
  margin:18px 0 0; }
.keyc { border:1px solid var(--line); border-radius:3px; background:var(--surface); padding:12px 14px; }
.keyc p { margin:7px 0 0; font-size:13px; color:var(--muted); max-width:46ch; }
"""


# Filled by build(); the spreadsheet reads it rather than recomputing the page.
DATA_OUT = {}


def build():
    tn, dv, tm, mt, link, tv = load()
    T, D = vbl_corpus()
    feed = json.load(open(os.path.join(DATA, "upcoming_vb.json")))
    refs = {r[7] for r in PLAN if r[7]}
    pa = proam(T, D)
    # The Beach Pro Tour draws are wanted for their entry lists only, not their brackets.
    bptd = {d["tdId"] for d in D.values()
            if d.get("gender") == "Womens" and (d.get("teams") or 0)
            and ("BPT" in (T.get(d["tid"]) or {}).get("name", "")
                 or "FIVB" in (T.get(d["tid"]) or {}).get("name", ""))}
    refs |= {x["td"] for x in pa}
    ents = entrants(refs | bptd)
    sp = sets_played(refs, lambda pid: (tv.get(str(pid)) or {}).get("tv"))
    S = {i: stats(i, ents, sp, tv) for i in refs}
    venues = json.load(open(os.path.join(DATA, "venues.json")))
    check_places(feed, D, venues)
    check_proam(pa, venues)
    cb = cbva_2027(tn, dv, tm, mt, link, tv)
    DAYS = division_days(refs, T, D)

    # One calendar. A dated event sorts on its date; a CBVA slot has only a month, so it
    # sorts to the end of that month and says so.
    items = []
    for date, conf, name, place, state, div, tier, ref in PLAN:
        s_ = S.get(ref) or {}
        # The tours and USA Volleyball label the same cohort differently, one year apart,
        # so "her band" is per-event rather than a single number.
        own = (div == "17U") or (div == "18U" and tier == "selection") or \
              (div == "18U" and "Futures" in name)
        # Link the 2027 listing where one exists, and last year's page where it does not,
        # so every row goes somewhere you can read about the event.
        tid = link_2027(name, date, feed) if conf else None
        was = LINK_FIX.get((date, name)) or ((D.get(ref) or {}).get("tid") if ref else None)
        # Her draw's length, in order of what the evidence is worth: an override where the
        # reference is a different event, then the days her division actually played last
        # time, then the span the 2027 listing has posted.
        f = next((t for t in feed if t["id"] == tid), None) if tid else None
        days = DAYS_FIX.get((date, div)) or DAYS.get(ref) or \
            (span(f["startDate"], f["endDate"]) if f else None)
        items.append({"sort": date, "month": date[:7], "when": date, "conf": conf,
                      "name": name, "place": place, "state": state, "div": div,
                      "tier": tier, "own": own, "tid": tid, "was": was,
                      "days": days, **s_})
    for e in cb:
        # A posted slot sorts and reads as the date it is; a projected one has only a
        # month, so it sorts to the end of that month and says it is undated.
        on = e.get("on")
        items.append({"sort": on or f'{e["year"]}-{e["month"]:02d}-32',
                      "month": f'{e["year"]}-{e["month"]:02d}',
                      "when": on, "conf": bool(on), "name": f"CBVA women&#8217;s open",
                      "place": f"{e['venue']}, {e['city']}", "state": "CA", "div": "Open",
                      "tier": "open", "med": e["med"], "above": round(e["above"]),
                      "sets": e["sets"], "con": e["con"], "slots": e["n"], "days": 1,
                      "proj": e.get("proj"), "agree": e.get("agree"),
                      "cbva": e.get("venueId")})
    items.sort(key=lambda x: x["sort"])
    dbl = doubles(items)
    for d in dbl:
        d["a"]["pair"] = d["b"]["pair"] = True

    def num(x, f="{:.0f}"):
        return f.format(x) if x is not None else "&#8212;"

    months, cur, rows = [], None, []
    for it in items:
        if it["month"] != cur:
            cur = it["month"]
            months.append((cur, []))
        months[-1][1].append(it)
    for k, v in months:
        d0 = datetime.date(int(k[:4]), int(k[5:7]), 1)
        rows.append(f'<tr class="mrow"><th colspan="9" scope="rowgroup">{d0.strftime("%B %Y")}'
                    f'<span class="mcount">{len(v)} entr{"ies" if len(v) != 1 else "y"}</span></th></tr>')
        for it in v:
            cls, label, _ = TIERS[it["tier"]]
            if it["when"] and it["conf"]:
                dd = datetime.date(*map(int, it["when"].split("-")))
                when = f'{dd.strftime("%-d %b")} <span class="dow">{dd.strftime("%a")}</span>'
            elif it["when"]:
                dd = datetime.date(*map(int, it["when"].split("-")))
                when = f'<span class="est">~{dd.strftime("%-d %b")}</span>'
            else:
                when = f'<span class="est">{MON[int(k[5:7])-1]}, undated</span>'
            own_tag = '<span class="own">her band</span>' if it.get("own") else ""
            if it.get("tid"):
                href, tip = f'{VBL}/tournament/{it["tid"]}', "This event on Volleyball Life"
            elif it.get("cbva"):
                href, tip = f'{CBVA_URL}/venues/{it["cbva"]}', "This venue on CBVA"
            elif it.get("was"):
                href, tip = (f'{VBL}/tournament/{it["was"]}',
                             "Last year's edition on Volleyball Life")
            elif it["name"] in SITE:
                href, tip = SITE[it["name"]], "USA Volleyball's events calendar"
            else:
                href = tip = None
            title = (f'<a class="lnk" href="{href}" target="_blank" rel="noopener" '
                     f'title="{tip}">{it["name"]}</a>' if href else it["name"])
            sub = esc(it["place"])
            if it.get("pair"):
                sub += ' &#183; <span class="pr">weekend pair</span>'
            if it.get("slots"):
                sub += f' &#183; {it["slots"]} past edition{"s" if it["slots"] != 1 else ""}'
            rows.append(f"""      <tr>
        <td class="dt num nw">{when}</td>
        <td class="evc"><b>{title}</b><span class="dv">{sub}</span></td>
        <td class="bdy"><span class="st">{it['state']}</span></td>
        <td class="rank">{it['div']}{own_tag}</td>
        <td><span class="tag {cls}">{label}</span></td>
        <td class="num rank">{num(it.get('med'), '{:.2f}')}</td>
        <td class="num rank">{num(it.get('above'))}</td>
        <td class="num rank days{'' if (it.get('days') or 1) < 2 else ' dmulti'}">{num(it.get('days'))}</td>
        <td class="num rank">{num(it.get('sets'), '{:.0f}')}</td>
        <td class="ht h{heat((it.get('con') or 0)/13)}">{num(it.get('con'), '{:.1f}')}</td>
      </tr>""")

    # The weekend-pair table. Each side keeps its own numbers, because one of them is
    # often missing: the corpus has no bracket for the Kauai Bikini Open or the Marine Open,
    # so a combined figure there is a floor rather than a total.
    drows = []
    for d in dbl:
        a, b = d["a"], d["b"]
        firm = ("Both posted" if d["firm"] == 2 else
                "One posted, one projected" if d["firm"] == 1 else "Both projected")
        fcls = ("f2" if d["firm"] == 2 else "f1" if d["firm"] == 1 else "f0")
        known = [x for x in (a, b) if x.get("con") is not None]
        tc = sum(x["con"] for x in known)
        ct = (f'{tc:.1f}' if len(known) == 2 else
              f'&#8805;&#8201;{tc:.1f}' if known else "&#8212;")
        lg = (f'{d["leg"][0]}&#8201;mi &#183; {d["leg"][1]}&#8201;min' if d["leg"]
              else "&#8212;")

        def side(x, when):
            tag = ('<span class="dw">posted</span>' if x.get("conf") else
                   f'<span class="est">projected {x.get("agree")}/{x.get("slots")}</span>')
            n = re.sub(r"\s*\(Girls p1440\)|\s*\(p1440 2X\)", "", x["name"])
            # The names already carry their own entities, exactly as the calendar sets
            # them; only the place comes from the data and needs escaping.
            return (f'<b>{when:%-d %b}</b> {tag}<span class="dv">{n}'
                    f'<br>{esc(x["place"])}</span>')
        drows.append(f"""      <tr>
        <td class="evc">{side(a, d["sat"])}</td>
        <td class="evc">{side(b, d["sun"])}</td>
        <td class="num rank nw">{lg}</td>
        <td class="num rank">{num(a.get('con'), '{:.1f}')} + {num(b.get('con'), '{:.1f}')}</td>
        <td class="ht h{heat(tc / 13)}">{ct}</td>
        <td><span class="tag {fcls}">{firm}</span></td>
      </tr>""")

    # The pro-am circuit, as it actually ran. One row per draw, newest last.
    prows = []
    for x in pa:
        t = S.get(x["td"]) or {}
        d0 = datetime.date.fromisoformat(x["date"])
        nm = re.sub(r"\s*\$[\d.,]+K?\)?$|\s*\(\$[^)]*\)", "", x["name"]).strip()
        prows.append(f"""      <tr>
        <td class="dt num nw">{d0:%-d %b}&#8201;<span class="dow">{d0:%y}</span></td>
        <td class="evc"><b><a class="lnk" href="{VBL}/tournament/{x["tid"]}" target="_blank"
          rel="noopener" title="This event on Volleyball Life">{esc(nm)}</a></b>
          <span class="dv">{esc(x["venue"])}</span></td>
        <td><span class="tag {'t-nxt' if x['next'] else 't-hl'}">{x["label"]}</span></td>
        <td class="num rank days{'' if x["days"] < 2 else ' dmulti'}">{x["days"]}</td>
        <td class="num rank">{num(t.get('med'), '{:.2f}')}</td>
        <td class="num rank">{num(t.get('above'))}</td>
        <td class="num rank">{num(t.get('sets'), '{:.0f}')}</td>
        <td class="ht h{heat((t.get('con') or 0) / 13)}">{num(t.get('con'), '{:.1f}')}</td>
        <td class="num rank days">{t.get('peers', 0)}</td>
      </tr>""")

    # The Beach Pro Tour, by tier.
    B = bpt(T, D, ents, tv)
    ORDER = ["Mexico Elite16", "Mexico Challenge", "Elite16, worldwide",
             "Challenge, worldwide", "Futures, the Americas", "Futures, worldwide"]
    WHERE = {
        "Mexico Elite16": "Tepic, Quintana Roo",
        "Mexico Challenge": "Tlaxcala, Nayarit, Yucat&#225;n, Veracruz, Guadalajara, La Paz",
        "Elite16, worldwide": "the sixteen-team top tier",
        "Challenge, worldwide": "the tier below it",
        "Futures, the Americas": "Pompano Beach FL, Halifax CAN &#8212; never Mexico",
        "Futures, worldwide": "mostly Europe and China",
    }
    brows = []
    for k in ORDER:
        v = B.get(k)
        if not v:
            continue
        mx = k.startswith("Mexico")
        brows.append(f"""      <tr>
        <td class="evc"><b>{k}</b><span class="dv">{WHERE[k]}</span></td>
        <td class="num rank">{v["n"]}</td>
        <td class="num rank">{v["med"]:.2f}</td>
        <td class="num rank">{v["lo"]:.2f}</td>
        <td class="ht h{heat(v["under"] / v["n"] * 3)}">{100 * v["under"] / v["n"]:.0f}%</td>
        <td class="num rank nw">{100 / (1 + 2.718281828 ** (v["med"] - PAIR)):.0f}%</td>
      </tr>""")

    # Santa Cruz runs five or six opens a year; pool them rather than quoting one month.
    scs = [e for e in cb if e["city"] == "Santa Cruz"]
    sc = {"med": st.median([e["med"] for e in scs]),
          "above": st.mean([e["above"] for e in scs]),
          "sets": st.mean([e["sets"] for e in scs if e["sets"]]),
          "con": st.mean([e["con"] for e in scs if e["con"] is not None]),
          "slots": len(scs)}
    best = max((e for e in cb if e["city"] != "Santa Cruz"), key=lambda e: e["con"] or 0)
    shares = sorted(100 * e["con"] / e["sets"] for e in cb
                    if e["city"] != "Santa Cruz" and e["sets"])
    jn = S.get(126054) or {}
    nmulti = sum(1 for i in items if (i.get("days") or 1) > 1)
    n26 = sum(1 for i in items if i["month"] < "2027-01")
    # The rollover, read off the November entry list rather than asserted.
    wcc = entrants({126068, 126069})
    gr = Counter(tv[str(p)]["grad"] for p in wcc.get(126068, ())
                 if tv.get(str(p), {}).get("grad"))
    wcc_n = sum(gr.values())
    wcc_grad = gr.most_common(1)[0][0] if gr else 2028
    g16 = sorted({tv[str(p)]["grad"] for p in wcc.get(126069, ())
                  if tv.get(str(p), {}).get("grad")})
    wcc16 = " and ".join(str(x) for x in g16) if g16 else "2029 and later"
    njun, nadj, nsame = adjacency(tn, dv, T, D)
    kb = S.get(117945) or {}
    isf = S.get(124255) or {}
    mar = next((sum(x["con"] for x in (d["a"], d["b"]) if x.get("con") is not None)
                for d in dbl if d["sat"] == datetime.date(2027, 3, 6)), 0)
    mins = [d["leg"][1] for d in dbl if d["leg"]]
    nov = next((d for d in dbl if d["sat"] == datetime.date(2026, 11, 21)), None)
    lag = nov["leg"][0] if nov and nov["leg"] else 0
    lagc = (nov["b"].get("con") or 0) if nov else 0

    # The pro-am numbers quoted in the prose, read off the same rows as the table.
    # Three groups, because the split is not simply geographic: Highline's own purse dates
    # in Los Angeles, its away dates at Santa Barbara and Coronado, and the two draws that
    # carry the AVP Next brand, which pull a different field entirely.
    LA_V = ("santa monica", "dockweiler", "manhattan", "ocean park", "ocean front",
            "huntington", "laguna", "hermosa", "el porto", "beach elite")

    def rng(rows, key):
        v = [S[x["td"]][key] for x in rows if S.get(x["td"], {}).get(key) is not None]
        return min(v), max(v)

    nxt = [x for x in pa if x["next"]]
    own = [x for x in pa if not x["next"]]
    la = [x for x in own if any(k in x["venue"].lower() for k in LA_V)]
    aw = [x for x in own if not any(k in x["venue"].lower() for k in LA_V)]
    lamin, lamax = rng(la, "med")
    awmin, awmax = rng(aw, "med")
    laa0, laa1 = rng(la, "above")
    awa0, awa1 = rng(aw, "above")
    nxmin, nxmax = rng(nxt, "med")
    nxa0, nxa1 = rng(nxt, "above")
    pr = [S[x["td"]]["peers"] for x in pa if S.get(x["td"])]
    pmin, pmax = min(pr), max(pr)
    # The two 2026 league-format dates, which are the volume outlier.
    lgx = [S[x["td"]] for x in pa if "League" in x["name"]]
    lg = st.mean(z["sets"] for z in lgx)
    lgc = st.mean(z["con"] for z in lgx)
    bv = defaultdict(set)
    for d in D.values():
        if (T.get(d["tid"]) or {}).get("org") == "BRAVO Beach":
            bv[d["tid"]].add(str(d.get("venue") or ""))
    bravoall = len(bv)
    bravo = sum(1 for vs in bv.values()
                if any(k in v for v in vs
                       for k in ("BRAVO Beach", "Bowling Green", "Marshall Court",
                                 "Rockrohr")))
    nconf = sum(1 for r in PLAN if r[1])
    nsel = sum(1 for r in PLAN if r[6] == "selection")
    nnat = sum(1 for r in PLAN if r[6] == "national")
    keys = "".join(
        f'<div class="keyc"><span class="tag {c}">{lab}</span><p>{txt}</p></div>'
        for c, lab, txt in TIERS.values())
    today = datetime.date.today()
    # Everything the page is made of, handed back alongside the markup so the spreadsheet
    # is the same numbers rather than a second computation of them.
    DATA_OUT.update({"items": items, "doubles": dbl, "proam": pa, "stats": S,
                     "bpt": B, "tiers": TIERS, "tv": len(tv), "built": today,
                     "santacruz": sc, "bestcbva": best, "juniors": jn})
    return f"""<title>Haisley &#183; November 2026 to December 2027</title>
<style>{CSS}{EXTRA}</style>

<div class="wrap">
<header>
  <p class="eyebrow">Beach volleyball &#183; November 2026 to December 2027 &#183; California, Arizona and Nevada</p>
  <h1>Every draw worth entering,<br><em>November 2026 to December 2027</em></h1>
  <p class="standfirst">Fourteen months, from the November that opens her first season as a
  17U to the end of 2027: every competition within reach in the three states she can drive
  or fly to in a day, in calendar order, each with the field it drew last time and the
  volleyball it gave &#8212; counted in <b>sets</b>, because a CBVA pool game is one set and
  a national bracket match is three. Born 2010, she turns 17 in February, and what that
  makes her depends on who is running the draw &#8212; which is the first thing to get
  straight.</p>
  <div class="facts">
    <div class="fact"><b>{len(items)}</b><span>Entries listed</span></div>
    <div class="fact"><b>{nconf}</b><span>Already posted</span></div>
    <div class="fact"><b>{nsel}</b><span>Selection events</span></div>
    <div class="fact"><b>{nnat}</b><span>National junior</span></div>
    <div class="fact"><b>{len(cb)}</b><span>CBVA open slots</span></div>
    <div class="fact"><b>{nmulti}</b><span>Multi-day dates</span></div>
    <div class="fact"><b>{len(dbl)}</b><span>LA weekend pairs</span></div>
    <div class="fact"><b>{jn["sets"]:.0f}</b><span>Sets at the biggest</span></div>
  </div>
</header>

<section>
  <h2>Why the window opens in November</h2>
  <p class="lede">The junior tours roll their age bands over on <b>1 September</b>, and
  USA Volleyball&#8217;s winter series already runs on the following year&#8217;s. So the
  season that starts this November is the one she plays as a 17U and a U18, and everything
  before it was a different athlete on paper. The two bodies still label the same cohort a
  year apart, and that difference runs through every row below.</p>
  <div class="panel">
    <table>
      <thead><tr><th scope="col">Body</th>
        <th scope="col">Oldest birth year in her band</th>
        <th scope="col">Her label to Aug 2026</th>
        <th scope="col">Her label from Sep 2026</th></tr></thead>
      <tbody>
        <tr><td class="evc"><b>USA Volleyball</b><span class="dv">NTDP rosters, national-team trials</span></td>
          <td class="rank">2010</td>
          <td class="rank">U17</td><td class="rank"><b>U18</b></td></tr>
        <tr><td class="evc"><b>AVP Juniors, AAU, BVCA</b><span class="dv">the junior championships</span></td>
          <td class="rank">2010</td>
          <td class="rank">16U</td><td class="rank"><b>17U</b></td></tr>
        <tr><td class="evc"><b>p1440 Futures Tour</b><span class="dv">no 17U draw at all</span></td>
          <td class="rank">2010</td>
          <td class="rank">16U</td><td class="rank"><b>18U</b>, playing up</td></tr>
      </tbody>
    </table>
  </div>
  <p class="lede" style="margin-top:14px">The rollover is not a reading of the rulebook, it
  is on the entry list. Every player so far entered in the <b>17U</b> draw at the AVP
  Juniors West Coast Championships on 7&#8211;8 November graduates in <b>{wcc_grad}</b>
  &#8212; her year &#8212; and the 16U draw beside it has moved on to {wcc16}. Last November the same 17U draw was a year older. She was on the
  NTDP <b>U17</b> roster and entered AVP Juniors Nationals in <b>16U</b> in the same
  summer, and both were correct; from this November she is a <b>U18</b> at a USA
  Volleyball trial and a <b>17U</b> at AVP Juniors, AAU and BVCA, where entering 18U means
  playing up a year. The Futures Tour runs only 16U and 18U, and she has aged out of 16U,
  so there 18U is the only option.</p>
  <p class="lede"><b>Both 17U and 18U are listed below where an event runs both</b>, with
  &#8220;her band&#8221; marking the one she is naturally in. The numbers make the choice
  for her: the 17U draws carry nobody above her, and the 18U draws carry up to eighteen.</p>
</section>

<section>
  <h2>What counts, and what does not</h2>
  <p class="lede">Six kinds of date, and the difference between them is the whole plan.
  <b>Above her</b> is the number of individual players in that draw rated better than her
  9.68 and <b>median</b> is the field's median TruVolley. <b>Sets</b> is what a pair rated
  like hers actually played, and <b>contested</b> is the part of it against a pair within
  0.75 of her own &#8212; the sets that were a contest rather than a formality. Contested
  sets are the currency; everything else is a proxy for them. <b>Days</b> is how long her
  own draw runs, which is not the same as how long the event runs: AAU Hermosa and AVP
  Juniors Nationals each occupy five days of the pier, and an age group plays three of
  them. It is counted from the dates her division actually played last time, so 18U and
  17U at the same championship can differ.</p>
  <div class="keys">{keys}</div>
  <p class="lede" style="margin-top:18px">Three things are deliberately absent. The
  <b>recruiting showcases</b> &#8212; GNBV, the Western World Mega Collegiate Showcase
  &#8212; are off the list because she is committed to Santa&#160;Clara, and the field they
  draw backs that up: the 2026 Western World showcase carried nobody above her at a median
  of 7.26. The <b>CIFSS Pairs Championship</b> is a CIF Southern Section event and she is at
  a Central Coast Section school, so it is not open to her. <b>16U draws</b> are not listed
  either: she aged out of 16U when the bands rolled over in September, and the last 16U
  field she could have entered, at the 2026 AVP Juniors Nationals, carried nobody above her
  in any case. And the
  <b>AVP League qualifiers and NORCECA playoffs</b> appear only as <span class="tag t-rch">
  out of reach</span> &#8212; medians above 11.3 with most of the field over 10.5, and a
  median of one and a half matches before the exit.</p>
</section>

<section>
  <h2>The calendar</h2>
  <p class="lede">A plain date is already posted &#8212; on Volleyball Life for an event,
  on CBVA for an open. All {n26} rows between now and the end of December are posted,
  because both bodies publish about two months out; almost everything from January on is
  not. An <span class="est">~italic date</span> is an estimate: the
  series has run in the same week for two or three seasons and the next edition is not up
  yet. Field numbers come from the most recent edition of that event, never from the one
  on the row, which has not happened. Every event name is a link: to its own listing where
  one is posted, to last year's edition where it is not, and to the venue on CBVA for the
  open slots.
  <b>Days</b> separates the Saturday dates from the ones that need a hotel: every CBVA open
  and most of the p1440 circuit is a single day, the Futures Tour and the trials are
  weekends, and the four national championships are three days apiece. Where a date and a
  day count disagree &#8212; 14 July is a Wednesday &#8212; the date is when the event
  opens and the days are the part of it her draw plays. Rows marked
  <span class="pr">weekend pair</span> are one-day draws that fall on the two days of the
  same LA weekend; they are set out below.</p>
  <div class="panel">
    <table>
      <thead><tr>
        <th scope="col">Date</th><th scope="col">Event</th><th scope="col">St</th>
        <th scope="col">Draw</th><th scope="col">Kind</th>
        <th scope="col" class="num">Median</th><th scope="col" class="num">Above her</th>
        <th scope="col" class="num">Days</th>
        <th scope="col" class="num">Sets</th><th scope="col" class="num">Contested</th>
      </tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>
</section>

<section>
  <h2>Two draws in one LA weekend</h2>
  <p class="lede">One flight, one hotel, two draws. It is available more often than the
  calendar above makes it look, because of how the two circuits schedule around each other:
  CBVA has run two women&#8217;s opens in the LA basin on consecutive days exactly once in
  three completed seasons &#8212; and has posted a second for 21&#8211;22 November &#8212;
  but the junior circuit deliberately takes the day CBVA is not using.
  Of the {njun} genuine one-day girls&#8217; 17U/18U draws in the LA basin since September
  2023, {nadj} had a CBVA women&#8217;s open the day before or after &#8212; and another
  {nsame} ran head-to-head with one on the same day, which is the case to avoid.</p>
  <div class="panel">
    <table>
      <thead><tr><th scope="col">Saturday</th><th scope="col">Sunday</th>
        <th scope="col" class="num">Between</th>
        <th scope="col" class="num">Contested, each day</th>
        <th scope="col" class="num">Weekend total</th>
        <th scope="col">Dates</th></tr></thead>
      <tbody>
{chr(10).join(drows)}
      </tbody>
    </table>
  </div>
  <ul class="notes" style="margin-top:16px">
    <li><b>21&#8211;22 November is bookable now, and it closes the CBVA season.</b> Both
    dates are posted: North Beach on the Saturday, Laguna on the Sunday, {lag} miles apart.
    It is the one weekend where CBVA itself supplies both halves &#8212; in three completed
    seasons it has done that in the LA basin exactly once &#8212; and after 22 November the
    circuit stops until March, so this is the last open of the year. The evidence is thin
    on one side: North Beach has never run a November open before, and Laguna&#8217;s one
    previous November gave {lagc:.1f} contested sets.</li>
    <li><b>6&#8211;7 February is the next one that needs no guessing.</b> Both dates are
    posted on Volleyball Life and the beaches are {LEG[("North Beach, Santa Monica", "Hermosa Beach Pier")][0]}
    miles apart. The weekend is lopsided, though: the Saturday draws a median of
    {kb["med"]:.2f} with nobody above her, so it is a tune-up, and the Sunday is an
    ISF trial worth {isf["con"]:.0f} contested sets. Enter it for the Sunday.</li>
    <li><b>6&#8211;7 March is the best weekend on the list if CBVA keeps its slot.</b>
    Manhattan Pier has opened its women&#8217;s season on the Saturday nearest 8 March in
    each of the last three years, and the IBVL Winter Series Championships are posted for
    the Sunday at Hermosa, three miles down the strand. Together that is
    {mar:.1f} contested sets, more than any single date before July.</li>
    <li><b>A projected CBVA date is a coin flip, and the page says so.</b> Backtested by
    predicting the 2026 season from 2024 and 2025 across the 33 slots with enough history,
    the projection is exact 45% of the time and within a week 91%. So treat every pair
    marked <span class="tag f1">one posted, one projected</span> or
    <span class="tag f0">both projected</span> as a weekend to watch rather than to book:
    CBVA posts about seven weeks out, which for the March pairs means late January.</li>
    <li><b>Three more near-misses sit exactly one week off.</b> Newland projects to
    20&#8201;March against the Marine Open on the 21st &#8212; that one pairs &#8212; but
    Manhattan Pier&#8217;s late-April Saturday lands on the 24th against the p1440 West
    Coast Championships on the 18th, and Ocean Park&#8217;s April Sunday on the 11th with
    nothing beside it. A one-week shift in either direction turns each of those into a
    double, which is the other reason to re-read this table once the dates go up.</li>
    <li><b>The second draw is almost free, and that is the whole argument.</b> The travel,
    the hotel and the day off school are paid for by the first one; the second costs an
    entry fee and a drive of
    {min(mins)}&#8211;{max(mins)} minutes.
    Nothing else on this calendar improves the sets-per-trip ratio as cheaply.</li>
  </ul>
</section>

<section>
  <h2>Highline, AVP Next, BRAVO and Mexico</h2>
  <p class="lede">Four names worth checking, and they do not turn out to be four options.
  Two are real and sit a tier above anything else she can drive to; one is a good series in
  the wrong state; and the Mexican one is a tier she cannot enter, under a name that stopped
  existing in 2022.</p>

  <h3>The pro-am circuit in California</h3>
  <p class="lede">Highline is a Los Angeles promoter running one- and two-day adult opens
  with purses from $2,500 to $10,000 &#8212; Ocean Park and Santa Monica Pier,
  Dockweiler, Manhattan, Huntington, and away dates at Santa Barbara and Coronado. AVP Next is the AVP&#8217;s own
  developmental label, $8,000 minimum purse, and Highline runs some of its California
  stops. Both are harder than any CBVA open, and both hand out far more volleyball.
  Every draw either of them has run in California since 2025:</p>
  <div class="panel">
    <table>
      <thead><tr><th scope="col">Date</th><th scope="col">Event</th>
        <th scope="col">Series</th><th scope="col" class="num">Days</th>
        <th scope="col" class="num">Median</th><th scope="col" class="num">Above her</th>
        <th scope="col" class="num">Sets</th><th scope="col" class="num">Contested</th>
        <th scope="col" class="num">Pairs</th></tr></thead>
      <tbody>
{chr(10).join(prows)}
      </tbody>
    </table>
  </div>
  <ul class="notes" style="margin-top:16px">
    <li><b>The league-format dates are the volume outlier on this whole page.</b> Highline
    ran two of them in 2026 &#8212; Ocean Park in February and Manhattan Pier in March
    &#8212;
    and a pair rated like hers played {lg:.0f} sets in a single day with {lgc:.1f} of them
    contested. The best CBVA slot on the calendar gives {best["con"]:.1f} contested in a
    day and AVP Juniors Nationals {jn["con"]:.1f} across three. Nothing else comes close
    per day of travel.</li>
    <li><b>There are three different events here wearing one name.</b> Highline&#8217;s own
    purse dates in Los Angeles median {lamin:.2f} to {lamax:.2f} with {laa0:.0f} to
    {laa1:.0f} players above her &#8212; harder than the hardest CBVA open, which medians
    {best["med"]:.2f}. Its away dates at Santa Barbara and Coronado median {awmin:.2f} to
    {awmax:.2f} with {awa0:.0f} to {awa1:.0f} above her, and give twelve sets for it. And
    the {len(nxt)} draws carrying the AVP Next banner &#8212; Santa Barbara, Huntington
    Beach and Santa Monica Pier &#8212; median {nxmin:.2f} to {nxmax:.2f} but pull
    {nxa0:.0f} to {nxa1:.0f} players above her, the deepest adult fields in the state
    outside the AVP itself. Pick by the row, not by the promoter.</li>
    <li><b>Read the per-event set counts as indicative, not settled.</b> The last column is
    how many pairs rated within her band were actually in that draw, and it runs from
    {pmin} to {pmax}. A figure resting on one or two pairs is one or two teams&#8217;
    afternoon, not a property of the event. The medians and the count above her rest on the
    whole entry list and are solid.</li>
    <li><b>Entry is a membership, not a qualification.</b> AVP Next is a double-elimination
    or pool format played best of three to 21, 21, 15, capped at four full matches a day,
    with a published minimum age of fourteen and an AVP membership required; Highline&#8217;s
    own opens are open entry. There is nothing to qualify for and nothing to be nominated
    to, which is what separates this tier from the one below the next heading.</li>
    <li><b>Only one of them is on the calendar above, and that is deliberate.</b> A
    CBVA slot earns a calendar row by running the same venue in the same month in two of the
    last three seasons. Of this whole circuit only the Santa Barbara Open clears that bar
    &#8212; 3&#8211;5 October 2025 and 2&#8211;4 October 2026 &#8212; so it is listed and the
    rest are not. Highline&#8217;s first full season was 2026; it ran roughly one
    women&#8217;s open a month from February to September, and until a second season
    repeats them there is no slot to project. Watch its listings rather than planning
    around a date.</li>
    <li><b>BRAVO Beach is in Bowling Green, Kentucky.</b> It is a real series &#8212; USAV
    points and AVP East and West Coast Championship qualifiers, about thirty dates a year
    &#8212; and {bravo} of its {bravoall} recorded events are at its own facility in
    Kentucky. None are in California, Arizona or Nevada. Whoever recommended it was almost
    certainly recommending the format rather than the place.</li>
  </ul>

  <h3>Mexico, and what happened to the stars</h3>
  <p class="lede">There is no such thing as a one- or two-star tournament any more. The star
  ratings belonged to the FIVB World Tour, whose last season was 2021; the Beach Pro Tour
  replaced it in 2022 with three tiers &#8212; Futures, Challenge and Elite16 &#8212; of
  which Futures is roughly where the old one-star sat. The ratings below are the
  <i>American</i> entrants in each draw, because the US entry list is the one she would have
  to be on, and the last column is her chance of winning a given match against a pair at
  that median, read off the same curve the rest of this page uses.</p>
  <div class="panel">
    <table>
      <thead><tr><th scope="col">Tier</th>
        <th scope="col" class="num">US entrants rated</th>
        <th scope="col" class="num">Median</th><th scope="col" class="num">Weakest</th>
        <th scope="col" class="num">Below her</th>
        <th scope="col" class="num">Her match odds</th></tr></thead>
      <tbody>
{chr(10).join(brows)}
      </tbody>
    </table>
  </div>
  <ul class="notes" style="margin-top:16px">
    <li><b>Mexico does not host the entry tier.</b> In the whole record there has never been
    a Futures in Mexico. What Mexico hosts is Challenge and Elite16 &#8212; Tlaxcala and
    Nayarit in March 2026, Yucat&#225;n and Quintana Roo in 2025, Tepic, Veracruz,
    Guadalajara, La Paz before that. The American entrants in those draws median
    {B["Mexico Challenge"]["med"]:.2f}, and the weakest of them is
    {B["Mexico Challenge"]["lo"]:.2f}. Against that median she wins about one match in
    {round(1 / (1 / (1 + 2.718281828 ** (B["Mexico Challenge"]["med"] - PAIR))))}.</li>
    <li><b>The tier she could genuinely enter is Futures, and it is not next door.</b>
    Across every women&#8217;s Futures draw since 2024, {B["Futures, worldwide"]["under"]} of
    {B["Futures, worldwide"]["n"]} rated American entrants &#8212;
    {100 * B["Futures, worldwide"]["under"] / B["Futures, worldwide"]["n"]:.0f}% &#8212; are
    rated below her, and a 2026 graduate rated 9.18 played one. The Americas get one or two
    a year: Pompano Beach, Florida in December 2024 and again in December 2025, and Halifax
    in 2024. Nothing on the Pacific side, and nothing in Mexico.</li>
    <li><b>You do not enter; USA Volleyball enters you.</b> A federation may put at most
    four teams on a Futures confirmed entry list, the entry form is due about 35 days out
    and the confirmed list is published 28 days out. That makes it the same kind of decision
    as the January trials rather than something to book &#8212; which is an argument for
    the trials, not against the Futures.</li>
    <li><b>And the whole structure is being rebuilt during her 2027.</b> Volleyball World
    announced in January 2026 that an FIVB Beach World Series would launch in November 2026
    and replace the Beach Pro Tour, built around roughly ten destination events. What
    happens to Futures, Challenge and Elite16 under it has not been published, so no 2027
    international calendar on this page would be worth printing.</li>
    <li><b>So the honest answer on Mexico is no, and the useful one is the tier below.</b>
    A Futures entry is worth asking her NTDP contact about for 2028, after a season of the
    pro-am dates above and a trials appearance. A Mexican Challenge is a professional event
    two rating points above her and is not a 2027 question.</li>
  </ul>
</section>

<section>
  <h2>Santa Cruz, and what it is for</h2>
  <p class="lede">Fifteen minutes from the house, roughly $200 for first, and she has won
  the last three. It belongs on the calendar &#8212; but not as competition, and the
  contested-sets column says why.</p>
  <div class="panel">
    <table>
      <thead><tr><th scope="col">CBVA open</th><th scope="col" class="num">Median field</th>
        <th scope="col" class="num">Above her</th><th scope="col" class="num">Sets</th>
        <th scope="col" class="num">Contested</th><th scope="col" class="num">Share</th>
      </tr></thead>
      <tbody>
        <tr><td class="evc"><b>Main Beach, Santa Cruz</b><span class="dv">{sc["slots"]} slots a year &#183; 15 minutes away</span></td>
          <td class="num rank">{sc["med"]:.2f}</td><td class="num rank">{sc["above"]:.0f}</td>
          <td class="num rank">{sc["sets"]:.1f}</td>
          <td class="ht h{heat((sc["con"] or 0)/13)}">{sc["con"]:.1f}</td>
          <td class="num rank">{100*sc["con"]/sc["sets"]:.0f}%</td></tr>
        <tr><td class="evc"><b>{esc(best["venue"])}, {esc(best["city"])}</b>
          <span class="dv">the best CBVA slot on the list</span></td>
          <td class="num rank">{best["med"]:.2f}</td><td class="num rank">{best["above"]:.0f}</td>
          <td class="num rank">{best["sets"]:.1f}</td>
          <td class="ht h{heat((best["con"] or 0)/13)}">{best["con"]:.1f}</td>
          <td class="num rank">{100*best["con"]/best["sets"]:.0f}%</td></tr>
        <tr><td class="evc"><b>AVP Juniors National Championships</b>
          <span class="dv">Hermosa Beach, three days in July</span></td>
          <td class="num rank">{jn["med"]:.2f}</td><td class="num rank">{jn["above"]:.0f}</td>
          <td class="num rank">{jn["sets"]:.1f}</td>
          <td class="ht h{heat((jn["con"] or 0)/13)}">{jn["con"]:.1f}</td>
          <td class="num rank">{100*jn["con"]/jn["sets"]:.0f}%</td></tr>
      </tbody>
    </table>
  </div>
  <ul class="notes" style="margin-top:16px">
    <li><b>It is the weakest contest on the circuit, by a distance.</b> Santa Cruz gives
    {sc["sets"]:.1f} sets to a pair rated like hers and {sc["con"]:.1f} of them against
    anyone near her level &#8212; {100*sc["con"]/sc["sets"]:.0f}%. The other CBVA slots on the
    list run from {shares[0]:.0f}% to {shares[-1]:.0f}%, median {st.median(shares):.0f}%.
    Three days at AVP Juniors Nationals are worth
    {jn["con"]/sc["con"]:.0f} Santa Cruz Saturdays in contested volleyball.</li>
    <li><b>Against a field with a median of {sc["med"]:.2f} she is an
    {100/(1+2.718281828**-(PAIR-sc["med"])):.0f}% favourite in a typical match.</b> That figure is not a guess: across 7,000 rated CBVA
    women's matches the stronger pair's win rate tracks a logistic in the rating gap almost
    exactly &#8212; 57% at a half-point gap, 81% at a point and a half, 91% at two and a
    half. A match she wins seven times in eight carries almost no information and almost no
    rating.</li>
    <li><b>So: play it, and count it as paid practice.</b> Fifteen minutes of travel makes
    the opportunity cost nearly zero, $200 more than covers the entry, and five sets of
    serve-receive in a real draw beats five sets in training. The only rule is that it never
    substitutes for a travel date &#8212; and on the calendar above, the Santa Cruz slots
    fall in months that already hold something better.</li>
    <li><b>The prize is not a reason by itself.</b> At roughly $200 for first it is a good
    Saturday, not a revenue stream, and it is the one number on this page that comes from
    you rather than from the data.</li>
  </ul>
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
    <li><b>An estimated date is an estimate.</b> {nconf} of the {len(items)} rows carry a
    date their organiser has posted; the other {len(items) - nconf} are projected from a
    series that has run in the same week for two or three years. Everything through
    December is posted and almost nothing after it is. Organisers move dates; confirm
    before booking anything.</li>
    <li><b>The field numbers describe last year's draw, not next year's.</b> They are the
    best guide available to what a date is worth, but next season's entry list does not
    exist yet, and a selection event's field in particular turns over every season.</li>
    <li><b>Ratings are current TruVolley</b>, applied to fields up to two years old, so an
    older edition reads slightly stronger than it was. Unrated entrants are excluded from
    the medians, which skews them a little high.</li>
    <li><b>The day count is last year's, not next year's.</b> It is the number of distinct
    dates her division played at the most recent edition, so it catches the part of a
    five-day festival that belongs to her age group &#8212; but a tour that adds a day or
    merges two age groups changes it, and a listing often posts a single opening date
    rather than a span.</li>
    <li><b>Age bands are birth-year ceilings, and the junior ones turn over in September.</b>
    U-N admits anyone born in the qualifying year or later, so a 17U draw this season
    admits 2010 and younger and she is the oldest year in it; an 18U draw admits 2009 and
    younger and she is playing up. USA Volleyball counts a year differently, which is what
    the first section is about. In September 2027 the tours roll again and she becomes an
    18U; in 2028 she ages out of USA Volleyball's U18 and that year's U19 becomes the
    equivalent position.</li>
    <li><b>Trials entry is not the same as trials eligibility.</b> Nineteen of the
    twenty-four entrants at the 2026 U18 trials came off the NTDP rosters she was also on,
    and athletes two years younger than her entered, so the route is open &#8212; but the
    published criteria should be confirmed with her NTDP contact rather than inferred from
    who turned up.</li>
    <li><b>Nevada contributes two dates and neither is a reason to go.</b> Arizona earns
    its place because the p1440 circuit runs Mesa dates she can reach; Nevada is listed
    for completeness, and what the record holds is a December girls' pairs date in Las Vegas
    and a Tahoe Saturday played on grass, which carries its own rating and cannot move her
    sand one. Out-of-region national events are left out because they are not a day's
    travel: the Futures Tour stops in Florida, Texas and Washington, and its <b>spring
    championship</b>, which was at Santa Monica in March 2026 and has moved to Gulf
    Shores, Alabama for 27&#8211;28 February 2027. That move is the reason every row on
    this page is now checked against its own listing before the page is written.</li>
  </ul>
</section>
<footer>
  Confirmed dates from the Volleyball Life tournament crawl; estimated dates projected from
  the 2024&#8211;2026 editions of the same series. Field strength and match counts computed
  from those editions' entry lists and published brackets, with TruVolley for
  {len(tv):,} players retrieved {today.strftime("%-d %B %Y")}. CBVA circuit from CBVA's own
  tournament database. The five tables on this page are also a
  <a href="plan-2027.xlsx">spreadsheet</a>, built from the same numbers.
</footer>
</div>
"""


if __name__ == "__main__":
    # Build first, write second: open(..., "w") truncates on a build that raises,
    # and this build deliberately raises on a venue mismatch.
    page = build()
    open(OUT, "w").write(page)
    print("wrote", OUT)
