import re
from pathlib import Path
from typing import Any

import yaml

from app.empathy.contracts import HiddenNeedsProfile, ImplicitConstraint, TripModel
from app.empathy.route_planner import RoutePlanner


class HiddenNeedsExtractor:
    """Rule-based hidden needs extractor for travel/car rental scenarios."""

    STANDARD_FILTER_HINTS = {
        "elderly_passenger": "Standard Sedan / SUV",
        "toddler_family": "Standard Sedan / SUV",
        "couple_leisure": "Any Economy car",
        "college_move": "Midsize SUV",
        "mountain_travel": "Any SUV",
    }

    def __init__(self, config_path: str | Path | None = None):
        path = Path(config_path or "config/empathy/hidden_needs.yaml")
        self.config = self._load_config(path)

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"patterns": {}, "constraint_weights": {}}
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    @staticmethod
    def _trigger_matches(trigger: str, text: str) -> bool:
        """Match whole words/phrases only — avoid false hits like 'son' in 'personalization'."""
        normalized = trigger.strip().lower()
        if not normalized:
            return False
        parts = [re.escape(part) for part in re.split(r"\s+", normalized) if part]
        pattern = r"\b" + r"\s+".join(parts) + r"\b"
        return re.search(pattern, text, re.I) is not None

    def extract(self, scenario_text: str) -> HiddenNeedsProfile:
        text = (scenario_text or "").lower()
        persona_tags: list[str] = []
        constraints: list[ImplicitConstraint] = []
        evidence: list[str] = []
        weights = self.config.get("constraint_weights") or {}

        for pattern_id, pattern in (self.config.get("patterns") or {}).items():
            triggers = pattern.get("triggers") or []
            matched = [trigger for trigger in triggers if self._trigger_matches(trigger, text)]
            if not matched:
                continue
            persona = pattern.get("persona") or pattern_id
            persona_tags.append(persona)
            evidence.extend(matched)
            for constraint_id in pattern.get("constraints") or []:
                constraints.append(
                    ImplicitConstraint(
                        constraint_id=constraint_id,
                        weight=float(weights.get(constraint_id, 0.1)),
                        reason=f"Triggered by {pattern_id.replace('_', ' ')} context",
                        source="rules",
                    )
                )

        deduped: dict[str, ImplicitConstraint] = {}
        for item in constraints:
            existing = deduped.get(item.constraint_id)
            if existing is None or item.weight > existing.weight:
                deduped[item.constraint_id] = item

        confidence = min(0.95, 0.45 + 0.12 * len(persona_tags) + 0.05 * len(deduped))
        standard_filter = self.STANDARD_FILTER_HINTS.get(persona_tags[0], "Generic category match") if persona_tags else ""

        return HiddenNeedsProfile(
            persona_tags=sorted(set(persona_tags)),
            implicit_constraints=list(deduped.values()),
            confidence=round(confidence, 4) if persona_tags else 0.0,
            evidence_phrases=sorted(set(evidence)),
            standard_filter_match=standard_filter,
        )


class TripExtractor:
    """Extract trip hints from scenario text and optional overrides."""

    MILE_PATTERN = re.compile(
        # Match "300 miles", "500-mile", "1,200 mi" (plural miles must be allowed).
        r"(\d{1,3}(?:,\d{3})+|\d{2,4})\s*(?:-?\s*)?(?:miles?|mi)\b",
        re.I,
    )
    HOUR_PATTERN = re.compile(r"(\d{1,2})\s*(?:-?\s*)?(?:hour|hr)\b", re.I)
    DAY_PATTERN = re.compile(r"(\d{1,2})\s*(?:-?\s*)?(?:day|days)\b", re.I)
    DESTINATION_HINTS = {
        "denver": "Denver, CO",
        "colorado": "Colorado",
        "pacific coast": "Pacific Coast Highway",
        "pch": "Pacific Coast Highway",
        "yosemite": "Yosemite National Park, CA",
        "lake tahoe": "Lake Tahoe, CA",
        "tahoe": "Lake Tahoe, CA",
        "napa": "Napa Valley, CA",
        "sfo": "San Francisco, CA",
        "san francisco": "San Francisco, CA",
        "seattle": "Seattle, WA",
    }

    def __init__(self):
        self.route_planner = RoutePlanner()

    def extract(
        self,
        scenario_text: str,
        destination: str | None = None,
        route_miles: float | None = None,
        rental_days: int = 3,
    ) -> TripModel:
        text = (scenario_text or "").lower()
        resolved_destination = destination
        if not resolved_destination:
            for hint, label in self.DESTINATION_HINTS.items():
                if hint in text:
                    resolved_destination = label

        distance = route_miles
        if distance is None:
            mile_matches = self.MILE_PATTERN.findall(scenario_text or "")
            if mile_matches:
                distance = max(float(value.replace(",", "")) for value in mile_matches)
            else:
                hour_match = self.HOUR_PATTERN.search(scenario_text or "")
                if hour_match:
                    distance = float(hour_match.group(1)) * 55

        inferred_days = rental_days
        day_match = self.DAY_PATTERN.search(scenario_text or "")
        if day_match:
            inferred_days = max(inferred_days, int(day_match.group(1)))

        route_hint = None
        if "pacific coast" in text or "pch" in text:
            route_hint = "pacific_coast"
        elif any(word in text for word in ("yosemite", "tahoe", "sierra")):
            route_hint = "california_sierra_loop"
        elif "denver" in text or "colorado" in text:
            route_hint = "denver"
        elif any(word in text for word in ("yellowstone", "grand teton", "glacier")):
            route_hint = "national_parks_loop"
        elif "seattle" in text and "rent" in text:
            route_hint = "seattle_vacation"

        trip = TripModel(
            destination=resolved_destination,
            distance_miles=distance,
            rental_days=max(1, inferred_days),
            route_hint=route_hint,
        )
        return self.route_planner.apply_to_trip(trip, scenario_text, route_miles=route_miles)
