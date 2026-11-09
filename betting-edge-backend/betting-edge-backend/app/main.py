from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .providers.odds_api import OddsApiProvider, OddsApiError
from .providers.research import ResearchProvider
from .normalizer import normalize_odds
from .calculations import implied_probability, american_odds, edge
from .nfl_venues import nfl_home_venue
from .player_trends import PlayerTrendRequest, analyze_player_trend
from .player_csv import analyze_csv, PlayerCsvError
from .nflverse_stats import weekly_rows, analyze_weekly, StatsUnavailable, MARKETS
from .nfl_projection import baseline
from pydantic import BaseModel, Field


# =========================================================
# SETTINGS / APP
# =========================================================

settings = get_settings()

app = FastAPI(
    title="Betting Edge API",
    version="0.2.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# =========================================================
# PROVIDERS
# =========================================================

provider = OddsApiProvider(
    settings.odds_api_key,
    settings.odds_api_base_url,
)

research = ResearchProvider()


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "betting-edge-api",
        "version": "0.2.0",
        "time": datetime.now(timezone.utc),
    }


# =========================================================
# SPORTS
# =========================================================

@app.get("/api/v1/sports")
async def sports():
    try:
        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "data": await provider.sports(),
        }

    except OddsApiError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# =========================================================
# EVENTS
# =========================================================

@app.get("/api/v1/events")
async def events(
    sport: str = "americanfootball_nfl",
):
    try:
        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "data": await provider.events(sport),
        }

    except OddsApiError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# =========================================================
# STANDARD ODDS
# =========================================================

@app.get("/api/v1/odds")
async def odds(
    sport: str = "americanfootball_nfl",
    markets: str = "h2h,spreads,totals",
    regions: str = "us",
    bookmakers: str | None = None,
):
    try:
        raw, quota = await provider.odds(
            sport=sport,
            regions=regions,
            markets=markets,
            bookmakers=bookmakers,
        )

        normalized = normalize_odds(raw)

        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "quota": quota,
            "data": [
                item.model_dump(mode="json")
                for item in normalized
            ],
        }

    except OddsApiError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# =========================================================
# PLAYER PROPS
# =========================================================

@app.get("/api/v1/events/{event_id}/props")
async def props(
    event_id: str,
    sport: str = "americanfootball_nfl",
    markets: str = (
        "player_rush_yds,"
        "player_reception_yds"
    ),
    regions: str = "us",
    bookmakers: str | None = None,
):
    try:
        raw, quota = await provider.event_props(
            sport=sport,
            event_id=event_id,
            regions=regions,
            markets=markets,
            bookmakers=bookmakers,
        )

        normalized = normalize_odds([raw])

        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "quota": quota,
            "data": (
                normalized[0].model_dump(mode="json")
                if normalized
                else None
            ),
        }

    except OddsApiError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# =========================================================
# EVENT MARKETS
# =========================================================

@app.get("/api/v1/events/{event_id}/markets")
async def markets(
    event_id: str,
    sport: str = "americanfootball_nfl",
    regions: str = "us",
):
    try:
        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "data": await provider.event_markets(
                sport=sport,
                event_id=event_id,
                regions=regions,
            ),
        }

    except OddsApiError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# =========================================================
# RESEARCH LAYER
# =========================================================

@app.get("/api/v1/research/game")
async def research_game(
    home_team: str = Query(...),
    away_team: str = Query(...),
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    kickoff: str | None = Query(None),
):
    """
    Collect current research for a selected game.

    Sources currently include:
    - Google News RSS
    - Open-Meteo weather
    """

    try:
        venue = nfl_home_venue(home_team)
        # The NFL venue table is used only when the request is for NFL.
        # Explicit coordinates take precedence (e.g. international games).
        if latitude is None and longitude is None and venue:
            if venue["outdoor"]:
                latitude, longitude = venue["latitude"], venue["longitude"]
        data = await research.research_game(
            home_team=home_team,
            away_team=away_team,
            latitude=latitude,
            longitude=longitude,
            kickoff=kickoff,
        )
        data["venue"] = venue
        if venue and not venue["outdoor"] and latitude is None:
            data["weather_note"] = "Indoor/roofed venue; outdoor weather is not representative of playing conditions."

        return {
            "source": "public-current-sources",
            "fetched_at": datetime.now(timezone.utc),
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail="Research request failed.",
        )


