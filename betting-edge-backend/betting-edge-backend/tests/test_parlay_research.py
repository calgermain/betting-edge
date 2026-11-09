from app.parlay_research import Candidate, ResearchRequest, research_candidates


def _rows():
    result = []
    for week in range(1, 10):
        result.append({"season": "2025", "season_type": "REG", "week": str(week),
                       "player_id": "receiver1", "player_display_name": "Sample Receiver",
                       "position": "WR", "receiving_yards": str(60 + week),
                       "opponent_team": "MIN"})
    return result


def test_batch_research_provides_directional_score_not_probability():
    request = ResearchRequest(season=2025, candidates=[
        Candidate(id="over", player="Sample Receiver", market="receiving_yards",
                  line=30, side="Over"),
        Candidate(id="under", player="Sample Receiver", market="receiving_yards",
                  line=30, side="Under"),
    ])
    data = research_candidates(_rows(), request)
    over, under = data["results"]
    assert over["status"] == under["status"] == "researched"
    assert over["score"] > 0 > under["score"]
    assert over["validated_probability"] is False
    assert "probability" not in over
    assert over["sample_size"] == 9


def test_unavailable_player_is_not_ranked():
    data = research_candidates(_rows(), ResearchRequest(season=2025, candidates=[
        Candidate(id="missing", player="Unknown Player", market="receiving_yards",
                  line=50, side="Over")]))
    assert data["results"][0]["score"] is None


def test_unsupported_market_is_not_ranked():
    data = research_candidates(_rows(), ResearchRequest(season=2025, candidates=[
        Candidate(id="invalid", player="Sample Receiver", market="fantasy_points",
                  line=50, side="Over")]))
    assert data["results"][0]["status"] == "unavailable"
