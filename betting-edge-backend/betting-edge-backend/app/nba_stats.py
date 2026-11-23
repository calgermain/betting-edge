"""Cached NBA player game logs from SportsDataverse/hoopR (no Odds API credits).

Season is the END year: 2027 means the 2026-27 season.
These are historical observations, not injury-adjusted forecasts or bet advice.
"""
from __future__ import annotations

import asyncio
import io
import math
import re
import time
from datetime import datetime, timezone
from statistics import mean

import httpx

SOURCE = ("https://github.com/sportsdataverse/sportsdataverse-data/releases/"
          "download/nba_stats_player_game_logs/player_game_logs_{season}.parquet")
MARKETS = {"points": "pts", "rebounds": "reb", "assists": "ast",
           "threes": "fg3m", "minutes": "min", "pra": None}
TTL_SECONDS = 6 * 60 * 60
MAX_BYTES = 12_000_000
_cache: dict[int, tuple[float, list[dict], str]] = {}
_locks: dict[int, asyncio.Lock] = {}


class NBAStatsUnavailable(Exception):
    pass


def _name(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", (value or "").casefold())
    if tokens and tokens[-1] in {"jr", "sr", "ii", "iii", "iv"}:
        tokens.pop()
    return "".join(tokens)


def _parse_parquet(raw: bytes) -> list[dict]:
    import pyarrow.parquet as pq
    table = pq.read_table(io.BytesIO(raw))
    required = {"player_id", "player_name", "game_id", "game_date", "season_type",
                "pts", "reb", "ast", "fg3m", "min"}
    if not required.issubset(table.column_names):
        raise NBAStatsUnavailable("Unexpected hoopR player-game-log schema")
    return table.select(sorted(required | ({"team_abbreviation"} & set(table.column_names)))).to_pylist()


async def season_rows(season: int) -> tuple[list[dict], dict]:
    cached = _cache.get(season)
    if cached and time.monotonic() - cached[0] < TTL_SECONDS:
        return cached[1], _meta(cached, False)
    lock = _locks.setdefault(season, asyncio.Lock())
    async with lock:
        cached = _cache.get(season)
        if cached and time.monotonic() - cached[0] < TTL_SECONDS:
            return cached[1], _meta(cached, False)
        try:
            async with httpx.AsyncClient(timeout=40, follow_redirects=True) as client:
                async with client.stream("GET", SOURCE.format(season=season)) as response:
                    response.raise_for_status()
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise NBAStatsUnavailable("NBA season file exceeds size limit")
                        chunks.append(chunk)
            rows = await asyncio.to_thread(_parse_parquet, b"".join(chunks))
            entry = (time.monotonic(), rows, datetime.now(timezone.utc).isoformat())
            _cache[season] = entry
            return rows, _meta(entry, False)
        except (httpx.HTTPError, OSError, ValueError, NBAStatsUnavailable) as exc:
            if cached:
                return cached[1], _meta(cached, True)
            raise NBAStatsUnavailable("NBA hoopR season data unavailable") from exc


def _meta(entry: tuple, stale: bool) -> dict:
    return {"fetched_at": entry[2], "cache_age_seconds": int(time.monotonic()-entry[0]),
            "stale": stale, "source": SOURCE, "source_status": "stale_fallback" if stale else "cached_or_fresh"}


def player_research(rows: list[dict], player: str, season: int, market: str,
                    line: float | None = None, player_id: int | None = None) -> dict:
    if market not in MARKETS:
        raise ValueError("Unsupported NBA market")
    if line is not None and (not math.isfinite(line) or line < 0):
        raise ValueError("Invalid prop line")
    matching = [r for r in rows if str(r.get("season_type", "")).lower() == "regular-season"
                and (r.get("player_id") == player_id if player_id is not None
                     else _name(r.get("player_name", "")) == _name(player))]
    ids = {r["player_id"] for r in matching}
    if not matching:
        return {"status": "not_found", "player": player, "season": season}
    if len(ids) > 1:
        return {"status": "ambiguous_player", "player": player, "player_ids": sorted(ids)}
    games = []
    for row in matching:
        try:
            parts = [float(row[key]) for key in ("pts", "reb", "ast")]
            value = sum(parts) if market == "pra" else float(row[MARKETS[market]])
            minutes = float(row["min"])
            if not all(math.isfinite(v) and v >= 0 for v in (value, minutes)):
                continue
            games.append({"date": row["game_date"], "game_id": row["game_id"],
                          "team": row.get("team_abbreviation"), "value": value,
                          "minutes": minutes})
        except (KeyError, ValueError, TypeError):
            continue
    games.sort(key=lambda g: (str(g["date"]), str(g["game_id"])), reverse=True)
    if not games:
        return {"status": "no_market_data", "player": player, "season": season}
    values = [g["value"] for g in games]
    recent = values[:5]
    # Same exploratory baseline family as NFL: 60% last five, 40% season.
    projection = .6 * mean(recent) + .4 * mean(values)
    chronological = list(reversed(values))
    errors = []
    for i in range(5, len(chronological)):
        prior = chronological[:i]
        predicted = .6 * mean(prior[-5:]) + .4 * mean(prior)
        errors.append(abs(predicted - chronological[i]))
    result = {
        "status": "ok", "player": matching[0]["player_name"], "player_id": next(iter(ids)),
        "season": season, "market": market, "sample_size": len(games),
        "last_game_date": games[0]["date"], "season_average": round(mean(values), 2),
        "last_5_average": round(mean(recent), 2),
        "projected_stat": round(projection, 2),
        "walk_forward_mae": round(mean(errors), 2) if errors else None,
        "average_minutes": round(mean(g["minutes"] for g in games), 2),
        "last_5_minutes": round(mean(g["minutes"] for g in games[:5]), 2),
        "games": games[:15], "validated_probability": False,
        "injury_adjusted": False, "lineup_adjusted": False,
        "methodology": "60% last-five + 40% season mean; walk-forward MAE uses prior games only. "
                       "No injury, minutes forecast, matchup, or sportsbook calibration.",
    }
    if line is not None:
        result["line"] = line
        result["historical_over_rate"] = round(sum(v > line for v in values) / len(values), 4)
        result["historical_under_rate"] = round(sum(v < line for v in values) / len(values), 4)
    return result
