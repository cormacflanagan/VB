# Beach NTDP Girls — Tournament Analysis

Cross-references the rosters of USA Volleyball's 2026 Beach NTDP Summer Training Series
against each athlete's competition record on [Volleyball Life](https://volleyballlife.com),
for the twelve months ending **9 August 2026**.

Three groups are covered:

| Group | Athletes | Source | Report |
| --- | --- | --- | --- |
| Girls U18 | 13 | Published NTDP roster | [`docs/bntdp-18u.html`](docs/bntdp-18u.html) |
| Girls U17 | 20 | Published NTDP roster | [`docs/bntdp-17u.html`](docs/bntdp-17u.html) |
| Class of 2027 | 60 | Derived — see below | [`docs/bntdp-2027.html`](docs/bntdp-2027.html) |
| Class of 2028 | 60 | Derived — see below | [`docs/bntdp-2028.html`](docs/bntdp-2028.html) |
| Class of 2028 | 30 | Same cohort, tighter cut | [`docs/bntdp-2028_top30.html`](docs/bntdp-2028_top30.html) |
| Class of 2028 | 20 | Same cohort, tightest cut | [`docs/bntdp-2028_top20.html`](docs/bntdp-2028_top20.html) |
| **2027 and younger** | 60 | Age-eligible — see below | [`docs/bntdp-2027_younger.html`](docs/bntdp-2027_younger.html) |
| **2028 and younger** | 60 | Age-eligible — see below | [`docs/bntdp-2028_younger.html`](docs/bntdp-2028_younger.html) |

Four companion pages answer planning questions the matrix cannot:

| Page | Question |
| --- | --- |
| [`docs/calendar-2027.html`](docs/calendar-2027.html) | Which events does the class of 2027 actually turn up to, month by month? |
| [`docs/partners-2028_top30.html`](docs/partners-2028_top30.html) | Who partners with whom inside the class-of-2028 top 30? |
| [`docs/partners-2027_younger.html`](docs/partners-2027_younger.html) | The same, across the 18U-eligible top 60. |
| [`docs/partners-2028_younger.html`](docs/partners-2028_younger.html) | The same, across the 17U-eligible top 60. |
| [`docs/august-temps.html`](docs/august-temps.html) | How hot is an August day in Santa Cruz, and has it moved? |
| [`docs/august-nights.html`](docs/august-nights.html) | The same question for August nights &mdash; where the answer is yes. |

**Doubles only.** Club, 3v3 and 5v5 results are excluded: a placing there reflects a squad
of five to twelve, not the individual. The test is roster size rather than the division
name, which is unreliable — "Open (5v5)", "OPEN", "Club Division" and "Girls Open (5 Pairs)"
are all team formats. Every entry kept has exactly one partner.

**Each age division is treated as its own competition.** The 18U bracket and the 16U
bracket running beside it at the same event are different fields, so they are different
competitions. The output is a players × competitions matrix: every cell is a finishing
position, and the size of that field is carried in the column heading, alongside each
player's TruVolley rating.

## Rosters

Names and USAV regions come from USA Volleyball's published roster page; Volleyball Life
IDs are in [`scripts/rosters.py`](scripts/rosters.py), resolved by name search and checked
against date of birth, graduation year, club and competition footprint.

Two needed manual resolution, both in the U17 group:

- **Olivia LeDoyen** (id 30929) is spelled `LeDoyen` on Volleyball Life and her profile
  still carries a Florida address, but she plays for a South Bay club and competes almost
  entirely in Southern California, matching her SCSN listing.
- **Ashley Ruschill** has two profiles; 105245 is the active one (118 events), 247847 is a
  near-empty duplicate with nothing inside the window.

## Age-eligible cohorts

A graduating class answers "who else is in her year". A bracket does not work that way: an
18U field is grad 2027 **and younger**, so the girls a 2027 player actually meets include every
strong 2028, 2029 and 2030 playing up. USA Volleyball says the same thing in its own rosters —
the NTDP **U17** group spans grad 2028, 2029 and 2030.

