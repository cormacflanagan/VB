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

Two companion pages answer planning questions the matrix cannot:

| Page | Question |
| --- | --- |
| [`docs/calendar-2027.html`](docs/calendar-2027.html) | Which events does the class of 2027 actually turn up to, month by month? |
| [`docs/partners-2028_top30.html`](docs/partners-2028_top30.html) | Who partners with whom inside the class-of-2028 top 30? |

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

**48 of our 467 events matched**, 46 of them to a specific division, and only 8 carry "CBVA" in
the Volleyball Life name — so a name test would have missed five in six. Matched events carry a
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

## Partnerships

`scripts/partners_page.py <group>` builds the who-played-with-whom matrix. A partnership is
counted once per *competition* — the same (event, division) key the rest of the analysis uses —
so a pair that goes deep in a bracket counts the same as one that goes out in the first round.

Among the class-of-2028 top 30, **36 of the 435 possible pairings** have happened at all, across
392 doubles entries and 126 distinct partners in total. The matrix is therefore sparse, and the
more informative column is the count of *different* partners per player: the cohort mostly plays
outside itself, and only Summer Tukua has a single partner all year.

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
