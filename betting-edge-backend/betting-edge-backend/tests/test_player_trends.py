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


def test_unsorted_game_logs_use_latest_five():
    games = [
        {"date": f"2026-10-{day:02}", "opponent": "Opponent", "value": day}
        for day in [3, 1, 6, 2, 5, 4]
    ]
    result = analyze_player_trend(PlayerTrendRequest(
        player="Example Player", market="rushing_yards", line=3.5, games=games
    ))
    assert result["last_5_values"] == [6, 5, 4, 3, 2]
    assert result["last_5_over_count"] == 3
    assert result["last_5_under_count"] == 2


def test_duplicate_dates_rejected():
    import pytest
    with pytest.raises(ValueError):
        PlayerTrendRequest(player="Example", market="receptions", line=3.5, games=[
            {"date": "2026-10-01", "opponent": "A", "value": 4},
            {"date": "2026-10-01", "opponent": "B", "value": 5},
        ])


def test_invalid_dates_rejected():
    import pytest
    with pytest.raises(ValueError):
        PlayerTrendRequest(player="Example", market="receptions", line=3.5, games=[
            {"date": "2026-02-30", "opponent": "A", "value": 4},
        ])
