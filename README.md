# BNTDP 18U Girls — Tournament Analysis

Cross-references the **Girls U18 roster** of USA Volleyball's 2026 Beach NTDP Summer
Training Series against each athlete's competition record on
[Volleyball Life](https://volleyballlife.com), for the twelve months ending
**9 August 2026**.

The output is a players × tournaments matrix: every cell is a finish over the size of
the field in that athlete's division, alongside each player's TruVolley rating.

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
| `scripts/build.py` | Shapes the matrix and shared-event list → `site_data.json` |
| `scripts/render.py` | Emits the static HTML report → `bntdp.html` |

`data/clean.json` and `data/site_data.json` are the retrieved snapshots, so the report
can be regenerated without re-querying the API.

## Caveats

- **Athletes enter multiple divisions at one event.** The matrix shows the better finish
  and marks the cell; the second entry is listed in the report's notes.
- **Coach and spectator registrations appear in player histories.** These are filtered
  out, otherwise they show up as bogus first-place finishes.
- **Some events are 5-a-side club competitions**, not pairs — the BVCA Orange County
  dates and Club v Club. A finish there reflects a squad, not a duo.
- **Ties are shared.** Beach draws award equal finishes to teams knocked out in the same
  round, which is why blocks of 5th, 9th and 17th recur.
- **One field size is unavailable** (Surf City/World Mega College Showcase, Girls 16U)
  where Volleyball Life reports a team count of zero.
