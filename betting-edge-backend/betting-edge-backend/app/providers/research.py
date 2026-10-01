from __future__ import annotations

import asyncio
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import feedparser
import httpx


class ResearchProvider:
    """
    Research layer using public/current sources.

    - Google News RSS for current news/injury/team reports
    - Open-Meteo for weather
    """

    def __init__(self):
        self.timeout = 15

    async def _get_text(self, url: str) -> str:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "BettingEdgeResearch/1.0"
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    @staticmethod
    def _clean_text(value: str) -> str:
        value = html.unescape(value or "")
        value = re.sub(r"<[^>]+>", "", value)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _published(entry) -> str | None:
        value = entry.get("published") or entry.get("updated")

        if not value:
            return None

        try:
            dt = parsedate_to_datetime(value)
            return dt.isoformat()
        except Exception:
            return value

    async def news(self, query: str, limit: int = 8):
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        )

        try:
            raw = await self._get_text(url)
            feed = feedparser.parse(raw)

            results = []

            for entry in feed.entries[:limit]:
                results.append(
                    {
                        "title": self._clean_text(
                            entry.get("title", "")
                        ),
                        "source": self._clean_text(
                            entry.get("source", {}).get(
                                "title", ""
                            )
                        ),
                        "url": entry.get("link"),
                        "published": self._published(entry),
                        "summary": self._clean_text(
                            entry.get("summary", "")
                        ),
                    }
                )

            return results

        except Exception as exc:
            return [
                {
                    "title": "News search unavailable",
                    "source": "Research service",
                    "url": None,
                    "published": None,
                    "summary": str(exc),
                }
            ]

    async def weather(
        self,
        latitude: float,
        longitude: float,
    ):
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current=temperature_2m,wind_speed_10m,"
            "precipitation,weather_code"
            "&hourly=temperature_2m,precipitation_probability,"
            "wind_speed_10m,weather_code"
            "&temperature_unit=fahrenheit"
            "&wind_speed_unit=mph"
            "&forecast_days=2"
        )

        async with httpx.AsyncClient(
            timeout=self.timeout
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def research_game(
        self,
        home_team: str,
        away_team: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ):
        queries = [
            f'"{home_team}" "{away_team}" injury',
            f'"{home_team}" "{away_team}" injuries',
            f'"{home_team}" "{away_team}" lineup',
            f'"{home_team}" "{away_team}" weather',
            f'"{home_team}" "{away_team}" news',
        ]

        news_results = await asyncio.gather(
            *(self.news(query, limit=6) for query in queries)
        )

        flattened = []

        seen_urls = set()

        for results in news_results:
            for item in results:
                url = item.get("url")

                if url and url in seen_urls:
                    continue

                if url:
                    seen_urls.add(url)

                flattened.append(item)

        injury_items = []
        lineup_items = []
        weather_items = []

        for item in flattened:
            title = (
                item.get("title", "")
                + " "
                + item.get("summary", "")
            ).lower()

            if any(
                word in title
                for word in [
                    "injury",
                    "injured",
                    "questionable",
                    "doubtful",
                    "out",
                    "ir ",
                    "inactive",
                    "limited",
                ]
            ):
                injury_items.append(item)

            if any(
                word in title
                for word in [
                    "lineup",
                    "starter",
                    "starting",
                    "active",
                    "inactive",
                ]
            ):
                lineup_items.append(item)

            if any(
                word in title
                for word in [
                    "weather",
                    "wind",
                    "rain",
                    "snow",
                    "temperature",
                ]
            ):
                weather_items.append(item)

        weather_data = None

        if latitude is not None and longitude is not None:
            try:
                weather_data = await self.weather(
                    latitude,
                    longitude,
                )
            except Exception as exc:
                weather_data = {
                    "error": str(exc)
                }

        return {
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "teams": {
                "home": home_team,
                "away": away_team,
            },
            "injuries": injury_items[:10],
            "lineups": lineup_items[:10],
            "weather_news": weather_items[:10],
            "all_news": flattened[:20],
            "weather": weather_data,
        }
