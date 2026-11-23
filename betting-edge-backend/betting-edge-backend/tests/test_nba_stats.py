from app.nba_stats import player_research, SOURCE


def _rows():
    return [
        {"player_id": 12, "player_name": "Sample Player", "season_type": "regular-season",
         "game_id": f"0022600{i:03d}", "game_date": f"2026-11-{i:02d}",
         "pts": 10 + i, "reb": 5, "ast": 3, "fg3m": 2,
         "min": 30, "team_abbreviation": "BOS"}
        for i in range(1, 11)
    ]


def test_hoopr_release_path_uses_season_end_year():
    assert SOURCE.format(season=2027).endswith("player_game_logs_2027.parquet")


def test_player_research_points_and_pra():
    points = player_research(_rows(), "Sample Player", 2027, "points", 15.5)
    pra = player_research(_rows(), "Sample Player", 2027, "pra")
    assert points["status"] == "ok"
    assert points["sample_size"] == 10
    assert points["walk_forward_mae"] is not None
    assert points["historical_over_rate"] == .5
    assert pra["projected_stat"] == points["projected_stat"] + 8
    assert points["validated_probability"] is False
    assert points["injury_adjusted"] is False


def test_missing_player_and_market():
    assert player_research(_rows(), "Unknown", 2027, "points")["status"] == "not_found"
    import pytest
    with pytest.raises(ValueError):
        player_research(_rows(), "Sample Player", 2027, "fantasy_points")
