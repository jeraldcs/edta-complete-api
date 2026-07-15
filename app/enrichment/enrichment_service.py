import os
from pathlib import Path
from typing import Any

import yaml

from app.empathy.contracts import EnrichmentBundle, RouteProfile, TripModel, WeatherSnapshot


class EnrichmentService:
    """Weather, route, and gas-price enrichment with stub fallbacks."""

    def __init__(self, config_path: str | Path | None = None):
        path = Path(config_path or "config/enrichment_providers.yaml")
        self.config = self._load_config(path)

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    def enrich(self, trip: TripModel, scenario_text: str = "") -> EnrichmentBundle:
        text = (scenario_text or "").lower()
        destination_key = self._destination_key(trip.destination, text)
        weather = self._weather(destination_key, text)
        route = self._route(destination_key, text, trip)
        derived = self._derived_constraints(weather, route)
        gas_price = self._gas_price(destination_key)

        live_mode = bool(os.getenv("WEATHER_API_KEY") or os.getenv("ROUTE_API_KEY"))
        return EnrichmentBundle(
            weather=weather,
            route=route,
            derived_constraints=derived,
            gas_price_usd=gas_price,
            source_mode="live" if live_mode else "stub",
        )

    @staticmethod
    def _destination_key(destination: str | None, text: str) -> str:
        combined = f"{destination or ''} {text}".lower()
        for key in ("denver", "colorado", "pacific coast", "pch", "seattle"):
            if key in combined:
                return key
        return (destination or "").lower()

    def _weather(self, destination_key: str, text: str) -> WeatherSnapshot:
        stubs = (self.config.get("weather") or {}).get("stub_destinations") or {}
        for key, payload in stubs.items():
            if key in destination_key or key in text:
                return WeatherSnapshot(
                    forecast=payload.get("forecast", "clear"),
                    wind_mph=float(payload.get("wind_mph", 0)),
                    source="stub",
                    note=payload.get("note", ""),
                )
        if any(word in text for word in ("snow", "winter", "blizzard")):
            return WeatherSnapshot(
                forecast="snow",
                wind_mph=20.0,
                source="keyword",
                note="Winter weather mentioned in scenario.",
            )
        if any(word in text for word in ("rain", "storm")):
            return WeatherSnapshot(
                forecast="heavy_rain",
                wind_mph=15.0,
                source="keyword",
                note="Rainy conditions mentioned in scenario.",
            )
        return WeatherSnapshot(forecast="clear", wind_mph=5.0, source="default")

    def _route(self, destination_key: str, text: str, trip: TripModel) -> RouteProfile:
        stubs = (self.config.get("route") or {}).get("stub_routes") or {}
        threshold = float((self.config.get("route") or {}).get("elevation_threshold_ft", 5000))
        for key, payload in stubs.items():
            if key in destination_key or key in text or trip.route_hint == key.replace(" ", "_"):
                distance = trip.distance_miles or payload.get("distance_miles")
                return RouteProfile(
                    max_elevation_ft=float(payload.get("max_elevation_ft", 0)),
                    steep_grade=bool(payload.get("steep_grade")),
                    distance_miles=float(distance) if distance else None,
                    source="stub",
                )
        return RouteProfile(
            max_elevation_ft=0.0,
            steep_grade=False,
            distance_miles=trip.distance_miles,
            source="default",
        )

    @staticmethod
    def _derived_constraints(weather: WeatherSnapshot, route: RouteProfile) -> list[str]:
        derived: list[str] = []
        if route.steep_grade or route.max_elevation_ft >= 5000:
            derived.extend(["awd_preferred", "strong_engine"])
        if weather.forecast in {"snow", "heavy_rain", "high_wind"}:
            derived.append("awd_preferred")
        return sorted(set(derived))

    def _gas_price(self, destination_key: str) -> float:
        gas_config = self.config.get("gas_price") or {}
        default = float(gas_config.get("default_usd_per_gallon", 3.85))
        by_state = gas_config.get("by_state") or {}
        if "denver" in destination_key or "colorado" in destination_key:
            return float(by_state.get("CO", default))
        if "pacific" in destination_key or "pch" in destination_key:
            return float(by_state.get("CA", default))
        if "seattle" in destination_key:
            return float(by_state.get("WA", default))
        return default

    def enrichment_notes(self, enrichment: EnrichmentBundle) -> list[str]:
        notes: list[str] = []
        weather = enrichment.weather
        if weather and weather.forecast in {"snow", "heavy_rain", "high_wind"} and weather.note:
            notes.append(
                f"We upgraded your recommendation to an AWD SUV because "
                f"{weather.forecast.replace('_', ' ')} is forecasted along your route."
            )
        route = enrichment.route
        if route and route.steep_grade:
            notes.append(
                "Steep elevation along your route — prioritizing AWD and stronger engine options."
            )
        return notes
