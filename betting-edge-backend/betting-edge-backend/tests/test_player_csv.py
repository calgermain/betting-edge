import pytest

from app.player_csv import PlayerCsvError, analyze_csv


def test_csv_game_log_analysis():
    result = analyze_csv(
        "Sample Receiver", "receiving_yards", 65.5,
        "date,opponent,value,snaps\n"
        "2026-10-01,MIN,75,55\n"
        "2026-10-08,CHI,45,48\n"
        "2026-10-15,GB,100,60\n",
    )
    assert result["sample_size"] == 3
    assert result["over_count"] == 2
    assert result["under_count"] == 1
    assert result["last_5_values"] == [100, 45, 75]
    assert result["data_source"] == "caller_supplied"


@pytest.mark.parametrize("csv_text", [
    "date,opponent\n2026-10-01,MIN\n",
    "date,opponent,value\n2026-10-01,MIN,-1\n",
    "date,opponent,value\n2026-10-01,MIN,10,EXTRA\n",
    "date,opponent,value\n2026-10-01,MIN,abc\n",
])
def test_bad_csv_is_rejected(csv_text):
    with pytest.raises(PlayerCsvError):
        analyze_csv("Example", "receiving_yards", 10, csv_text)
