from app.nfl_projection import baseline


def test_weighted_baseline_is_not_an_edge():
    games = [{"value": 100, "opponent": "MIN"},
             {"value": 80, "opponent": "CHI"},
             {"value": 60, "opponent": "MIN"},
             {"value": 40, "opponent": "GB"},
             {"value": 20, "opponent": "DET"},
             {"value": 10, "opponent": "GB"}]
    result = baseline(games, 65.5, "MIN")
    assert result["status"] == "exploratory"
    assert result["projected_stat"] == 58.33
    assert result["vs_opponent_games"] == 2
    assert result["vs_opponent_average"] == 80
    assert result["probability"] is None
    assert result["edge"] is None


def test_small_samples_do_not_get_projections():
    assert baseline([{"value": 20}], 15)["status"] == "insufficient_sample"
