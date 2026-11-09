"""Leakage-free, chronological walk-forward evaluation of descriptive NFL baselines.

No sportsbook prices or betting recommendations. All forecasts use ONLY earlier games.
"""
from __future__ import annotations

from statistics import mean


def evaluate(games: list[dict], min_train: int = 3) -> dict:
    """Input newest-first, as returned by nflverse; evaluate subsequent observed games."""
    chronological = list(reversed(games))
    if len(chronological) <= min_train:
        return {"status": "insufficient_sample", "games": len(games),
                "evaluated_games": 0, "minimum_games": min_train + 1}
    errors = {"weighted": [], "season_mean": [], "last_five_mean": []}
    observations = []
    for index in range(min_train, len(chronological)):
        history = [float(game["value"]) for game in chronological[:index]]
        actual = float(chronological[index]["value"])
        season_mean = mean(history)
        recent_mean = mean(history[-5:])
        forecasts = {
            "weighted": 0.6 * recent_mean + 0.4 * season_mean,
            "season_mean": season_mean,
            "last_five_mean": recent_mean,
        }
        for key, forecast in forecasts.items():
            errors[key].append(abs(forecast - actual))
        observations.append({
            "week": chronological[index].get("week"),
            "actual": actual,
            "weighted_prediction": round(forecasts["weighted"], 2),
            "absolute_error": round(abs(forecasts["weighted"] - actual), 2),
            "training_games": index,
        })
    mae = {key: round(mean(values), 2) for key, values in errors.items()}
    return {
        "status": "evaluated",
        "evaluated_games": len(observations),
        "minimum_training_games": min_train,
        "mae": mae,
        "observations": observations,
        "method": "Expanding-window, one-game-ahead walk-forward; no future observations in training.",
        "limitations": "In-sample season history; small samples, injuries, opponent strength and roster changes are not modeled. MAE does not validate betting probabilities or establish an edge.",
        "validated_probability": False,
    }


def evaluate_population(rows: list[dict], market: str, season: int,
                        min_train: int = 3, min_games: int = 6) -> dict:
    """Pooled out-of-sample errors across regular-season player game logs.

    Every evaluated player-week is predicted from that player's earlier weeks.
    No market prices or bookmaker outcomes are used.
    """
    from collections import defaultdict
    import math

    from .nflverse_stats import MARKETS

    if market not in MARKETS:
        raise ValueError("Unsupported market")
    groups = defaultdict(list)
    for row in rows:
        if row.get("season_type") != "REG" or str(row.get("season")) != str(season):
            continue
        player_id = row.get("player_id")
        if not player_id:
            continue
        try:
            week = int(row["week"])
            value = float(row[MARKETS[market]])
        except (KeyError, ValueError, TypeError):
            continue
        if week < 1 or not math.isfinite(value) or value < 0:
            continue
        groups[player_id].append({"week": week, "value": value})
    all_errors = {"weighted": [], "season_mean": [], "last_five_mean": []}
    evaluated_players = 0
    for games in groups.values():
        # Prevent duplicate player/week rows from biasing pooled evaluation.
        weeks = {}
        for game in games:
            weeks.setdefault(game["week"], game)
        ordered = [weeks[w] for w in sorted(weeks, reverse=True)]
        if len(ordered) < max(min_games, min_train + 1):
            continue
        result = evaluate(ordered, min_train=min_train)
        if result["status"] != "evaluated":
            continue
        evaluated_players += 1
        # Reconstruct unrounded predictions for pooled MAE.
        chronological = list(reversed(ordered))
        for index in range(min_train, len(chronological)):
            history = [g["value"] for g in chronological[:index]]
            actual = chronological[index]["value"]
            season_mean = mean(history)
            recent_mean = mean(history[-5:])
            for name, prediction in {
                "weighted": .6 * recent_mean + .4 * season_mean,
                "season_mean": season_mean,
                "last_five_mean": recent_mean,
            }.items():
                all_errors[name].append(abs(actual - prediction))
    if not evaluated_players:
        return {"status": "insufficient_sample", "season": season, "market": market,
                "evaluated_players": 0, "evaluated_player_games": 0}
    raw_mae = {key: mean(values) for key, values in all_errors.items()}
    pooled_mae = {key: round(value, 3) for key, value in raw_mae.items()}
    best_error = min(raw_mae.values())
    # A numerical tie is not evidence that one model outperforms another.
    tolerance = 1e-9
    tied = [name for name, error in raw_mae.items() if abs(error - best_error) <= tolerance]
    winner = tied[0] if len(tied) == 1 else None
    improvement = raw_mae["season_mean"] - raw_mae["weighted"]
    return {
        "status": "evaluated", "season": season, "market": market,
        "evaluated_players": evaluated_players,
        "evaluated_player_games": len(all_errors["weighted"]),
        "pooled_mae": pooled_mae, "lowest_mae_model": winner,
        "tied_lowest_mae_models": tied if len(tied) > 1 else [],
        "weighted_mae_improvement_vs_season": round(improvement, 3),
        "weighted_outperforms_season": improvement > tolerance,
        "method": "Chronological expanding-window one-game-ahead backtest, pooled by player-game.",
        "limitations": "Exploratory historical evaluation on one season. Player games are not independent, missing weeks are not imputed, and no odds or probability calibration is included.",
        "validated_probability": False,
    }
