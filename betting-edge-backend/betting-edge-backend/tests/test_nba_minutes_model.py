import pytest
from app.nba_stats import player_research


def rows():
    return [{"player_id": 3, "player_name": "Example Player", "season_type": "regular-season",
             "game_id": str(i), "game_date": f"2026-11-{i:02d}",
             "pts": i*2, "reb": 4, "ast": 2, "fg3m": 1, "min": 20+i}
            for i in range(1, 11)]


def test_minutes_model_backtests_prior_games_only():
    d=player_research(rows(), "Example Player", 2027, "points", 12.5)
    m=d["minutes_model"]
    assert m["status"]=="exploratory"
    assert m["backtest_games"]==5
    assert m["walk_forward_mae"] is not None
    assert m["minutes_walk_forward_mae"] is not None
    assert m["minutes_source"]=="historical_baseline"
    assert d["validated_probability"] is False


def test_manual_minutes_is_explicit_scenario_not_backtest_leakage():
    base=player_research(rows(), "Example Player", 2027, "points")["minutes_model"]
    scenario=player_research(rows(), "Example Player", 2027, "points", projected_minutes=36)["minutes_model"]
    assert scenario["minutes_source"]=="manual_scenario"
    assert scenario["projected_minutes"]==36
    assert scenario["projected_stat"]>base["projected_stat"]
    assert scenario["walk_forward_mae"]==base["walk_forward_mae"]


def test_scenario_minutes_validation():
    with pytest.raises(ValueError):
        player_research(rows(), "Example Player", 2027, "points", projected_minutes=49)
