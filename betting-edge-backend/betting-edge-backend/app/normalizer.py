from .models import NormalizedEventOdds, Bookmaker, Market, Outcome

def normalize_odds(raw_events):
    result = []
    for raw in raw_events:
        books = []
        for rb in raw.get("bookmakers", []):
            markets = []
            for rm in rb.get("markets", []):
                outcomes = [Outcome(name=o["name"], price=o["price"], point=o.get("point"), description=o.get("description")) for o in rm.get("outcomes", [])]
                markets.append(Market(key=rm["key"], last_update=rm.get("last_update"), outcomes=outcomes))
            books.append(Bookmaker(key=rb["key"], title=rb["title"], last_update=rb.get("last_update"), markets=markets))
        result.append(NormalizedEventOdds(
            id=raw["id"], sport_key=raw["sport_key"], sport_title=raw.get("sport_title", raw["sport_key"]),
            commence_time=raw["commence_time"], home_team=raw["home_team"], away_team=raw["away_team"],
            bookmakers=books
        ))
    return result