# =========================================================
# RESEARCH NEWS
# =========================================================

@app.get("/api/v1/research/news")
async def research_news(
    query: str = Query(...),
    limit: int = Query(
        8,
        ge=1,
        le=20,
    ),
):
    """
    Search current news for a team, player,
    matchup, injury situation, etc.
    """

    try:
        data = await research.news(
            query=query,
            limit=limit,
        )

        return {
            "source": "google-news-rss",
            "fetched_at": datetime.now(timezone.utc),
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"News request failed: {e}",
        )


# =========================================================
# RESEARCH WEATHER
# =========================================================

@app.get("/api/v1/research/weather")
async def research_weather(
    latitude: float,
    longitude: float,
    kickoff: str | None = Query(None),
):
    """
    Current and forecast weather for a game location.
    """

    try:
        data = await research.weather(
            latitude=latitude,
            longitude=longitude,
            kickoff=kickoff,
        )

        return {
            "source": "open-meteo",
            "fetched_at": datetime.now(timezone.utc),
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail="Weather request failed.",
        )


# =========================================================
# CALCULATIONS — IMPLIED PROBABILITY
# =========================================================

@app.get("/api/v1/calculations/implied")
async def calc_implied(
    odds: float,
):
    probability = implied_probability(odds)

    return {
        "american_odds": odds,
        "implied_probability": probability,
        "fair_american_odds": american_odds(
            probability
        ),
    }


# =========================================================
# CALCULATIONS — EDGE
# =========================================================

@app.get("/api/v1/calculations/edge")
async def calc_edge(
    odds: float,
    estimated_probability: float,
):
    probability = implied_probability(odds)

    return {
        "american_odds": odds,
        "estimated_probability": estimated_probability,
        "implied_probability": probability,
        "edge": edge(
            estimated_probability,
            odds,
        ),
        "fair_american_odds": american_odds(
            estimated_probability
        ),
    }


# =========================================================
# NFL PLAYER TRENDS — CALLER-SUPPLIED VERIFIED GAME LOGS
# =========================================================

@app.post("/api/v1/nfl/player-trends")
async def nfl_player_trends(request: PlayerTrendRequest):
    return {"source": "caller-supplied-game-logs", "data": analyze_player_trend(request)}


class NflPlayerCsvRequest(BaseModel):
    player: str = Field(min_length=1, max_length=120)
    market: str
    line: float = Field(ge=0, allow_inf_nan=False)
    csv_text: str = Field(min_length=1, max_length=32_000)


@app.post("/api/v1/nfl/player-trends/csv")
async def nfl_player_trends_csv(request: NflPlayerCsvRequest):
    try:
        result = analyze_csv(request.player, request.market, request.line, request.csv_text)
    except PlayerCsvError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"source": "caller-supplied-csv", "data": result}


@app.get("/api/v1/nfl/player-stats")
async def nfl_player_stats(
    player: str = Query(..., min_length=2, max_length=120),
    market: str = Query(...),
    line: float = Query(..., ge=0, allow_inf_nan=False),
    season: int = Query(2026, ge=1999, le=2100),
    player_id: str | None = Query(None, max_length=80),
    opponent: str | None = Query(None, max_length=5),
):
    """Historical nflverse weekly stats; cached and free of sportsbook API calls."""
    if season > datetime.now(timezone.utc).year:
        raise HTTPException(status_code=422, detail="Season cannot be in the future.")
    if market not in MARKETS:
        raise HTTPException(status_code=422, detail="Unsupported NFL player market.")
    try:
        rows, freshness = await weekly_rows(season)
        data = analyze_weekly(rows, player, market, line, season, player_id)
        projection = baseline(data["games"], line, opponent) if data["status"] == "ok" else None
        return {"source": "nflverse", "freshness": freshness, "data": data,
                "projection": projection}
    except StatsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
