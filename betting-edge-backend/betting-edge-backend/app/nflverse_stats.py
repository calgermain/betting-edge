"""Read public nflverse weekly NFL player stats without Odds API requests.

Source: https://github.com/nflverse/nflverse-data/releases/tag/stats_player
The published CSV is a season-wide snapshot, cached for six hours in-process.
Weekly values are historical observations, not betting probabilities.
"""
from __future__ import annotations

import asyncio
import csv
import io
import math
import re
import time
from datetime import datetime, timezone
from statistics import mean, median

import httpx

SOURCE = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{season}.csv"
MARKETS = {
    "passing_yards": "passing_yards",
    "rushing_yards": "rushing_yards",
    "receiving_yards": "receiving_yards",
    "receptions": "receptions",
    "passing_tds": "passing_tds",
    "rushing_tds": "rushing_tds",
    "receiving_tds": "receiving_tds",
}
_cache: dict[int, tuple[float, list[dict], str]] = {}
_locks: dict[int, asyncio.Lock] = {}
TTL_SECONDS = 6 * 60 * 60
MAX_BYTES = 15_000_000


class StatsUnavailable(Exception):
    pass


def _name(value: str) -> str:
    """Normalize punctuation and common suffixes; never fuzzy-guess identities."""
    value = (value or "").casefold().replace("’", "'")
    tokens = re.findall(r"[a-z0-9]+", value)
    if tokens and tokens[-1] in {"jr", "sr", "ii", "iii", "iv"}:
        tokens.pop()
    return "".join(tokens)


async def weekly_rows(season: int) -> tuple[list[dict], dict]:
    cached = _cache.get(season)
    if cached and time.monotonic() - cached[0] < TTL_SECONDS:
        return cached[1], _metadata(cached, False)
    lock = _locks.setdefault(season, asyncio.Lock())
    async with lock:
        cached = _cache.get(season)
        if cached and time.monotonic() - cached[0] < TTL_SECONDS:
            return cached[1], _metadata(cached, False)
        url = SOURCE.format(season=season)
        try:
            async with httpx.AsyncClient(timeout=35, follow_redirects=True) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    parts = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise StatsUnavailable("Season file exceeds size limit")
                        parts.append(chunk)
            raw = b"".join(parts).decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(raw))
            required = {"season", "week", "player_id", "player_display_name", "season_type"}
            if not required.issubset(set(reader.fieldnames or [])):
                raise StatsUnavailable("Unexpected nflverse data schema")
            rows = list(reader)
            entry = (time.monotonic(), rows, datetime.now(timezone.utc).isoformat())
            _cache[season] = entry
            return rows, _metadata(entry, False)
        except (httpx.HTTPError, UnicodeError, csv.Error) as exc:
            if cached:
                return cached[1], _metadata(cached, True)
            raise StatsUnavailable("NFL weekly stats source unavailable") from exc


def _metadata(entry: tuple, stale: bool) -> dict:
    return {
        "fetched_at": entry[2],
        "cache_age_seconds": max(0, int(time.monotonic() - entry[0])),
        "stale": stale,
        "source_status": "stale_fallback" if stale else "cached_or_fresh",
    }


def analyze_weekly(rows: list[dict], player: str, market: str, line: float,
                   season: int, player_id: str | None = None) -> dict:
    if market not in MARKETS:
        raise ValueError("Unsupported player market")
    matching = [
        row for row in rows
        if (row.get("player_id") == player_id if player_id
            else _name(row.get("player_display_name", "")) == _name(player))
        and row.get("season_type") == "REG"
        and str(row.get("season")) == str(season)
    ]
    ids = {row.get("player_id") for row in matching}
    if not matching:
        return {"status": "not_found", "player": player, "season": season,
                "message": "No exact normalized player match. Verify spelling and season."}
    if len(ids) > 1:
        return {"status": "ambiguous_player", "player": player, "season": season,
                "player_ids": sorted(str(x) for x in ids if x)}
    games = []
    for row in matching:
        try:
            week = int(row["week"])
            value = float(row[MARKETS[market]])
            if not math.isfinite(value) or value < 0:
                continue
            games.append({"week": week, "opponent": row.get("opponent_team"),
                          "team": row.get("team") or row.get("recent_team"),
                          "value": value})
        except (KeyError, TypeError, ValueError):
            continue
    # A missing game is not a zero-yard performance. Never impute weeks.
    games.sort(key=lambda row: row["week"], reverse=True)
    if not games:
        return {"status": "no_market_data", "player": player, "season": season}
    values = [game["value"] for game in games]
    recent = values[:5]
    over = sum(v > line for v in values)
    under = sum(v < line for v in values)
    return {
        "status": "ok", "player": player, "player_id": next(iter(ids)),
        "market": market, "line": line, "season": season,
        "sample_size": len(values), "games": games[:25],
        "latest_week": games[0]["week"],
        "average": round(mean(values), 2), "median": round(median(values), 2),
        "last_5_average": round(mean(recent), 2),
        "last_5_values": recent,
        "over_count": over, "under_count": under,
        "push_count": len(values) - over - under,
        "historical_over_rate": round(over / len(values), 4),
        "methodology": "Historical weekly stats only; not a predictive probability or betting edge.",
        "source": SOURCE.format(season=season),
    }
