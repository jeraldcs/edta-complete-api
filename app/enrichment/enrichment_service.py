from pathlib import Path
from typing import Any

import yaml

from app.empathy.contracts import EnrichmentBundle, RouteProfile, TripModel, WeatherSnapshot
from app.empathy.route_planner import RoutePlanner


class EnrichmentService:
    """Weather, route, and gas-price enrichment with stub fallbacks."""

    def __init__(self, config_path: str | Path | None = None):
        path = Path(config_path or "config/enrichment_providers.yaml")
        self.config = self._load_config(path)
        self.route_planner = RoutePlanner()

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

        # Only claim "live" when a provider call actually returned live data — keys alone
        # are not enough (stubs/keywords are still used when live providers are absent).
        sources = {
            getattr(weather, "source", None),
            getattr(route, "source", None),
        }
        source_mode = "live" if "live" in sources else "stub"
        return EnrichmentBundle(
            weather=weather,
            route=route,
            derived_constraints=derived,
            gas_price_usd=gas_price,
            source_mode=source_mode,
        )

    @staticmethod
    def _destination_key(destination: str | None, text: str) -> str:
        combined = f"{destination or ''} {text}".lower()
        for key in (
            "california_sierra_loop",
            "yosemite",
            "tahoe",
            "napa",
            "denver",
            "colorado",
            "pacific coast",
            "pch",
            "seattle",
            "san francisco",
            "sfo",
        ):
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
        if any(word in text for word in ("snow", "winter", "blizzard", "snowfall", "snowstorm", "icy")):
            return WeatherSnapshot(
                forecast="snow",
                wind_mph=20.0,
                source="keyword",
                note="Winter weather mentioned in scenario.",
            )
        if any(word in text for word in ("rain", "storm")) and "snowstorm" not in text:
            return WeatherSnapshot(
                forecast="heavy_rain",
                wind_mph=15.0,
                source="keyword",
                note="Rainy conditions mentioned in scenario.",
            )
        heat_tokens = (
            "110",
            "extreme heat",
            "desert",
            "scorching",
            "cooling performance",
            "heatwave",
            "heat wave",
        )
        southwest = any(token in text for token in ("arizona", "nevada", "phoenix", "las vegas"))
        if any(token in text for token in heat_tokens) or ("summer" in text and southwest):
            return WeatherSnapshot(
                forecast="extreme_heat",
                wind_mph=12.0,
                source="keyword",
                note="Extreme summer heat mentioned in scenario.",
            )
        return WeatherSnapshot(forecast="clear", wind_mph=5.0, source="default")

    def _route(self, destination_key: str, text: str, trip: TripModel) -> RouteProfile:
        planned = self.route_planner.route_profile(text)
        if planned and planned.get("distance_miles"):
            return RouteProfile(
                max_elevation_ft=float(planned.get("max_elevation_ft") or 0),
                steep_grade=bool(planned.get("steep_grade")),
                distance_miles=float(planned["distance_miles"]),
                source="route_planner",
            )

        stubs = (self.config.get("route") or {}).get("stub_routes") or {}
        threshold = float((self.config.get("route") or {}).get("elevation_threshold_ft", 5000))
        lookup_keys = [
            trip.route_hint or "",
            destination_key,
            text,
        ]
        for key, payload in stubs.items():
            if any(
                key in lookup
                for lookup in lookup_keys
                if lookup
            ):
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
        if weather.forecast == "extreme_heat":
            derived.extend(["fuel_efficiency", "cabin_comfort"])
            if route.distance_miles and float(route.distance_miles) >= 700:
                derived.append("fuel_efficiency")
        return sorted(set(derived))

    def _gas_price(self, destination_key: str) -> float:
        gas_config = self.config.get("gas_price") or {}
        default = float(gas_config.get("default_usd_per_gallon", 3.85))
        by_state = gas_config.get("by_state") or {}
        if "denver" in destination_key or "colorado" in destination_key:
            return float(by_state.get("CO", default))
        if any(key in destination_key for key in ("pacific", "pch", "yosemite", "tahoe", "napa", "san francisco", "sfo", "california")):
            return float(by_state.get("CA", default))
        if "seattle" in destination_key:
            return float(by_state.get("WA", default))
        return default

    def enrichment_notes(
        self,
        enrichment: EnrichmentBundle,
        *,
        top_candidate_id: str | None = None,
    ) -> list[str]:
        notes: list[str] = []
        weather = enrichment.weather
        if weather and weather.forecast in {"snow", "heavy_rain", "high_wind"} and weather.note:
            forecast_label = weather.forecast.replace("_", " ")
            top_id = (top_candidate_id or "").lower()
            if "awd" in top_id:
                notes.append(
                    f"We upgraded your recommendation to an AWD SUV because "
                    f"{forecast_label} is forecasted along your route."
                )
            else:
                notes.append(
                    f"Favoring AWD / higher-traction options because "
                    f"{forecast_label} is forecasted along your route."
                )
        if weather and weather.forecast == "extreme_heat":
            notes.append(
                "Extreme heat along your route — prioritizing fuel efficiency and cabin comfort "
                "for long Southwest highway miles."
            )
        route = enrichment.route
        if route and route.steep_grade:
            notes.append(
                "Steep elevation along your route — prioritizing AWD and stronger engine options."
            )
        if route and route.distance_miles and route.source == "route_planner":
            notes.append(
                f"Estimated total driving distance for your multi-stop route: {route.distance_miles:.0f} miles."
            )
        return notes
