from app.nflverse_stats import analyze_weekly


def row(week, name="Sample Receiver", player_id="id1", value="70", season="2026"):
    return {
        "season": season, "season_type": "REG", "week": str(week),
        "player_display_name": name, "player_id": player_id,
        "receiving_yards": value, "opponent_team": "MIN", "team": "CHI",
    }


def test_weekly_stats_order_and_hit_rates():
    rows = [row(2, value="40"), row(1, value="65.5"), row(3, value="80")]
    result = analyze_weekly(rows, "Sample Receiver", "receiving_yards", 65.5, 2026)
    assert result["status"] == "ok"
    assert result["last_5_values"] == [80, 40, 65.5]
    assert result["over_count"] == 1
    assert result["under_count"] == 1
    assert result["push_count"] == 1


def test_ambiguous_name_is_not_guessed():
    result = analyze_weekly([row(1), row(2, player_id="id2")],
                            "Sample Receiver", "receiving_yards", 40, 2026)
    assert result["status"] == "ambiguous_player"


def test_missing_player_and_market():
    assert analyze_weekly([row(1)], "Missing", "receiving_yards", 40, 2026)["status"] == "not_found"
    assert analyze_weekly([row(1, value="")], "Sample Receiver", "receiving_yards", 40, 2026)["status"] == "no_market_data"


def test_player_suffix_and_punctuation_matching():
    result = analyze_weekly([row(1, name="John Smith Jr.")],
                            "John Smith", "receiving_yards", 50, 2026)
    assert result["status"] == "ok"


def test_suffix_normalization_does_not_guess_duplicate_players():
    rows = [row(1, name="John Smith Jr.", player_id="a"),
            row(1, name="John Smith", player_id="b")]
    result = analyze_weekly(rows, "John Smith", "receiving_yards", 50, 2026)
    assert result["status"] == "ambiguous_player"
