from app.nfl_backtest import evaluate


def test_walk_forward_never_uses_future_games():
    # Input newest-first. First three observations train; fourth is held out.
    result = evaluate([
        {"week": 4, "value": 100},
        {"week": 3, "value": 30},
        {"week": 2, "value": 20},
        {"week": 1, "value": 10},
    ])
    assert result["status"] == "evaluated"
    assert result["evaluated_games"] == 1
    assert result["observations"][0]["training_games"] == 3
    assert result["observations"][0]["weighted_prediction"] == 20
    assert result["mae"]["weighted"] == 80
    assert result["validated_probability"] is False


def test_insufficient_sample_does_not_report_mae():
    result = evaluate([{"value": 10}, {"value": 20}, {"value": 30}])
    assert result["status"] == "insufficient_sample"
    assert "mae" not in result


def test_constant_series_has_zero_error():
    result = evaluate([{"value": 50}] * 8)
    assert all(error == 0 for error in result["mae"].values())


def test_population_backtest_groups_players_and_excludes_future_and_postseason():
    from app.nfl_backtest import evaluate_population

    rows = []
    for player in ("a", "b"):
        for week in range(1, 7):
            rows.append({"player_id": player, "season": "2026",
                         "season_type": "REG", "week": str(week),
                         "receiving_yards": "50"})
    rows.append({"player_id": "a", "season": "2026", "season_type": "POST",
                 "week": "7", "receiving_yards": "1000"})
    result = evaluate_population(rows, "receiving_yards", 2026)
    assert result["evaluated_players"] == 2
    assert result["evaluated_player_games"] == 6
    assert result["pooled_mae"]["weighted"] == 0
    assert result["validated_probability"] is False


def test_population_backtest_rejects_sparse_data():
    from app.nfl_backtest import evaluate_population

    assert evaluate_population([], "receptions", 2026)["status"] == "insufficient_sample"


def test_tied_models_are_not_declared_winners():
    from app.nfl_backtest import evaluate_population
    rows = [{"player_id": "same", "season": "2026", "season_type": "REG",
             "week": str(w), "receiving_yards": "50"} for w in range(1, 9)]
    result = evaluate_population(rows, "receiving_yards", 2026)
    assert result["lowest_mae_model"] is None
    assert len(result["tied_lowest_mae_models"]) == 3
    assert result["weighted_outperforms_season"] is False
