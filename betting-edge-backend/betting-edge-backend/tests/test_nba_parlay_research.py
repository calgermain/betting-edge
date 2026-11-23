from app.nba_parlay_research import NBACandidate, NBAResearchRequest, rank_nba_candidates


def rows():
    return [{"player_id": 1, "player_name": "Sample Player", "season_type": "regular-season",
             "game_id": str(i), "game_date": f"2026-11-{i:02d}",
             "pts": 20 + i, "reb": 5, "ast": 4, "fg3m": 2, "min": 30}
            for i in range(1, 13)]


def test_positive_over_and_negative_under():
    req=NBAResearchRequest(season=2027,candidates=[
        NBACandidate(id="over",player="Sample Player",market="points",line=15.5,side="Over"),
        NBACandidate(id="under",player="Sample Player",market="points",line=15.5,side="Under"),
    ])
    data=rank_nba_candidates(rows(),req)
    a,b=data["results"]
    assert a["status"]==b["status"]=="researched"
    assert a["score"]>0>b["score"]
    assert a["validated_probability"] is False
    assert a["injury_adjusted"] is False


def test_unavailable_player_not_recommended():
    req=NBAResearchRequest(season=2027,candidates=[
        NBACandidate(id="missing",player="No Such Player",market="points",line=15.5,side="Over")])
    item=rank_nba_candidates(rows(),req)["results"][0]
    assert item["score"] is None
    assert item["status"]=="unavailable"
