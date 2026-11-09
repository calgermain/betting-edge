from __future__ import annotations

import asyncio
import html
import re
from datetime import datetime, timezone, timedelta
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
            # An upstream failure is not a news article or injury report.
            return []

    async def weather(self, latitude: float, longitude: float, kickoff: str | None = None):
        """Forecast near kickoff, never silently substitute current conditions."""
        if not kickoff:
            return {"status": "missing_kickoff"}
        try:
            target = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            if target.tzinfo is None:
                return {"status": "invalid_kickoff"}
            target = target.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return {"status": "invalid_kickoff"}

        now = datetime.now(timezone.utc)
        if target < now - timedelta(hours=2):
            return {"status": "past_game"}
        if target > now + timedelta(days=15):
            return {"status": "outside_forecast_window"}

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude, "longitude": longitude,
            "hourly": "temperature_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m,weather_code",
            "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
            "timezone": "GMT", "forecast_days": 16,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        if not times:
            return {"status": "unavailable"}
        samples = []
        for i, timestamp in enumerate(times):
            try:
                dt = datetime.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if abs((dt - target).total_seconds()) <= 1800:
                samples.append((abs((dt - target).total_seconds()), i, dt))
        if not samples:
            return {"status": "outside_forecast_window"}
        _, i, sample_time = min(samples)
        def metric(key):
            values = hourly.get(key) or []
            return values[i] if i < len(values) else None
        return {
            "status": "forecast",
            "forecast_for": sample_time.isoformat(),
            "kickoff": target.isoformat(),
            "temperature_2m": metric("temperature_2m"),
            "precipitation_probability": metric("precipitation_probability"),
            "precipitation": metric("precipitation"),
            "wind_speed_10m": metric("wind_speed_10m"),
            "wind_gusts_10m": metric("wind_gusts_10m"),
            "weather_code": metric("weather_code"),
            "source": "open-meteo",
        }

    async def research_game(
        self,
        home_team: str,
        away_team: str,
        latitude: float | None = None,
        longitude: float | None = None,
        kickoff: str | None = None,
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

        injury_pattern = re.compile(
            r"\b(?:injury|injuries|injured|questionable|doubtful|"
            r"out|inactive|limited|ruled out)\b",
            re.IGNORECASE,
        )

        for item in flattened:
            title = (
                item.get("title", "")
                + " "
                + item.get("summary", "")
            ).lower()

            if injury_pattern.search(title):
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
                    kickoff,
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
