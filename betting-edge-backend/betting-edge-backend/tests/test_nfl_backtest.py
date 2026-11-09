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
