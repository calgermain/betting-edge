from app.nfl_matchups import defensive_context


def _row(week, defense, position, yards, season="2025", kind="REG"):
    return {"season": season, "season_type": kind, "week": str(week),
            "opponent_team": defense, "position": position,
            "receiving_yards": str(yards)}


def test_defensive_context_uses_position_and_prior_weeks_only():
    rows = []
    for week in range(1, 7):
        rows += [_row(week, "MIN", "WR", 100),
                 _row(week, "CHI", "WR", 50),
                 _row(week, "MIN", "RB", 900)]
    rows.append(_row(7, "MIN", "WR", 10000))
    result = defensive_context(rows, 2025, "receiving_yards", "MIN", "WR", before_week=7)
    assert result["status"] == "descriptive"
    assert result["sample_weeks"] == 6
    assert result["opponent_allowed_per_week"] == 100
    assert result["league_allowed_per_week"] == 75
    assert result["allowed_ratio"] == 1.333
    assert "probability" not in result


def test_defensive_context_requires_sample():
    result = defensive_context([_row(1, "MIN", "WR", 100)],
                               2025, "receiving_yards", "MIN", "WR")
    assert result["status"] == "insufficient_sample"


def test_defensive_context_excludes_postseason_and_other_seasons():
    rows = [_row(week, "MIN", "WR", 50) for week in range(1, 5)]
    rows += [_row(5, "MIN", "WR", 9999, kind="POST"),
             _row(5, "MIN", "WR", 9999, season="2024")]
    result = defensive_context(rows, 2025, "receiving_yards", "MIN", "WR")
    assert result["sample_weeks"] == 4
    assert result["opponent_allowed_per_week"] == 50
