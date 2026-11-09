# Betting Edge Backend

FastAPI backend for the Betting Edge frontend.

## Local setup

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
# Put your real ODDS_API_KEY in .env
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Endpoints

GET /health
GET /api/v1/sports
GET /api/v1/events?sport=americanfootball_nfl
GET /api/v1/odds?sport=americanfootball_nfl&markets=h2h,spreads,totals
GET /api/v1/events/{event_id}/props?sport=americanfootball_nfl&markets=player_rush_yds,player_reception_yds

Never put ODDS_API_KEY in the public GitHub Pages frontend.


## NFL player trend research (no external API calls)

The backend provides descriptive game-log calculations, **not** win-probability
estimates or sportsbook recommendations. The caller must supply verified stats.

- `POST /api/v1/nfl/player-trends` accepts structured game logs.
- `POST /api/v1/nfl/player-trends/csv` accepts a CSV string.

Example CSV request:

```json
{
  "player": "Example Receiver",
  "market": "receiving_yards",
  "line": 65.5,
  "csv_text": "date,opponent,value,snaps\n2026-10-01,MIN,75,55\n2026-10-08,CHI,45,48"
}
```

CSV headers must be `date,opponent,value`, optionally `snaps`. Dates
are ISO `YYYY-MM-DD`; the maximum is 25 unique games. Supported markets:
`passing_yards`, `rushing_yards`, `receiving_yards`, `receptions`,
`passing_tds`, `rushing_tds`, and `receiving_tds`.

Results report sample size, averages, last-five values, over/under/push counts,
and historical hit rates. These are historical descriptions only; no predictive
probability is implied.

To run offline tests from the Render root directory:
```bash
pip install pytest
python -m pytest -q
```

## Game-time weather

`GET /api/v1/research/game` accepts `kickoff` as an ISO 8601 timestamp
with timezone, in addition to home and away teams. Outdoor NFL home venues
are looked up from the stadium table. Open-Meteo hourly weather is requested
near kickoff when it falls within the forecast horizon. Missing, past and
out-of-range forecasts have explicit status values. Indoor/roofed venues
suppress outdoor weather. Neutral-site games and retractable-roof decisions
still require explicit venue verification.


## Automatic NFL player game logs (nflverse)

`GET /api/v1/nfl/player-stats?player=Example%20Receiver&market=receiving_yards&line=65.5&season=2026`

Fetches the public nflverse `stats_player_week_{season}.csv` release, caches
the season CSV in memory for six hours, and calculates descriptive statistics
from regular-season player-week records. Subsequent player requests reuse the
cached season data. No Odds API request is made. This is an independent,
community-maintained source and its availability/freshness can vary.

Name matching is exact after basic punctuation normalization. If two players
share the same name, the API returns `ambiguous_player` and player IDs
rather than guessing. Supply `player_id` to select a specific player.
The response includes weekly values and the upstream source URL, not a
predictive probability. Player stats are not yet connected to the frontend UI.

Data: nflverse (CC BY 4.0). Attribution: https://github.com/nflverse/nflverse-data
