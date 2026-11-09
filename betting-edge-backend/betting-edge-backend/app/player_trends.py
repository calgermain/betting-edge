"""Transparent descriptive analysis of NFL player game logs.

No sportsbook prices, simulated projections or invented player data are used.
The caller supplies verified game-by-game values and the selected prop line.
"""
from __future__ import annotations
from statistics import mean, median, pstdev
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class PlayerGame(BaseModel):
    date: date
    opponent: str = Field(min_length=1, max_length=120)
    value: float = Field(ge=0, allow_inf_nan=False)
    snaps: int | None = Field(default=None, ge=0)


class PlayerTrendRequest(BaseModel):
    player: str = Field(min_length=1, max_length=120)
    market: Literal["passing_yards", "rushing_yards", "receiving_yards", "receptions", "passing_tds", "rushing_tds", "receiving_tds"]
    line: float = Field(ge=0, allow_inf_nan=False)
    games: list[PlayerGame] = Field(min_length=1, max_length=25)

    @model_validator(mode="after")
    def check_dates(self):
        if len({game.date for game in self.games}) != len(self.games):
            raise ValueError("Each game must have a unique date")
        return self


def analyze_player_trend(request: PlayerTrendRequest) -> dict:
    # Input order does not affect recent-game calculations.
    ordered = sorted(request.games, key=lambda g: g.date, reverse=True)
    values = [g.value for g in ordered]
    recent = values[:5]
    # Strict over: a value equal to the line does not win an over bet.
    over = sum(value > request.line for value in values)
    under = sum(value < request.line for value in values)
    pushes = len(values) - over - under
    return {
        "player": request.player,
        "market": request.market,
        "line": request.line,
        "sample_size": len(values),
        "average": round(mean(values), 2),
        "median": round(median(values), 2),
        "std_dev": round(pstdev(values), 2),
        "last_5_average": round(mean(recent), 2),
        "last_5_values": recent,
        "over_count": over,
        "under_count": under,
        "push_count": pushes,
        "historical_over_rate": round(over / len(values), 4),
        "historical_under_rate": round(under / len(values), 4),
        "last_5_over_count": sum(v > request.line for v in recent),
        "last_5_under_count": sum(v < request.line for v in recent),
        "last_5_push_count": sum(v == request.line for v in recent),
        "methodology": "Descriptive history only; not a predictive probability or betting edge.",
        "data_source": "caller_supplied",
    }
