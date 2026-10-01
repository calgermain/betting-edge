from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .providers.odds_api import OddsApiProvider, OddsApiError
from .normalizer import normalize_odds
from .calculations import implied_probability, american_odds, edge


settings = get_settings()

app = FastAPI(
    title="Betting Edge API",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


provider = OddsApiProvider(
    settings.odds_api_key,
    settings.odds_api_base_url,
)


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "betting-edge-api",
        "time": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------
# SPORTS
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# EVENTS
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# ALL SPORT ODDS
# ---------------------------------------------------------

@app.get("/api/v1/odds")
async def odds(
    sport: str = "americanfootball_nfl",
    markets: str = "h2h,spreads,totals",
    regions: str = "us",
    bookmakers: str | None = None,
):
    try:
        raw, quota = await provider.odds(
            sport,
            regions,
            markets,
            bookmakers,
        )

        normalized = normalize_odds(raw)

        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "quota": quota,
            "data": [
                x.model_dump(mode="json")
                for x in normalized
            ],
        }

    except OddsApiError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# ---------------------------------------------------------
# SINGLE EVENT ODDS
# ---------------------------------------------------------

@app.get("/api/v1/events/{event_id}/odds")
async def event_odds(
    event_id: str,
    sport: str = "americanfootball_nfl",
    markets: str = "h2h,spreads,totals",
    regions: str = "us",
    bookmakers: str | None = None,
):
    try:
        raw, quota = await provider.event_props(
            sport,
            event_id,
            regions,
            markets,
            bookmakers,
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


# ---------------------------------------------------------
# PLAYER PROPS
# ---------------------------------------------------------

@app.get("/api/v1/events/{event_id}/props")
async def props(
    event_id: str,
    sport: str = "americanfootball_nfl",
    markets: str = "player_rush_yds,player_reception_yds",
    regions: str = "us",
    bookmakers: str | None = None,
):
    try:
        raw, quota = await provider.event_props(
            sport,
            event_id,
            regions,
            markets,
            bookmakers,
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


# ---------------------------------------------------------
# EVENT MARKETS
# ---------------------------------------------------------

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
                sport,
                event_id,
                regions,
            ),
        }

    except OddsApiError as e:
        raise HTTPException(
            status_code=502,
            detail=str(e),
        )


# ---------------------------------------------------------
# IMPLIED PROBABILITY
# ---------------------------------------------------------

@app.get("/api/v1/calculations/implied")
async def calc_implied(
    odds: float,
):
    p = implied_probability(odds)

    return {
        "american_odds": odds,
        "implied_probability": p,
        "fair_american_odds": american_odds(p),
    }


# ---------------------------------------------------------
# EDGE
# ---------------------------------------------------------

@app.get("/api/v1/calculations/edge")
async def calc_edge(
    odds: float,
    estimated_probability: float,
):
    p = implied_probability(odds)

    return {
        "american_odds": odds,
        "estimated_probability": estimated_probability,
        "implied_probability": p,
        "edge": edge(
            estimated_probability,
            odds,
        ),
        "fair_american_odds": american_odds(
            estimated_probability
        ),
    }
