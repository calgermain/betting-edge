import httpx


class WeatherProviderError(RuntimeError):
    pass


class WeatherProvider:
    """
    Uses Open-Meteo's public forecast API.
    No API key is required.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    async def forecast(self, latitude: float, longitude: float):
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "precipitation,"
                "rain,"
                "snowfall,"
                "weather_code,"
                "wind_speed_10m,"
                "wind_gusts_10m"
            ),
            "hourly": (
                "temperature_2m,"
                "precipitation_probability,"
                "precipitation,"
                "rain,"
                "snowfall,"
                "wind_speed_10m,"
                "wind_gusts_10m"
            ),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "forecast_days": 2,
            "timezone": "auto",
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                )

            if response.status_code >= 400:
                raise WeatherProviderError(
                    f"Weather provider returned HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:500]}"
                )

            return response.json()

        except httpx.HTTPError as exc:
            raise WeatherProviderError(
                f"Weather request failed: {exc}"
            ) from exc
