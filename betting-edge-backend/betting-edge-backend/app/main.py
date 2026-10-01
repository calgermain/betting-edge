from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .providers.odds_api import (
    OddsApiProvider,
    OddsApiError,
)
from .normalizer import normalize_odds
from .calculations import (
    implied_probability,
    american_odds,
    edge,
)
from .providers.weather import WeatherProvider, WeatherProviderError
from .providers.news import NewsProvider, NewsProviderError
weather_provider = WeatherProvider()
news_provider = NewsProvider()
@app.get("/api/v1/research")
async def research(
    event_id: str,
    sport: str = "americanfootball_nfl",
    news_query: str | None = None,
):
    """
    Gather current research surrounding a selected event.

    This endpoint intentionally does not manufacture a probability.
    It returns the underlying research inputs first.
    """

    event = None

    try:
        events = await provider.events(sport)

        for candidate in events:
            if candidate.get("id") == event_id:
                event = candidate
                break

        if not event:
            raise HTTPException(
                404,
                "Event not found."
            )

        home_team = event.get("home_team", "")
        away_team = event.get("away_team", "")

        query = news_query or (
            f'"{home_team}" OR "{away_team}" '
            f'NFL injury news'
        )

        news = await news_provider.search(
            query,
            limit=10,
        )

        return {
            "event": {
                "id": event.get("id"),
                "sport_key": event.get("sport_key"),
                "sport_title": event.get("sport_title"),
                "commence_time": event.get(
                    "commence_time"
                ),
                "home_team": home_team,
                "away_team": away_team,
            },
            "research": {
                "news": news,
                "news_query": query,
            },
            "model_status": (
                "RESEARCH DATA GATHERED — "
                "PROBABILITY MODEL NOT YET APPLIED"
            ),
            "fetched_at": datetime.now(timezone.utc),
        }

    except NewsProviderError as exc:
        raise HTTPException(
            502,
            str(exc)
        )

    except OddsApiError as exc:
        raise HTTPException(
            502,
            str(exc)
        )


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


provider = OddsApiProvider(
    settings.odds_api_key,
    settings.odds_api_base_url,
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "betting-edge-api",
        "time": datetime.now(timezone.utc),
    }


@app.get("/api/v1/sports")
async def sports():
    try:
        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "data": await provider.sports(),
        }

    except OddsApiError as e:
        raise HTTPException(502, str(e))


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
        raise HTTPException(502, str(e))


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
                item.model_dump(mode="json")
                for item in normalized
            ],
        }

    except OddsApiError as e:
        raise HTTPException(502, str(e))


@app.get("/api/v1/events/{event_id}/odds")
async def event_odds(
    event_id: str,
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

        matching = [
            item
            for item in raw
            if item.get("id") == event_id
        ]

        normalized = normalize_odds(matching)

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
        raise HTTPException(502, str(e))


@app.get("/api/v1/events/{event_id}/props")
async def props(
    event_id: str,
    sport: str = "americanfootball_nfl",
    markets: str = (
        "player_pass_yds,"
        "player_pass_tds,"
        "player_rush_yds,"
        "player_rush_attempts,"
        "player_reception_yds,"
        "player_receptions,"
        "player_anytime_td"
    ),
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
        raise HTTPException(502, str(e))


@app.get("/api/v1/events/{event_id}/markets")
async def markets(
    event_id: str,
    sport: str = "americanfootball_nfl",
    regions: str = "us",
):
    try:
        data, quota = await provider.event_markets(
            sport,
            event_id,
            regions,
        )

        return {
            "source": "the-odds-api",
            "fetched_at": datetime.now(timezone.utc),
            "quota": quota,
            "data": data,
        }

    except OddsApiError as e:
        raise HTTPException(502, str(e))


@app.get("/api/v1/calculations/implied")
async def calc_implied(odds: float):
    probability = implied_probability(odds)

    return {
        "american_odds": odds,
        "implied_probability": probability,
        "fair_american_odds": american_odds(
            probability
        ),
    }


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