`scripts/close_cohort.py <year>` crawls the partner graph to closure on `gradYear >= year`
instead of `== year`. It seeds from the class populations already closed and from the ids those
crawls *rejected* — a rejected id is one that partnered with a girl in the class and failed the
equality test, which is exactly the pool the inequality admits — so round 0 is a re-check rather
than a re-expansion, saving several thousand fetches. `scripts/cohort_roster.py <year> <n>`
then draws the cut into a roster file the rest of the pipeline registers like any other group.

**The 2028-and-younger cohort closed at 13,126 girls, 11,309 of them rated**, over six rounds
whose above-floor admissions decayed 70, 17, 8, 4, 2, 0. The top 60 stopped moving after round 2
— three further rounds and 4,600 more girls changed it by one place.

**Twenty of that top 60 are younger than 2028** — seventeen from 2029, three from 2030 — so a
third of the real field was invisible to the class grouping. They cluster at the two ends: five
inside the top 15 (Nariah Johnson at #6, Tristan Ana Del Riego #10, Brooke Proctor #12, Reagan
Carlin #13 as a 2030, Ashley Ruschill #14), and eight in the last sixteen places. The cut is
tight: #60 is Isabella Cordaway-Dreier at 7.625, a thousandth ahead of #61.

**The 2027-and-younger cohort closed at 17,178 girls, 14,398 rated**, and it is the more
striking of the two: **28 of its top 60 are younger than 2027** — 20 from 2028, 6 from 2029,
2 from 2030. Nearly half the 18U field is younger than the class that names it. The top ten
stays age-segregated (seven of the first ten are 2027s), but from #8 downward the classes
interleave completely. Its cut is at 8.102, half a rating point above the 17U group's 7.625.

Because a cohort spans several classes, the roster table carries a **Class** column and each
matrix row a year badge — shown only when the group actually spans more than one year.

Crawls this long do not always outlive the machine they run on, so the expansion phase runs in
chunks of 400 and records who has been expanded after each one. Without that, a resumed run
restarts its whole round and can never converge.

## Graduating-class groups

Volleyball Life publishes no class ranking, so these groups are derived rather than read off
a page. `scripts/discover_class.py <year>` crawls the partner graph outward from a seed set
of known athletes in that class, keeping every player whose profile reports the matching
`gradYear` and `male == false`. `scripts/close_class.py <year>` then runs that crawl **to
closure**: it repeatedly expands the partners of every player already found, stopping only
when a full round turns up nobody new above a 7.0 rating floor.

Adding a class means adding a seed dictionary to `discover_class.py`; any
`roster_<year>[_suffix].json` is auto-registered as a group by `rosters.py`, which also picks
the shared-competition threshold from the roster size — 8+ at fifty athletes or more, 5+ from
twenty-five, 4+ below — so the bar stays roughly proportional and the cuts remain comparable
to one another. The suffix lets one cohort carry several cuts side by side without their data files
colliding — `roster_2028_top30.json` produces the group `2028_top30`, writes
`2028_top30_{clean,site,h2h}.json`, and still renders as "class of 2028" because the year is
parsed off the front of the key.

Ratings move as results process, so a cut drawn days ago is drawn on stale numbers.
`scripts/refresh_class.py <year>` re-rates an already-closed cohort — reusing the cached
population rather than re-crawling — re-draws the cut and prints the churn. Re-rating the
2028 cohort on 11 August moved 578 ratings and changed three of the sixty, which is why a
redo re-draws the cut rather than only re-rendering.

**Closure is not optional.** A discovery run that stops on its round cap has *not* proved
anything about the cut-off, and the 2027 run did exactly that on its first attempt — six
rounds, 1,780 girls found, and 737 candidates still unchecked. `discover_class.py` now tracks
convergence explicitly and prints a warning when it stops on the cap, so a capped run cannot
be mistaken for a closed one.

Closure matters more than it sounds. A two-hop crawl found 449 girls, and spot-checking it
against a top-30 cut suggested it was complete — but that only ever proved completeness
*above* that cut. Running to closure took the population to **1,574 girls in the class, 1,373
of them rated**, and six of the players it added land inside a top-60 cut. The final round
added 563 players and not one cleared the floor, so the ranking is now stable at this depth.

The 60 highest TruVolley scores are the roster (`scripts/roster_2028.json`; full population
kept in `data/pop2028.json` so the cut can be redrawn without re-crawling). The cut is tight:
#61 is Nikolina Mimic at 7.331, fifteen thousandths behind #60.

Because the group is 60 rather than 13, its matrix uses a shared-by-8 threshold instead of 3.

The script also harvests `/vision/players`, Volleyball Life's opt-in recruiting directory,
which exposes height, playing side and block-touch metrics. Coverage proved too thin to use
(it returns 20 records and the metrics are largely null), so heights come from the ordinary
player profile instead.

## Data sources

All read from the Volleyball Life public API at `https://api-v8.volleyballlife.com`:

| Endpoint | Provides |
| --- | --- |
| `GET /playerprofile/search/{name}` | Player lookup, used to resolve roster names to IDs |
| `GET /playerprofile/{id}` | Tournament history including `tdId` (tournament-division ID) |
| `GET /playerprofile/{id}/truvolley` | TruVolley rating, peak, confidence, win/loss record |
| `POST /Tournament/CountsV3Bulk` | Team count per division — the field size denominator |
| `GET /vision/players` | Opt-in recruiting directory: height, side, block touch (sparse) |
| `POST /playerprofile/feed/matches` | Match-level results: opponents, sets, phase — the head-to-head source |

Field size comes from the team count of the specific division the athlete competed in,
matched by `tdId`. Division names alone are not sufficient: one event runs several
divisions of very different sizes.

## Pipeline

```
python3 scripts/discover2028.py                 # build the class roster -> roster_2028.json
python3 scripts/collect_group.py 17U 18U 2028   # fetch  -> data/<group>_{clean,site}.json
python3 scripts/render_group.py  17U 18U 2028   # render -> docs/bntdp-<group>.html
```

Run with no arguments, both scripts process both groups. `scripts/resolve17.py` is the
one-off name-resolution helper used to build the U17 roster IDs; it is kept for auditing
and for adding future groups. `scripts/shortnames.json` maps full event names to the
abbreviations used in matrix column heads — anything not listed there is abbreviated
automatically at a word boundary.

`data/*_clean.json` and `data/*_site.json` are the retrieved snapshots, so the reports can
be regenerated without re-querying the API.

## What the two groups look like

All five reports run on the same twelve-month window ending 11 August 2026 and the same
rating epoch, so they are directly comparable.

| | Girls U18 | Girls U17 | Class of 2027 | Class of 2028 |
| --- | --- | --- | --- | --- |
| Athletes | 13 | 20 | 60 | 60 |
| Events attended (doubles) | 87 | 110 | 294 | 283 |
| Pairs competitions | 103 | 141 | 305 | 353 |
| Matrix threshold | 3+ | 3+ | 8+ | 8+ |
| Matrix columns | 20 | 25 | 23 | 21 |
| Club results dropped | 40 | 73 | 226 | 158 |
| Distinct doubles matches | 815 | 1,088 | 2,635 | 3,429 |
| Head-to-head pairings | 52 | 62 | 357 | 434 |

The class of 2027 is the stronger cohort at the top — Thais Treumann alone is rated 10.170,
above anything in 2028 — but its members meet each other less often: 357 pairings from 2,635
matches, against 434 from 3,429 for 2028.

The U18 group is far more concentrated: the U18 Beach National Team Trials put 12 of its
13 into one 12-team field, and two more competitions drew 11. Nothing in the U17 year
gathers more than 9 of the 20, because that cohort splits across 15U, 16U, 17U and 18U
brackets rather than converging on a single selection event.

Dropping club formats hit the U17 group hardest — 73 results removed against the U18s' 40 —
and removed the BVCA Orange County 5v5 series, which had been the U17s' densest column.

## Links out to Volleyball Life

Every athlete name and every competition name in the reports is a link:

| Element | Target |
| --- | --- |
| Athlete name (roster, matrix row, appendix, chart label and dot) | `volleyballlife.com/player/{playerProfileId}` |
| Competition name (matrix column head, appendix) | `volleyballlife.com/tournament/{tournamentId}/division/{tdId}` |
| CBVA tag, where CBVA runs the event | `cbva.com/tournaments/{id}[/{divisionId}]` |

Competitions link to the **division** page rather than the event, so the destination is the
exact field the cell is scored against — the 16U bracket, not the whole tournament that also
ran 18U and 15U beside it. Both URL shapes were checked against the live site.

## CBVA

CBVA runs much of the Southern California circuit, but Volleyball Life records the sanction as
"AVPA" — the field is useless for identifying their events, and the name only sometimes says
"CBVA". So membership is established against CBVA itself. `scripts/cbva.py` crawls
`cbva.com/tournaments`, which is server-rendered and filterable by date, a month at a time —
**194 tournaments** across the window — then `--link` matches ours to theirs on date plus venue,
after normalising away the words the two sites disagree about ("pier", "beach", "courts").

The venue match is made against the whole Volleyball Life name, not just the part after "at".
Half of CBVA's own events are recorded there as "6/13/26, Main Beach, Santa Cruz" with the
location field empty, so a stricter read matched 48 events and silently missed the entire
Santa Cruz series. Offering the whole name costs nothing, because only CBVA's venue tokens are
scored: **89 of our 467 events match**, and only 8 carry "CBVA" in the name — so a name test
would have missed ten in eleven. Matched events carry a
CBVA tag beside the sanction: in the reports on the matrix column head and the appendix row, in
the calendar in the Body column.

CBVA's tournament pages render client-side, so their content cannot be verified by fetching
them; the IDs come from CBVA's own anchors on the listing page and the URLs return 200.

## Head-to-head

A finishing position only says who placed higher in the same field; it does not say the two
players ever met. `scripts/h2h.py` pulls actual matches from `POST /playerprofile/feed/matches`
(body `{playerIds, tournamentIds}`) and reconstructs both sides of the net from the querying
player plus her partners versus her opponents.

A match is returned once per player queried, so results are de-duplicated on `matchId`. Where
two group members were opponents *as a pair*, the match correctly counts against each of them;
where they played together it is recorded as a partnership instead, not a head-to-head. Only
doubles matches are kept, the same rule the rest of the analysis uses.

For the class-of-2028 group that is **3,498 distinct doubles matches**, of which **607 results
across 451 pairings** were contested between two members of the top 60 — 451 of the 1,770
possible pairings have met at least once. `scripts/h2hview.py` renders a round-robin
crosstable (rows are athletes in rating order, columns the same athletes by rank number) and a
rivalry list. Cell colour is diverging: one pole for the row player ahead, the other for
behind, neutral for level, blank for never met.

## The rating-against-workload figure

Each report carries a scatter of TruVolley against number of doubles competitions, with a
least-squares fit. Across the 60-player class group the fit slopes **down**: r = −0.33,
r² = 0.11. The effect survives dropping the light schedules (r = −0.32 for the 52 players
with eight or more competitions), so it is not an artifact of a few inactive profiles.

The likely mechanism is that TruVolley rewards win rate, so a player who enters fewer, more
selective events protects her rating while one who plays a heavy national schedule against
strong fields spends it. Read the rating alongside the workload axis, not on its own.

`scripts/scatter.py` renders the figure as inline SVG — one hue, no legend, identity on the
notable points carried by direct labels rather than colour, and hover text in an SVG `<title>`
so the page still needs no JavaScript. The palette was checked with the dataviz validator and
passes all six checks against both the light and dark chart surfaces.

## The season calendar

`scripts/calendar.py <group>` counts how many of the top 60, top 30 and top 15 turned up,
**per age bracket** — the same rule as the matrices, where the 18U field and the 17U field
running beside it are separate competitions. Division names are folded onto the bracket they
are actually played at: an explicit age wins, and failing that the youngest graduating year
admitted sets the ceiling, so "Girls 18U", "U18 Girls", "Girls 18:U (Grad Year 2026-2027)" and
"Class of '26 & Younger" all resolve to 18U. Adult open draws land under Women's. `scripts/calendar_page.py` renders it in calendar order with a sequential heat ramp
on the three turnout columns, so the events the cohort converges on stand out from the ones a
single pair happened to enter. `MIN_TURNOUT` sets the bar, applied to each bracket on its own;
at 4 of the top 60 the list stays
short enough to plan from, and it also clears out the weekly 2v2 mini-tournaments that
dominated the next-edition matches at a lower bar.

For the class of 2027 that is **59 brackets across 55 events**, from 294 events entered in all.
The season has one clear peak, three weeks in July at Hermosa Beach — but the split changes what
it says. AVP Juniors Nationals drew 40 of the 60 across both brackets, and the split shows why
that number flatters: 30 in the 18U, 15 in the 17U. The single biggest field of the year is not
that but **BVCA Individual Pairs, 34 of the 60 in one 18U draw**. AAU Hermosa splits almost
evenly, 13 and 14, so neither of its fields is as deep as its 27 suggests.

`FOCUS` names the bracket the reader is planning for — 17U — and gets its own section above
the calendar, with no turnout bar, because a 17U draw *existing* is the fact worth knowing.
That section is the page's most useful finding: of the 294 events the class of 2027 entered,
**six ran a 17U bracket at all**, 50 of their 822 entries. AVP Juniors (West Coast, East Coast,
Nationals), the AAU Hermosa pairs, BVCA Pairs West Coast and one recruiting showcase are the
whole list. Everywhere else the choice was 18U or the adult women's open, with nothing between
— so a thin 17U record reflects an absent draw, not an avoided one. The class-of-2028 cohort
shows the same six-event pattern independently.

Because the page exists to pick next year's schedule, each row is matched to its 2026-27
edition where one is already on Volleyball Life's upcoming feed, by a name normalised to strip
years and ordinals (`norm()` in `calendar.py`). **4 of the 55** matched; the rest are either
not yet posted or genuinely one-off. Raising the bar to 4 mattered here: at 2, 29 events matched,
but almost all were weekly 2v2 mini-tournaments that post a year of dates in advance.

### The national-team pathway

Selection dates are not ordinary tournaments — turnout there is who was picked or qualified,
not who chose to enter — so they get their own section, matched by name (`PATHWAY`) and counted
against the **published NTDP rosters** as well as against the class. That is the one place in
this repo where the two data sets meet: the U18 and U17 groups are read for attendance and
scored out of 13 and 20.

It isolates the two dates that carry the selection. The **U18 Beach National Team Trials**
(31 January, Manhattan Beach Pier) held 12 of the eventual 13-girl U18 roster, and the **Youth
Olympic Games Trials** (18 June, Hermosa Beach Pier) held 11. Everything else on the pathway —
the ISF trials, USAV Beach Nationals, the U23 trials — drew one to three of them, so a national
title is not the same thing as a selection room.

### The training series

The programme runs four residential training series a year, and they are the dates it is
actually built around — but they are invitational, have no draw and produce no result, so
Volleyball Life has no record of them and nothing in this repo can derive them. `NTDP_TRAINING`
in `calendar_page.py` carries them as literals read off USA Volleyball's own schedule, each row
linking to the announcement its dates came from:

| Series | Dates | Where |
| --- | --- | --- |
| Fall 2025 | 27–28 September | Virginia Beach, VA (51st Neptune Festival) |
| Winter 2025 | 27–29 December | Manhattan Beach, CA |
| Spring 2026 | 15–17 May | Manhattan Beach, CA |
| Summer 2026 | 26–30 July (girls) | Chula Vista Elite Athlete Training Center, CA |
| Fall 2026 | 25–27 September | Dania Beach, FL |

`scripts/ntdp_series.py` scrapes the rosters as well as the dates: each age group is one
`tableizer-table` of FIRST / LAST / REGION under a heading that names it, and `--match` resolves
the girls to Volleyball Life ids (89 of 101). Each series becomes a calendar row per girls' age
group, with the roster size where a field size goes and the names on hover. The age groups vary
— the spring series ran no U18 at all, because the Girls U18 National Team trained alongside it.

**101 girls were invited across the four series, six to all of them.** Of the 33 on the two
summer rosters this repo tracks, one had been to all four (Jordyn Wilson), sixteen to three and
seven only to the summer — so the summer roster reads as the end of a year's selection rather
than a single decision. The 2026–27 winter series has not been dated yet.

### The local dates

A turnout-ranked calendar is a ranking of *travel*, and it buries the home venue: of the Santa
Cruz dates last season carrying a draw she would enter, one drew anyone from the class-of-2027
top 60. So those dates are admitted to the calendar by geography rather than by turnout — they
sit in date order with the rest, marked `local`, carrying no turnout figures because there is
none to carry.

They come from CBVA's listing (`LOCAL` names the venue) rather than from the class's record, so
a date appears whether or not anyone in the class went, and `LOCAL_DIV` keeps only the draws
worth entering. Where the class *did* enter — nine of the fifteen, below the turnout bar — the
row is our own event with its real figures rather than a stand-in, and one that already cleared
the bar is tagged in place instead of repeated. CBVA's ladder runs Open, AA, A, B, and the Santa Cruz Saturdays alternate
between an Open+A card and an AA+B one, so keeping Open and A drops the weaker card entirely
rather than trimming a column from every date. A local 18U date nobody in the class entered is
dropped too — the Cal Cup bid series runs the same Wednesday draw eight times, and an empty one
carries nothing the week either side does not. That leaves **11 local dates** on the
calendar: women's Saturdays through the autumn and spring, and a midweek girls' 18U Cal Cup bid
series every Wednesday through June and July. `scripts/cbva.py --upcoming` crawls the
not-yet-played listing the same way, and those dates join the next-season table.

## August temperature at Santa Cruz

The calendar's home venue is Santa Cruz, so the last two pages ask what an August day there
is actually like: **the mean of every daily reading in August, one datapoint per year, back
to 1893.** Days and nights are separate pages because they are separate answers.

| Page | Element | Observed trend | Homogenised trend |
| --- | --- | --- | --- |
| [`docs/august-temps.html`](docs/august-temps.html) | Daily highs (TMAX) | −0.03 °F/decade | +0.08 °F/decade |
| [`docs/august-nights.html`](docs/august-nights.html) | Daily lows (TMIN) | **+0.46 °F/decade** | **+0.35 °F/decade** |

```
python3 scripts/august_temps.py --refresh   # both pages, re-downloading the sources
python3 scripts/august_temps.py tmin        # just the nights, from the cached sources
```

The source is NOAA's station **USC00047916, Santa Cruz, CA** — a Historical Climatology
Network site with daily observations from 1893 and the only long temperature record in the
town; every other Santa Cruz entry in GHCN is a modern volunteer rain gauge with no
thermometer. Days carrying a GHCN quality flag are dropped, and a year needs 28 of its 31
days to be averaged, which leaves **124 Augusts of highs and 123 of lows between 1893 and
2021**. The station stopped reporting in April 2022.

Each page draws two series, because the raw one cannot be read alone: the daily record as
observed, and NOAA's homogenised version of the same station (USHCN v2.5, `FLs.52j`),
corrected for changes of observation hour, instrument and siting and extended to 2025 by
infilling from neighbours.

**The days say nothing.** Observed −0.03 °F per decade, homogenised +0.08 — the correction
is larger than the trend it corrects, so the daytime record cannot settle its own sign.
That the raw daytime line carries station history is measurable rather than assumed: the
pipeline differences every August against **Watsonville**, 21 km down the coast, and reports
the gap by decade. It wanders across 5.3 °F — for two stations that share their weather it
should be a constant — and the 2010s sit at +4.1 °F after two decades near +1.5. That
stretch is shaded on the chart, and it is why 2015 appears as the warmest August on record
at 84.0 °F where the homogenised series puts it at 82.6 °F.

**The nights say a great deal.** Observed +0.46 °F per decade, homogenised +0.35: the
correction changes the size of the answer, not the answer. The last 30 Augusts average
**4.8 °F warmer at night** than the first 30, and every decade average from the 1980s on is
warmer than every decade average before it. The nighttime gap against Watsonville wanders
too, but without direction. What the record cannot separate is the town from the climate —
homogenisation catches a thermometer moving, not a city growing around one, and warmer
nights with unchanged afternoons is the textbook shape of an urban heat island as well as of
a warming ocean.

Either way the day–night gap has closed: across the 112 Augusts with both readings, the mean
spread between the day's high and its low fell from 24.4 °F over the first 30 to 19.7 °F over
the last 30, about a fifth of it gone.

`scripts/august_page.py` renders both figures as inline SVG on the same terms as the scatter
— two hues checked with the dataviz validator against both the light and dark chart surfaces,
the second series dashed as well as differently coloured, hover text in an SVG `<title>` so
the page needs no JavaScript, and the full table below the chart as the non-visual view.

## Partnerships

`scripts/partners_page.py <group>` builds the who-played-with-whom matrix. A partnership is
counted once per *competition* — the same (event, division) key the rest of the analysis uses —
so a pair that goes deep in a bracket counts the same as one that goes out in the first round.

Among the class-of-2028 top 30, **36 of the 435 possible pairings** have happened at all, across
392 doubles entries and 126 distinct partners in total. The matrix is therefore sparse, and the
more informative column is the count of *different* partners per player: the cohort mostly plays
outside itself, and only Summer Tukua has a single partner all year.

Run over the 18U-eligible top 60 the picture is the same shape at twice the size: **96 of 1,770
possible pairings**, 818 doubles entries, 222 distinct partners. The densest are Sienna
Mattoon–Tristan Ana Del Riego (9), Brooke Proctor–Reagan Carlin (8), then three pairs at 7.

The densest pairings are Madison Gillinger–Sadie Harris and Abigail Moffett–Charlotte Jansen
(8 competitions each), then Sage Illian–Dreya Scherfenberg (7). Because a player's most-used
partner is often *not* in the group — Kendal Walker has 14 competitions with Emerson Thomas and
no in-group partnership at all — the summary table marks out-of-group partners rather than
hiding them.

## Caveats

- **Athletes who enter two divisions at one event** appear once in each division's column,
  which is the point of the split — at AVP Juniors Nationals, Olivia Herron was 9th of 64
  in 18U and 63rd of 63 in 17U.
- **Coach and spectator registrations appear in player histories** with a finish of 1.
  These are filtered out, otherwise they show up as phantom wins.
- **TruVolley still includes club play.** The rating column comes from Volleyball Life and
  is computed across all formats, so unlike the matrix it is not doubles-only.
- **Ties are shared.** Beach draws award equal finishes to teams knocked out in the same
  round, which is why blocks of 5th, 9th and 17th recur.
- **A few field sizes are unavailable** where Volleyball Life reports a division team
  count of zero; those cells show the finish with the field marked as unavailable.
