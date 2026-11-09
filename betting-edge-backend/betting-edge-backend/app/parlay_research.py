"""Batch research for NFL player prop parlay candidates; no sportsbook requests."""
from __future__ import annotations

from pydantic import BaseModel, Field
from .nflverse_stats import analyze_weekly, MARKETS
from .nfl_projection import baseline
from .nfl_backtest import evaluate
from .nfl_matchups import defensive_context


class Candidate(BaseModel):
    id: str = Field(min_length=1, max_length=240)
    player: str = Field(min_length=2, max_length=120)
    market: str
    line: float = Field(ge=0, allow_inf_nan=False)
    side: str
    opponent: str | None = Field(default=None, max_length=5)


class ResearchRequest(BaseModel):
    season: int = Field(ge=1999, le=2100)
    candidates: list[Candidate] = Field(min_length=1, max_length=40)


def research_candidates(rows: list[dict], request: ResearchRequest) -> dict:
    """Rank *evidence quality*, not estimated hit probabilities or betting edge."""
    results = []
    player_positions = {}
    for row in rows:
        if str(row.get("season")) == str(request.season) and row.get("player_id") and row.get("position"):
            player_positions[row["player_id"]] = row["position"]
    for candidate in request.candidates:
        result = {"id": candidate.id, "status": "unavailable", "score": None,
                  "validated_probability": False}
        if candidate.market not in MARKETS or candidate.side not in {"Over", "Under"}:
            result["reason"] = "Unsupported market or side"
            results.append(result)
            continue
        data = analyze_weekly(rows, candidate.player, candidate.market,
                              candidate.line, request.season)
        if data["status"] != "ok":
            result["reason"] = data["status"]
            results.append(result)
            continue
        projection = baseline(data["games"], candidate.line)
        backtest = evaluate(data["games"])
        if projection["status"] != "exploratory" or backtest["status"] != "evaluated":
            result["reason"] = "Not enough observed games for projection and backtest"
            results.append(result)
            continue
        # Directional evidence is not a probability. Cap sample and error influence.
        gap = projection["projected_stat"] - candidate.line
        directional = gap if candidate.side == "Over" else -gap
        error = backtest["mae"]["weighted"]
        normalized = directional / max(error, 1.0)
        # Negative scores indicate the baseline contradicts the chosen side.
        score = round(max(-3, min(3, normalized)) * 10, 2)
        matchup = None
        if candidate.opponent:
            position = player_positions.get(data["player_id"])
            if position:
                matchup = defensive_context(rows, request.season, candidate.market,
                                            candidate.opponent, position)
        result.update({
            "status": "researched", "score": score,
            "sample_size": data["sample_size"],
            "projected_stat": projection["projected_stat"],
            "line": candidate.line, "side": candidate.side,
            "historical_hit_rate": round(
                (data["over_count"] if candidate.side == "Over" else data["under_count"]) /
                data["sample_size"], 3),
            "walk_forward_mae": error,
            "matchup": matchup,
            "reason": "Directional projection gap scaled by historical walk-forward MAE; uncalibrated",
        })
        results.append(result)
    return {"source": "nflverse", "season": request.season, "results": results,
            "limitations": "Research scores rank historical directional evidence only. Not probabilities, fair odds, guaranteed picks, or a correlation-adjusted parlay model."}
