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
