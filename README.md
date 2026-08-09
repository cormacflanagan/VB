# Beach NTDP Girls — Tournament Analysis

Cross-references the rosters of USA Volleyball's 2026 Beach NTDP Summer Training Series
against each athlete's competition record on [Volleyball Life](https://volleyballlife.com),
for the twelve months ending **9 August 2026**.

Two groups are covered:

| Group | Athletes | Report |
| --- | --- | --- |
| Girls U18 | 13 | [`docs/bntdp-18u.html`](docs/bntdp-18u.html) |
| Girls U17 | 20 | [`docs/bntdp-17u.html`](docs/bntdp-17u.html) |

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

## Data sources

All read from the Volleyball Life public API at `https://api-v8.volleyballlife.com`:

| Endpoint | Provides |
| --- | --- |
| `GET /playerprofile/search/{name}` | Player lookup, used to resolve roster names to IDs |
| `GET /playerprofile/{id}` | Tournament history including `tdId` (tournament-division ID) |
| `GET /playerprofile/{id}/truvolley` | TruVolley rating, peak, confidence, win/loss record |
| `POST /Tournament/CountsV3Bulk` | Team count per division — the field size denominator |

Field size comes from the team count of the specific division the athlete competed in,
matched by `tdId`. Division names alone are not sufficient: one event runs several
divisions of very different sizes.

## Pipeline

```
python3 scripts/collect_group.py 17U 18U   # fetch  -> data/<group>_clean.json, <group>_site.json
python3 scripts/render_group.py  17U 18U   # render -> docs/bntdp-<group>.html
```

Run with no arguments, both scripts process both groups. `scripts/resolve17.py` is the
one-off name-resolution helper used to build the U17 roster IDs; it is kept for auditing
and for adding future groups. `scripts/shortnames.json` maps full event names to the
abbreviations used in matrix column heads — anything not listed there is abbreviated
automatically at a word boundary.

`data/*_clean.json` and `data/*_site.json` are the retrieved snapshots, so the reports can
be regenerated without re-querying the API.

## What the two groups look like

| | Girls U18 | Girls U17 |
| --- | --- | --- |
| Athletes | 13 | 20 |
| Events attended | 100 | 135 |
| Competitions (event × division) | 116 | 172 |
| Shared by 3 or more | 26 | 33 |
| Shared by exactly 2 | 27 | 38 |
| Largest single turnout | 12 of 13 (U18 Trials) | 9 of 20 |

The U18 group is far more concentrated: the U18 Beach National Team Trials put 12 of its
13 into one 12-team field, and three more competitions drew 11. Nothing in the U17 year
gathers more than 9 of the 20, because that cohort splits across 15U, 16U, 17U and 18U
brackets rather than converging on a single selection event.

## Caveats

- **Athletes who enter two divisions at one event** appear once in each division's column,
  which is the point of the split — at AVP Juniors Nationals, Olivia Herron was 9th of 64
  in 18U and 63rd of 63 in 17U.
- **Coach and spectator registrations appear in player histories** with a finish of 1.
  These are filtered out, otherwise they show up as phantom wins.
- **Some competitions are club or five-a-side formats**, not pairs — the BVCA Orange
  County dates, Club v Club and the AAU club championships. A finish there reflects a
  squad rather than a duo; the division label names them.
- **Ties are shared.** Beach draws award equal finishes to teams knocked out in the same
  round, which is why blocks of 5th, 9th and 17th recur.
- **A few field sizes are unavailable** where Volleyball Life reports a division team
  count of zero; those cells show the finish with the field marked as unavailable.
