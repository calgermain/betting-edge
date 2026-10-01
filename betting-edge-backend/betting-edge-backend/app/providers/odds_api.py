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
            response = await client.get(
                f"{self.base_url}/{path.lstrip('/')}",
                params=query,
            )

        if response.status_code >= 400:
            raise OddsApiError(
                f"Odds provider returned HTTP "
                f"{response.status_code}: "
                f"{response.text[:500]}"
            )

        return response.json(), response.headers

    @staticmethod
    def _quota(headers):
        return {
            "remaining": headers.get("x-requests-remaining"),
            "used": headers.get("x-requests-used"),
            "last": headers.get("x-requests-last"),
        }

    async def sports(self):
        data, _ = await self._get("/sports")
        return data

    async def events(self, sport):
        data, _ = await self._get(
            f"/sports/{sport}/events"
        )
        return data

    async def odds(
        self,
        sport,
        regions="us",
        markets="h2h,spreads,totals",
        bookmakers=None,
    ):
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": "american",
            "dateFormat": "iso",
        }

        if bookmakers:
            params["bookmakers"] = bookmakers

        data, headers = await self._get(
            f"/sports/{sport}/odds",
            params,
        )

        return data, self._quota(headers)

    async def event_props(
        self,
        sport,
        event_id,
        regions="us",
        markets=(
            "player_pass_yds,"
            "player_pass_tds,"
            "player_rush_yds,"
            "player_rush_attempts,"
            "player_reception_yds,"
            "player_receptions,"
            "player_anytime_td"
        ),
        bookmakers=None,
    ):
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": "american",
            "dateFormat": "iso",
        }

        if bookmakers:
            params["bookmakers"] = bookmakers

        data, headers = await self._get(
            f"/sports/{sport}/events/{event_id}/odds",
            params,
        )

        return data, self._quota(headers)

    async def event_markets(
        self,
        sport,
        event_id,
        regions="us",
    ):
        data, headers = await self._get(
            f"/sports/{sport}/events/{event_id}/markets",
            {
                "regions": regions,
                "dateFormat": "iso",
            },
        )

        return data, self._quota(headers)
