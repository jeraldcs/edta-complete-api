from pathlib import Path
from typing import Any

import yaml

from app.empathy.contracts import TripModel


class RoutePlanner:
    """Resolve multi-stop road trips and estimated driving distances from scenario text."""

    def __init__(self, config_path: str | Path | None = None):
        path = Path(config_path or "config/empathy/routes.yaml")
        self.routes = self._load_config(path)

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"multi_stop_routes": {}}
        with path.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        return payload.get("multi_stop_routes") or {}

    def resolve(self, scenario_text: str) -> dict[str, Any] | None:
        text = (scenario_text or "").lower()
        matches: list[tuple[int, dict[str, Any]]] = []

        for route in self.routes.values():
            required = [keyword.lower() for keyword in route.get("required_keywords") or []]
            if not required or not all(keyword in text for keyword in required):
                continue
            optional = [keyword.lower() for keyword in route.get("optional_keywords") or []]
            optional_hits = sum(1 for keyword in optional if keyword in text)
            score = len(required) * 10 + optional_hits + len(route.get("segment_miles") or [])
            matches.append((score, route))

        if not matches:
            return None
        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    def apply_to_trip(
        self,
        trip: TripModel,
        scenario_text: str,
        *,
        route_miles: float | None = None,
    ) -> TripModel:
        if route_miles is not None:
            return trip

        route = self.resolve(scenario_text)
        if not route:
            return trip

        segments = [float(value) for value in route.get("segment_miles") or []]
        stops = list(route.get("stops") or [])
        total_miles = round(sum(segments), 1) if segments else trip.distance_miles

        return trip.model_copy(
            update={
                "origin": route.get("origin") or trip.origin,
                "destination": stops[-1] if stops else trip.destination,
                "distance_miles": total_miles,
                "stops": stops,
                "route_hint": route.get("route_hint") or trip.route_hint,
                "route_label": route.get("label"),
            }
        )

    def route_profile(self, scenario_text: str) -> dict[str, Any] | None:
        route = self.resolve(scenario_text)
        if not route:
            return None
        segments = [float(value) for value in route.get("segment_miles") or []]
        return {
            "label": route.get("label"),
            "stops": route.get("stops") or [],
            "segment_miles": segments,
            "distance_miles": round(sum(segments), 1) if segments else None,
            "max_elevation_ft": float(route.get("max_elevation_ft") or 0),
            "steep_grade": bool(route.get("steep_grade")),
            "route_hint": route.get("route_hint"),
        }
