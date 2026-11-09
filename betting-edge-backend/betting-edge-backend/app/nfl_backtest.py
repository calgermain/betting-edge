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
