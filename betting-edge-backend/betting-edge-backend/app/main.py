from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .providers.odds_api import OddsApiProvider, OddsApiError
from .providers.research import ResearchProvider
from .normalizer import normalize_odds
from .calculations import implied_probability, american_odds, edge


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
):
    """
    Collect current research for a selected game.

    Sources currently include:
    - Google News RSS
    - Open-Meteo weather
    """

    try:
        data = await research.research_game(
            home_team=home_team,
            away_team=away_team,
            latitude=latitude,
            longitude=longitude,
        )

        return {
            "source": "public-current-sources",
            "fetched_at": datetime.now(timezone.utc),
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Research request failed: {e}",
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
):
    """
    Current and forecast weather for a game location.
    """

    try:
        data = await research.weather(
            latitude=latitude,
            longitude=longitude,
        )

        return {
            "source": "open-meteo",
            "fetched_at": datetime.now(timezone.utc),
            "data": data,
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Weather request failed: {e}",
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
