import httpx

class OddsApiError(RuntimeError):
    pass

class OddsApiProvider:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def _get(self, path, params=None):
        query = dict(params or {})
        query["apiKey"] = self.api_key
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(f"{self.base_url}/{path.lstrip('/')}", params=query)
        if r.status_code >= 400:
            raise OddsApiError(f"Odds provider returned HTTP {r.status_code}: {r.text[:500]}")
        return r.json(), r.headers

    async def sports(self):
        data, _ = await self._get("/sports")
        return data

    async def events(self, sport):
        data, _ = await self._get(f"/sports/{sport}/events")
        return data

    async def odds(self, sport, regions="us", markets="h2h,spreads,totals", bookmakers=None):
        params = {"regions": regions, "markets": markets, "oddsFormat": "american", "dateFormat": "iso"}
        if bookmakers: params["bookmakers"] = bookmakers
        data, h = await self._get(f"/sports/{sport}/odds", params)
        return data, {"remaining": h.get("x-requests-remaining"), "used": h.get("x-requests-used"), "last": h.get("x-requests-last")}

    async def event_props(self, sport, event_id, regions="us", markets="player_rush_yds,player_reception_yds", bookmakers=None):
        params = {"regions": regions, "markets": markets, "oddsFormat": "american", "dateFormat": "iso"}
        if bookmakers: params["bookmakers"] = bookmakers
        data, h = await self._get(f"/sports/{sport}/events/{event_id}/odds", params)
        return data, {"remaining": h.get("x-requests-remaining"), "used": h.get("x-requests-used"), "last": h.get("x-requests-last")}

    async def event_markets(self, sport, event_id, regions="us"):
        data, _ = await self._get(f"/sports/{sport}/events/{event_id}/markets", {"regions": regions, "dateFormat": "iso"})
        return data
