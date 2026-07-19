import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

from app.empathy.contracts import HiddenNeedsProfile, ImplicitConstraint, TripModel


class ScenarioProfileMatcher:
    """Match free-text scenarios to trained travel profiles."""

    CONSTRAINT_WEIGHTS = {
        "awd_preferred": 0.16,
        "strong_engine": 0.10,
        "isofix_anchors": 0.12,
        "rear_legroom": 0.10,
        "high_cargo_family": 0.14,
        "luxury_comfort": 0.12,
        "premium_audio": 0.08,
        "fuel_efficiency": 0.12,
        "cabin_comfort": 0.12,
        "ev_powertrain": 0.18,
        "cargo_volume": 0.12,
        "beginner_easy": 0.14,
        "wet_weather_grip": 0.15,
    }

    PERSONA_STANDARD_FILTER = {
        "mountain_travel": "AWD SUV",
        "large_family": "Large SUV / Minivan",
        "business_executive": "Luxury Sedan",
        "adventure_travel": "AWD SUV",
        "urban_commuter": "Hybrid / Compact",
        "ev_buyer": "Electric Vehicle",
        "luxury_winter": "Premium AWD SUV",
        "first_time_driver": "Economy Compact",
        "rental_travel": "Midsize / SUV Rental",
        "wet_weather_travel": "AWD SUV",
        "desert_summer_travel": "Hybrid / Efficient Midsize",
    }

    PERSONA_SCORING_HINTS = {
        "mountain_travel": {"trust_score": 0.76, "fatigue_count": 2},
        "large_family": {"trust_score": 0.80, "fatigue_count": 3},
        "business_executive": {"trust_score": 0.91, "fatigue_count": 1},
        "adventure_travel": {"trust_score": 0.77, "fatigue_count": 2},
        "urban_commuter": {"trust_score": 0.68, "fatigue_count": 4},
        "ev_buyer": {"trust_score": 0.73, "fatigue_count": 2},
        "luxury_winter": {"trust_score": 0.85, "fatigue_count": 1},
        "first_time_driver": {"trust_score": 0.41, "fatigue_count": 6},
        "rental_travel": {"trust_score": 0.62, "fatigue_count": 3},
        "wet_weather_travel": {"trust_score": 0.71, "fatigue_count": 2},
        "desert_summer_travel": {"trust_score": 0.74, "fatigue_count": 2},
    }

    def __init__(self, config_path: str | Path | None = None):
        path = Path(config_path or "config/empathy/scenario_profiles.yaml")
        payload = self._load_config(path)
        self.profiles = payload.get("profiles") or {}

    @staticmethod
    def _load_config(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {"profiles": {}}
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {"profiles": {}}

    def match(self, scenario_text: str) -> tuple[str, dict[str, Any]] | None:
        text = (scenario_text or "").lower()
        best: tuple[int, str, dict[str, Any]] | None = None

        for profile_id, profile in self.profiles.items():
            required = [str(keyword).lower() for keyword in profile.get("required_keywords") or []]
            if required and not all(keyword in text for keyword in required):
                continue
            optional = [str(keyword).lower() for keyword in profile.get("optional_keywords") or []]
            optional_hits = sum(1 for keyword in optional if keyword in text)
            score = len(required) * 12 + optional_hits
            if profile.get("objective", "").lower()[:24] in text:
                score += 4
            if best is None or score > best[0]:
                best = (score, profile_id, profile)

        if best is None:
            return None
        return best[1], best[2]

    def enhance_hidden_needs(
        self,
        scenario_text: str,
        profile: HiddenNeedsProfile,
    ) -> HiddenNeedsProfile:
        matched = self.match(scenario_text)
        if not matched:
            return profile

        _, config = matched
        persona = config.get("persona")
        persona_tags = list(profile.persona_tags)
        if persona and persona not in persona_tags:
            persona_tags.append(persona)

        constraints = list(profile.implicit_constraints)
        existing = {item.constraint_id: item for item in constraints}
        for constraint_id in config.get("constraints") or []:
            weight = float(self.CONSTRAINT_WEIGHTS.get(constraint_id, 0.12))
            candidate = ImplicitConstraint(
                constraint_id=constraint_id,
                weight=weight,
                reason=f"Trained scenario profile: {config.get('objective', 'travel profile')}",
                source="scenario_profile",
            )
            prior = existing.get(constraint_id)
            if prior is None or candidate.weight > prior.weight:
                existing[constraint_id] = candidate

        evidence = list(profile.evidence_phrases)
        for keyword in (config.get("required_keywords") or [])[:3]:
            if keyword.lower() in (scenario_text or "").lower():
                evidence.append(keyword)

        standard_filter = self.PERSONA_STANDARD_FILTER.get(
            persona or "",
            profile.standard_filter_match or "Profile-matched vehicle",
        )

        return HiddenNeedsProfile(
            persona_tags=sorted(set(persona_tags)),
            implicit_constraints=list(existing.values()),
            confidence=min(0.98, max(profile.confidence, 0.72)),
            evidence_phrases=sorted(set(evidence)),
            standard_filter_match=standard_filter,
        )

    def apply_trip_defaults(
        self,
        scenario_text: str,
        trip: TripModel,
        *,
        route_miles: float | None = None,
    ) -> TripModel:
        if route_miles is not None:
            return trip
        matched = self.match(scenario_text)
        if not matched:
            return trip

        _, config = matched
        updates: dict[str, Any] = {}
        if not trip.distance_miles and config.get("default_miles"):
            updates["distance_miles"] = float(config["default_miles"])
        if config.get("default_rental_days"):
            updates["rental_days"] = max(trip.rental_days, int(config["default_rental_days"]))
        if config.get("route_hint") and not trip.route_hint:
            updates["route_hint"] = config["route_hint"]
        if config.get("objective"):
            updates["route_label"] = config["objective"]
        return trip.model_copy(update=updates) if updates else trip

    def preferred_vehicle(self, scenario_text: str) -> str | None:
        matched = self.match(scenario_text)
        if not matched:
            return None
        return matched[1].get("preferred_vehicle")

    def profile_pitch(self, scenario_text: str) -> str:
        matched = self.match(scenario_text)
        if not matched:
            return ""
        return str(matched[1].get("pitch") or "")

    def profile_public(self, scenario_text: str) -> dict[str, Any] | None:
        matched = self.match(scenario_text)
        if not matched:
            return None
        profile_id, config = matched
        return {
            "profile_id": profile_id,
            "objective": config.get("objective"),
            "preferred_vehicle": config.get("preferred_vehicle"),
            "pitch": config.get("pitch"),
            "persona": config.get("persona"),
        }

    def apply_scoring_attributes(self, scenario_text: str, profile_attributes: dict[str, Any]) -> dict[str, Any]:
        """Apply profile-specific trust/fatigue hints so TAPL and OSE vary by travel profile."""
        matched = self.match(scenario_text)
        if not matched:
            return profile_attributes
        profile_id, config = matched
        persona = config.get("persona") or ""
        hints = dict(config.get("scoring") or self.PERSONA_SCORING_HINTS.get(persona, {}))
        updated = dict(profile_attributes)
        for key, value in hints.items():
            flag = f"parsed_{key}"
            if not updated.get(flag):
                updated[key] = value
        if persona:
            updated["scenario_persona"] = persona
        updated["trained_profile_id"] = profile_id
        return updated


def scenario_anonymous_id(scenario_text: str) -> str:
    """Isolate demo TKGE/EML subjects per trained travel profile or scenario hash."""
    matcher = ScenarioProfileMatcher()
    matched = matcher.match(scenario_text)
    if matched:
        return f"travel-{matched[0]}"
    normalized = re.sub(r"\s+", " ", (scenario_text or "").strip().lower())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"scenario-{digest}"
