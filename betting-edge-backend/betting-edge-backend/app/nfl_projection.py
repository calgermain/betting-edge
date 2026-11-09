"""Exploratory NFL player projection baseline; never claims a validated betting edge."""
from __future__ import annotations

from statistics import mean, pstdev
import math


def baseline(games: list[dict], line: float, opponent: str | None = None) -> dict:
    """Games ordered newest first. Opponent observations are descriptive only."""
    values = [float(g["value"]) for g in games]
    if len(values) < 3:
        return {"status": "insufficient_sample", "minimum_games": 3,
                "sample_size": len(values)}
    recent = values[:5]
    season_avg = mean(values)
    recent_avg = mean(recent)
    estimate = 0.6 * recent_avg + 0.4 * season_avg
    opponent_games = [float(g["value"]) for g in games
                      if opponent and str(g.get("opponent") or "").upper() == opponent.upper()]
    trend = recent_avg - season_avg
    # Sample dispersion describes uncertainty; it is not a calibrated forecast interval.
    spread = pstdev(values) if len(values) > 1 else 0
    return {
        "status": "exploratory", "sample_size": len(values),
        "projected_stat": round(estimate, 2),
        "recent_average": round(recent_avg, 2),
        "season_average": round(season_avg, 2),
        "recent_vs_season": round(trend, 2),
        "historical_std_dev": round(spread, 2),
        "difference_from_line": round(estimate - line, 2),
        "opponent": opponent,
        "vs_opponent_games": len(opponent_games),
        "vs_opponent_average": round(mean(opponent_games), 2) if opponent_games else None,
        "model": "Unvalidated weighted average: 60% last five, 40% season",
        "probability": None, "edge": None, "recommendation": None,
        "warning": "Exploratory baseline, not a validated probability, fair price, or betting recommendation.",
    }
