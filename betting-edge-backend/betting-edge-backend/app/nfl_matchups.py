"""Descriptive opponent defensive allowance context from prior NFL player-week logs.

Never converts a defensive matchup into a calibrated probability or betting edge.
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
import math

from .nflverse_stats import MARKETS


def defensive_context(rows: list[dict], season: int, market: str,
                      opponent: str, position: str, before_week: int | None = None,
                      min_weeks: int = 4) -> dict:
    """Aggregate weekly defense totals for a position; exclude weeks >= before_week.

    League baseline uses defense-week totals, including weeks with no matching player
    rows as zero only when those weeks can be observed elsewhere in the dataset.
    """
    if market not in MARKETS:
        raise ValueError("Unsupported market")
    opponent = opponent.strip().upper()
    position = position.strip().upper()
    if not opponent or not position:
        return {"status": "missing_context"}
    # Collect actual defense-week appearances from ALL regular-season player rows.
    observed = set()
    totals = defaultdict(float)
    for row in rows:
        if str(row.get("season")) != str(season) or row.get("season_type") != "REG":
            continue
        try:
            week = int(row["week"])
        except (ValueError, TypeError, KeyError):
            continue
        if before_week is not None and week >= before_week:
            continue
        defense = str(row.get("opponent_team") or "").upper()
        if not defense:
            continue
        observed.add((defense, week))
        if str(row.get("position") or "").upper() != position:
            continue
        try:
            value = float(row[MARKETS[market]])
        except (ValueError, TypeError, KeyError):
            continue
        if math.isfinite(value) and value >= 0:
            totals[(defense, week)] += value
    opponent_values = [totals.get(key, 0.0) for key in observed if key[0] == opponent]
    if len(opponent_values) < min_weeks:
        return {"status": "insufficient_sample", "opponent": opponent,
                "position": position, "sample_weeks": len(opponent_values),
                "minimum_weeks": min_weeks}
    league_values = [totals.get(key, 0.0) for key in observed]
    league_average = mean(league_values)
    opponent_average = mean(opponent_values)
    if league_average <= 0:
        return {"status": "insufficient_sample", "opponent": opponent,
                "position": position, "sample_weeks": len(opponent_values)}
    ratio = opponent_average / league_average
    return {
        "status": "descriptive", "opponent": opponent, "position": position,
        "market": market, "sample_weeks": len(opponent_values),
        "opponent_allowed_per_week": round(opponent_average, 2),
        "league_allowed_per_week": round(league_average, 2),
        "allowed_ratio": round(ratio, 3),
        "interpretation": "Above 1.0 means this defense allowed more of the stat to the position than the league average.",
        "warning": "Unadjusted descriptive defense-week totals, not a player forecast adjustment, validated probability, or betting edge.",
    }
