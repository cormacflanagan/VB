# Beach NTDP Girls — Tournament Analysis

Cross-references the rosters of USA Volleyball's 2026 Beach NTDP Summer Training Series
against each athlete's competition record on [Volleyball Life](https://volleyballlife.com),
for the twelve months ending **9 August 2026**.

Three groups are covered:

| Group | Athletes | Source | Report |
| --- | --- | --- | --- |
| Girls U18 | 13 | Published NTDP roster | [`docs/bntdp-18u.html`](docs/bntdp-18u.html) |
| Girls U17 | 20 | Published NTDP roster | [`docs/bntdp-17u.html`](docs/bntdp-17u.html) |
| Class of 2028 | 30 | Derived — see below | [`docs/bntdp-2028.html`](docs/bntdp-2028.html) |

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

## The class-of-2028 group

Volleyball Life publishes no class ranking, so this group is derived rather than read off a
page. `scripts/discover2028.py` crawls the partner graph outward from 16 known 2028 athletes
on the two NTDP rosters, keeping every player whose profile reports `gradYear == 2028` and
`male == false`, to two hops. That found **449 girls in the class, 410 of them rated**; the
30 highest TruVolley scores become the roster (`scripts/roster_2028.json`, full population in
`data/pop2028.json`).

A convergence pass then expanded the partners of the top 60 — 985 previously unseen player
IDs, of which 50 turned out to be class-of-2028 girls, and **none scored above the #30
cut-off** (7.906). The top 30 is therefore stable with respect to the crawl. The cut is tight
though: #31 is Regina Stella Broshear at 7.843, 0.06 behind #30.

Because the group is 30 rather than 13, its matrix uses a shared-by-5 threshold instead of 3;
proportionally that is a slightly weaker bar than the NTDP groups' 3-of-13.

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

| | Girls U18 | Girls U17 | Class of 2028 |
| --- | --- | --- | --- |
| Athletes | 13 | 20 | 30 |
| Events attended (doubles) | 89 | 111 | 143 |
| Pairs competitions (event × division) | 105 | 142 | 174 |
| Matrix threshold | 3+ | 3+ | 5+ |
| Matrix columns | 20 | 25 | 20 |
| Shared by exactly 2 | 25 | 30 | 45 |
| Club results dropped | 40 | 73 | 75 |
| Largest single turnout | 12 of 13 (U18 Trials) | 9 of 20 | 13 of 30 |

The U18 group is far more concentrated: the U18 Beach National Team Trials put 12 of its
13 into one 12-team field, and two more competitions drew 11. Nothing in the U17 year
gathers more than 9 of the 20, because that cohort splits across 15U, 16U, 17U and 18U
brackets rather than converging on a single selection event.

Dropping club formats hit the U17 group hardest — 73 results removed against the U18s' 40 —
and removed the BVCA Orange County 5v5 series, which had been the U17s' densest column.

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
