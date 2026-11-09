"""Weather logic tests that do not make network calls."""
import asyncio
from datetime import datetime, timedelta, timezone

from app.providers.research import ResearchProvider


def run(coro):
    return asyncio.run(coro)


def test_missing_and_invalid_kickoff_do_not_call_provider():
    provider = ResearchProvider()
    assert run(provider.weather(44.97, -93.26))["status"] == "missing_kickoff"
    assert run(provider.weather(44.97, -93.26, "not-a-date"))["status"] == "invalid_kickoff"
    assert run(provider.weather(44.97, -93.26, "2026-11-10T12:00:00"))["status"] == "invalid_kickoff"


def test_past_game_does_not_call_provider():
    provider = ResearchProvider()
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assert run(provider.weather(44.97, -93.26, past))["status"] == "past_game"


def test_far_future_does_not_call_provider():
    provider = ResearchProvider()
    future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    assert run(provider.weather(44.97, -93.26, future))["status"] == "outside_forecast_window"
