import re
import httpx
import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.weather_widget")

WEATHER_KEYWORDS = ["weather", "temperature", "forecast", "rain", "sunny", "cloudy", "wind", "meteo", "wetter"]

class WeatherWidget(WidgetProvider):
    async def should_run(self, context) -> bool:
        query = getattr(context, "raw_input", "") or ""
        return any(kw in query.lower() for kw in WEATHER_KEYWORDS)

    async def execute(self, context) -> WidgetResult | None:
        query = getattr(context, "raw_input", "") or ""
        location = self._extract_location(query)
        if not location:
            return None

        coords = await self._geocode(location)
        if not coords:
            return WidgetResult(
                widget_type="weather",
                data={"error": f"Could not find location: {location}"},
                title=f"Weather: {location}",
                priority=3,
            )

        lat, lon = coords
        weather = await self._fetch_weather(lat, lon)
        if not weather:
            return None

        return WidgetResult(
            widget_type="weather",
            data={
                "location": location,
                "latitude": lat,
                "longitude": lon,
                "current": {
                    "temperature": weather.get("current", {}).get("temperature_2m"),
                    "feels_like": weather.get("current", {}).get("apparent_temperature"),
                    "humidity": weather.get("current", {}).get("relative_humidity_2m"),
                    "wind_speed": weather.get("current", {}).get("wind_speed_10m"),
                    "weather_code": weather.get("current", {}).get("weather_code"),
                },
                "units": weather.get("current_units", {}),
            },
            title=f"Current Weather: {location}",
            priority=3,
        )

    STOP_WORDS = frozenset({"the", "a", "an", "this", "that", "it", "is", "for", "my", "in", "at", "on", "to", "of", "and", "or", "weather", "forecast", "temperature", "today", "tomorrow", "like", "what", "how"})

    def _extract_location(self, query: str) -> str | None:
        patterns = [
            (r"(?:weather|temperature|forecast|meteo|wetter)\s+(?:in|at|for|a|de|à|im|in der)\s+([A-Za-zÀ-ÿ\s\-]+?)(?:\?|$|,|\.|and|\bweather\b|\btemperature\b)", re.IGNORECASE),
            (r"(?:what(?:'s| is|‘s))\s+(?:the\s+)?(?:weather|temperature|forecast)\s+(?:like\s+)?(?:in|at|for|a|de|à|im|in der)\s+([A-Za-zÀ-ÿ\s\-]+?)(?:\?|$|,|\.|and)", re.IGNORECASE),
            (r"(?:how\s+(?:is|are))\s+(?:the\s+)?(?:weather|temperature)\s+(?:in|at|for|a|de|à|im|in der)\s+([A-Za-zÀ-ÿ\s\-]+?)(?:\?|$|,|\.|and)", re.IGNORECASE),
            (r"([A-Z][a-zA-ZÀ-ÿ]+(?:\s+[A-Z][a-zA-ZÀ-ÿ]+)*)\s+(?:weather|forecast|temperature)", 0),
        ]
        for pattern, flags in patterns:
            m = re.search(pattern, query, flags)
            if m:
                loc = m.group(1).strip()
                if loc and len(loc) >= 2 and loc.lower() not in self.STOP_WORDS:
                    return loc
        return None

    async def _geocode(self, location: str) -> tuple[float, float] | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": location, "count": 1, "language": "en", "format": "json"},
                )
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", [])
                if results:
                    return results[0]["latitude"], results[0]["longitude"]
        except Exception as e:
            logger.warning(f"Geocoding failed for {location}: {e}")
        return None

    async def _fetch_weather(self, lat: float, lon: float) -> dict | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code",
                        "timezone": "auto",
                    },
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.warning(f"Weather fetch failed: {e}")
        return None
