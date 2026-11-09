"""Parse player game logs from pasted CSV, without external API calls.

CSV headers: date,opponent,value[,snaps]. Values must be numeric and
nonnegative; dates must use YYYY-MM-DD. No estimates are generated.
"""
from __future__ import annotations

import csv
import io

from pydantic import ValidationError

from .player_trends import PlayerGame, PlayerTrendRequest, analyze_player_trend


class PlayerCsvError(ValueError):
    pass


def analyze_csv(player: str, market: str, line: float, csv_text: str) -> dict:
    if len(csv_text) > 32_000:
        raise PlayerCsvError("CSV input is too large (maximum 32,000 characters).")
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        headers = {str(h).strip().lower() for h in (reader.fieldnames or [])}
        if not {"date", "opponent", "value"}.issubset(headers):
            raise PlayerCsvError("CSV must have date,opponent,value headers.")
        if not headers.issubset({"date", "opponent", "value", "snaps"}):
            raise PlayerCsvError("Unexpected CSV column; use date,opponent,value[,snaps].")
        games = []
        for row in reader:
            if len(games) >= 25:
                raise PlayerCsvError("Maximum 25 games per request.")
            if None in row:
                raise PlayerCsvError("CSV row has more values than headers.")
            normalized = {k.strip().lower(): v for k, v in row.items()}
            games.append(PlayerGame.model_validate({
                "date": normalized.get("date"),
                "opponent": normalized.get("opponent"),
                "value": normalized.get("value"),
                "snaps": normalized.get("snaps") or None,
            }))
        request = PlayerTrendRequest(player=player, market=market, line=line, games=games)
    except (csv.Error, ValidationError) as exc:
        raise PlayerCsvError(f"Invalid player game log: {exc}") from exc
    return analyze_player_trend(request)
