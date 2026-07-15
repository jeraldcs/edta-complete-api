import re
from pathlib import Path
from typing import Any

import yaml

from app.empathy.contracts import HiddenNeedsProfile, ImplicitConstraint, TripModel


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

    def extract(self, scenario_text: str) -> HiddenNeedsProfile:
        text = (scenario_text or "").lower()
        persona_tags: list[str] = []
        constraints: list[ImplicitConstraint] = []
        evidence: list[str] = []
        weights = self.config.get("constraint_weights") or {}

        for pattern_id, pattern in (self.config.get("patterns") or {}).items():
            triggers = pattern.get("triggers") or []
            matched = [trigger for trigger in triggers if trigger in text]
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

    MILE_PATTERN = re.compile(r"(\d{2,4})\s*(?:-?\s*)?(?:mile|mi)\b", re.I)
    HOUR_PATTERN = re.compile(r"(\d{1,2})\s*(?:-?\s*)?(?:hour|hr)\b", re.I)
    DESTINATION_HINTS = {
        "denver": "Denver, CO",
        "colorado": "Colorado",
        "pacific coast": "Pacific Coast Highway",
        "pch": "Pacific Coast Highway",
        "sfo": "San Francisco, CA",
        "seattle": "Seattle, WA",
    }

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
                    break

        distance = route_miles
        if distance is None:
            mile_match = self.MILE_PATTERN.search(scenario_text or "")
            if mile_match:
                distance = float(mile_match.group(1))
            else:
                hour_match = self.HOUR_PATTERN.search(scenario_text or "")
                if hour_match:
                    distance = float(hour_match.group(1)) * 55

        route_hint = None
        if "pacific coast" in text or "pch" in text:
            route_hint = "pacific_coast"
        elif "denver" in text or "colorado" in text:
            route_hint = "denver"

        return TripModel(
            destination=resolved_destination,
            distance_miles=distance,
            rental_days=max(1, rental_days),
            route_hint=route_hint,
        )
