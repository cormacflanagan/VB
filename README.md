# BNTDP 18U Girls — Tournament Analysis

Cross-references the **Girls U18 roster** of USA Volleyball's 2026 Beach NTDP Summer
Training Series against each athlete's competition record on
[Volleyball Life](https://volleyballlife.com), for the twelve months ending
**9 August 2026**.

**Each age division is treated as its own competition.** The 18U bracket and the 16U
bracket running beside it at the same event are different fields, so they are different
competitions. The output is a players × competitions matrix: every cell is a finishing
position, and the size of that field is carried in the column heading, alongside each
player's TruVolley rating.

Rendered report: [`docs/bntdp.html`](docs/bntdp.html)

## The roster

Thirteen athletes, from the USA Volleyball Beach NTDP Summer Training Series roster
page (Girls U18 group, Chula Vista, 26–30 July 2026):

| Athlete | USAV region | Volleyball Life ID |
| --- | --- | --- |
| Simrin Adams | So. Cal / So. Nevada | 25289 |
| Sarah Albers | Gateway | 84161 |
| Sienna Castillo | Northern California | 29854 |
| Sarah Cowan | Florida | 84725 |
| Sadie Harris | So. Cal / So. Nevada | 94909 |
| Olivia Herron | North Texas | 28688 |
| Sage Illian | Heart of America | 91052 |
| Lauren Leach | So. Cal / So. Nevada | 8426 |
| Georgeann Lee | Aloha | 61785 |
| Janie McCanna | Puget Sound | 24515 |
| Milaniakai Padilla | Aloha | 95165 |
| Sadie Stafford | Old Dominion | 147394 |
| Jordyn Wilson | So. Cal / So. Nevada | 23868 |

## Data sources

All read from the Volleyball Life public API at `https://api-v8.volleyballlife.com`:

| Endpoint | Provides |
| --- | --- |
| `GET /playerprofile/search/{name}` | Player lookup, used to resolve roster names to IDs |
| `GET /playerprofile/{id}` | Full tournament history including `tdId` (tournament-division ID) |
| `GET /playerprofile/{id}/finishes` | Tournament history with partners; cross-check on the above |
| `GET /playerprofile/{id}/truvolley` | TruVolley rating, peak, confidence, win/loss record |
| `POST /Tournament/CountsV3Bulk` | Team count per division — the field size denominator |

Field size comes from the team count of the specific division the athlete competed in,
matched by `tdId`. Division names alone are not sufficient: a single event runs several
divisions of different sizes.

## Pipeline

Run in order from the repository root; each step writes into the working directory.

| Script | Does |
| --- | --- |
| `scripts/search.py` | Resolves the 13 roster names to Volleyball Life player IDs |
| `scripts/collect.py` | Pulls finishes, TruVolley ratings and division counts → `raw.json` |
| `scripts/rebuild.py` | Re-keys entries by division, drops coach registrations → `clean.json` |
| `scripts/analyze.py`, `scripts/report.py` | Console summaries of shared events and placements |
| `scripts/build2.py` | Keys competitions by (event, division) → `site_data2.json` |
| `scripts/render2.py` | Emits the static HTML report → `bntdp.html` |

`data/clean.json` and `data/site_data2.json` are the retrieved snapshots, so the report
can be regenerated without re-querying the API. `scripts/shortnames.json` maps full event
names to the abbreviations used in the matrix column heads.

## What the split changes

Keying by division rather than by event turns 100 events into **116 competitions**. Of
those, 26 were entered by three or more of the roster and form the matrix; a further 27
drew exactly two and are listed separately as head-to-heads. The effect is largest for
athletes who compete outside 18U — Sadie Harris plays mostly 16U, so she shares 8
competitions with the group rather than the 15 events a division-blind count suggests.

## Caveats

- **Athletes who enter two divisions at one event** now appear once in each division's
  column, which is the point of the split — at AVP Juniors Nationals, Olivia Herron was
  9th of 64 in 18U and 63rd of 63 in 17U.
- **Coach and spectator registrations appear in player histories.** These are filtered
  out, otherwise they show up as bogus first-place finishes.
- **Some events are 5-a-side club competitions**, not pairs — the BVCA Orange County
  dates and Club v Club. A finish there reflects a squad, not a duo.
- **Ties are shared.** Beach draws award equal finishes to teams knocked out in the same
  round, which is why blocks of 5th, 9th and 17th recur.
- **One field size is unavailable** (Surf City/World Mega College Showcase, Girls 16U)
  where Volleyball Life reports a team count of zero.
