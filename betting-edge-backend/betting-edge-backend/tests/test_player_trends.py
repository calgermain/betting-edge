from app.player_trends import PlayerTrendRequest, analyze_player_trend


def test_over_under_push_and_recent_average():
    payload = PlayerTrendRequest(
        player="Example Player",
        market="receiving_yards",
        line=50,
        games=[
            {"date": "2026-10-01", "opponent": "A", "value": 30},
            {"date": "2026-10-08", "opponent": "B", "value": 50},
            {"date": "2026-10-15", "opponent": "C", "value": 70},
        ],
    )
    result = analyze_player_trend(payload)
    assert result["over_count"] == 1
    assert result["under_count"] == 1
    assert result["push_count"] == 1
    assert result["last_5_values"] == [70, 50, 30]
    assert result["historical_over_rate"] == 0.3333
    assert "not a predictive probability" in result["methodology"]
