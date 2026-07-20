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
        "desert_summer_travel": "Any Midsize / SUV",
        "efficiency_seeker": "Any Economy car",
        "comfort_seeker": "Any Midsize Sedan",
    }

    # Prefer safety/family personas over leisure when multiple fire (not alphabetical).
    PERSONA_PRIORITY = (
        "toddler_family",
        "elderly_passenger",
        "desert_summer_travel",
        "mountain_travel",
        "college_move",
        "couple_leisure",
        "efficiency_seeker",
        "comfort_seeker",
    )

    def __init__(self, config_path: str | Path | None = None):
        path = Path(config_path or "config/empathy/hidden_needs.yaml")
        self.config = self._load_config(path)

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"patterns": {}, "constraint_weights": {}}
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}

    # Toddler ages 0-12, or bare "year-old" / "year old" not attached to an adult age (13+).
    _TODDLER_AGE_PATTERN = re.compile(
        r"\b(?:[0-9]|1[0-2])(?:\s*-\s*|\s+)years?(?:\s*-\s*|\s+)old\b",
        re.I,
    )
    _BARE_YEAR_OLD_PATTERN = re.compile(
        r"(?<!\d-)(?<!\d\s)(?<!\d)\byears?\s*-?\s*old\b",
        re.I,
    )

    @classmethod
    def _trigger_matches(cls, trigger: str | int | float, text: str) -> bool:
        """Match whole words/phrases only — avoid false hits like 'son' in 'personalization'."""
        normalized = str(trigger).strip().lower()
        if not normalized:
            return False
        # "year-old" is a substring of "80-year-old"; only treat as toddler age when 0-12 or bare.
        if normalized in {"year-old", "year old"}:
            return bool(cls._TODDLER_AGE_PATTERN.search(text) or cls._BARE_YEAR_OLD_PATTERN.search(text))
        parts = [re.escape(part) for part in re.split(r"\s+", normalized) if part]
        pattern = r"\b" + r"\s+".join(parts) + r"\b"
        return re.search(pattern, text, re.I) is not None

    def _pattern_matches(self, pattern: dict[str, Any], text: str) -> list[str]:
        """Return matched trigger phrases, honoring companion_requires_any gates."""
        triggers = pattern.get("triggers") or []
        matched = [str(trigger) for trigger in triggers if self._trigger_matches(trigger, text)]
        companion_triggers = pattern.get("companion_triggers") or []
        companion_matched = [
            str(trigger) for trigger in companion_triggers if self._trigger_matches(trigger, text)
        ]
        if not companion_matched:
            return matched
        required = pattern.get("companion_requires_any") or []
        if not required:
            return matched + companion_matched
        if any(self._trigger_matches(item, text) for item in required):
            return matched + companion_matched
        # Companion words alone (e.g. spouse on a snow trip) do not fire leisure personas.
        return matched

    def _primary_persona(self, persona_tags: list[str]) -> str | None:
        unique = set(persona_tags)
        for persona in self.PERSONA_PRIORITY:
            if persona in unique:
                return persona
        return sorted(unique)[0] if unique else None

    def extract(self, scenario_text: str) -> HiddenNeedsProfile:
        text = (scenario_text or "").lower()
        persona_tags: list[str] = []
        constraints: list[ImplicitConstraint] = []
        evidence: list[str] = []
        weights = self.config.get("constraint_weights") or {}

        for pattern_id, pattern in (self.config.get("patterns") or {}).items():
            matched = self._pattern_matches(pattern, text)
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

        unique_personas = sorted(set(persona_tags))
        confidence = min(0.95, 0.45 + 0.12 * len(unique_personas) + 0.05 * len(deduped))
        primary = self._primary_persona(unique_personas)
        standard_filter = (
            self.STANDARD_FILTER_HINTS.get(primary, "Generic category match") if primary else ""
        )

        return HiddenNeedsProfile(
            persona_tags=unique_personas,
            implicit_constraints=list(deduped.values()),
            confidence=round(confidence, 4) if unique_personas else 0.0,
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
        "arizona": "Arizona",
        "nevada": "Nevada",
        "phoenix": "Phoenix, AZ",
        "las vegas": "Las Vegas, NV",
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
