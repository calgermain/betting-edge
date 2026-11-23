"""NBA historical directional evidence, not a calibrated betting probability."""
from __future__ import annotations

import math
from pydantic import BaseModel, Field
from .nba_stats import MARKETS, player_research


class NBACandidate(BaseModel):
    id: str = Field(min_length=1, max_length=300)
    player: str = Field(min_length=2, max_length=120)
    market: str
    line: float = Field(ge=0)
    side: str
    opponent: str | None = None


class NBAResearchRequest(BaseModel):
    season: int = Field(ge=2003, le=2100)
    candidates: list[NBACandidate] = Field(min_length=1, max_length=40)


def rank_nba_candidates(rows: list[dict], request: NBAResearchRequest) -> dict:
    results = []
    for c in request.candidates:
        item = {"id": c.id, "player": c.player, "market": c.market,
                "line": c.line, "side": c.side, "status": "unavailable",
                "score": None, "validated_probability": False}
        if c.market not in MARKETS or c.side not in {"Over", "Under"} or not math.isfinite(c.line):
            item["reason"] = "Unsupported market, side, or line"
            results.append(item)
            continue
        try:
            research = player_research(rows, c.player, request.season, c.market, c.line)
            if research["status"] != "ok":
                item["reason"] = research["status"]
            elif research["sample_size"] < 8:
                item["reason"] = "At least eight historical games required"
            else:
                minutes_model = research.get("minutes_model")
                # Select the historical model with lower observed walk-forward MAE.
                # No manual minutes scenario, injury, opponent or lineup adjustments.
                baseline_mae = research.get("walk_forward_mae")
                rate_mae = minutes_model.get("walk_forward_mae") if minutes_model else None
                use_rate = rate_mae is not None and (baseline_mae is None or rate_mae < baseline_mae)
                projection = minutes_model["projected_stat"] if use_rate else research["projected_stat"]
                mae = rate_mae if use_rate else baseline_mae
                if mae is None or mae <= 0:
                    item["reason"] = "Insufficient forecast-error evidence"
                else:
                    directional = (projection - c.line) * (1 if c.side == "Over" else -1)
                    score = round(max(-3, min(3, directional / max(mae, 1))) * 10, 2)
                    item.update(status="researched", score=score, projected_stat=projection,
                                walk_forward_mae=mae, model="minutes_aware" if use_rate else "weighted_baseline",
                                sample_size=research["sample_size"],
                                historical_hit_rate=(research["historical_over_rate"] if c.side == "Over"
                                                     else research["historical_under_rate"]),
                                injury_adjusted=False, lineup_adjusted=False, opponent_adjusted=False,
                                reason="Historical directional signal; not a calibrated edge")
        except (ValueError, TypeError) as exc:
            item["reason"] = str(exc)
        results.append(item)
    return {"season": request.season, "results": results, "validated_probability": False,
            "methodology": "Directional gap divided by walk-forward MAE; compares historical models. "
                           "No calibrated probabilities, injury/lineup/opponent adjustment or parlay correlation."}
