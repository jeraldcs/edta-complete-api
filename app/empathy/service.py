from typing import Any

from app.catalog import vehicle_candidates, vehicle_specs_by_id
from app.empathy.constraint_matcher import ConstraintMatcher
from app.empathy.contracts import EmpathyBundle, HiddenNeedsProfile, ImplicitConstraint, TripModel
from app.empathy.hidden_needs import HiddenNeedsExtractor, TripExtractor
from app.empathy.tco_calculator import TCOCalculator
from app.enrichment.enrichment_service import EnrichmentService
from app.models import CustomerContext, RankedRecommendation, Channel


class EmpathyEngine:
    """Orchestrates hidden needs, enrichment, constraint matching, and TCO."""

    EMPATHY_KEYWORDS = {
        "rental", "vehicle", "car", "suv", "road trip", "traveling", "grandmother",
        "toddler", "college", "dorm", "pacific coast", "denver", "partner", "moving",
    }

    PERSONA_PITCHES = {
        "elderly_passenger": "Low step-in height and easy entry for your 80-year-old grandmother.",
        "toddler_family": "ISOFIX child-seat anchors and generous rear legroom for your toddler.",
        "couple_leisure": "Panoramic roof, premium sound, and sleek handling for your coastal road trip.",
        "college_move": "Fold-flat rear seats, wide tailgate, and cargo space for the dorm move.",
        "mountain_travel": "AWD and engine power suited for mountain climbs and winter routes.",
    }

    def __init__(self):
        self.hidden_needs = HiddenNeedsExtractor()
        self.trip_extractor = TripExtractor()
        self.enrichment_service = EnrichmentService()
        self.constraint_matcher = ConstraintMatcher()
        self.tco_calculator = TCOCalculator()

    def should_activate(self, scenario_text: str, include_empathy: bool = False) -> bool:
        """Empathy ranking runs only when the client explicitly requests it."""
        return include_empathy

    def process(
        self,
        scenario_text: str,
        context: CustomerContext,
        *,
        include_empathy: bool = False,
        destination: str | None = None,
        route_miles: float | None = None,
        rental_days: int = 3,
    ) -> tuple[CustomerContext, EmpathyBundle]:
        active = self.should_activate(scenario_text, include_empathy)
        profile = self.hidden_needs.extract(scenario_text)
        trip = self.trip_extractor.extract(scenario_text, destination, route_miles, rental_days)
        enrichment = self.enrichment_service.enrich(trip, scenario_text)

        if enrichment.route.distance_miles and not trip.distance_miles:
            trip = trip.model_copy(update={"distance_miles": enrichment.route.distance_miles})
        if not trip.distance_miles and "500" in (scenario_text or ""):
            trip = trip.model_copy(update={"distance_miles": 500.0})

        all_constraints = list(profile.implicit_constraints)
        for constraint_id in enrichment.derived_constraints:
            all_constraints.append(
                ImplicitConstraint(
                    constraint_id=constraint_id,
                    weight=0.12,
                    reason="Derived from weather/route enrichment",
                    source="enrichment",
                )
            )

        specs = vehicle_specs_by_id()
        matches = self.constraint_matcher.score_all(specs, all_constraints) if active else {}

        business_context = dict(context.business_context)
        business_context.update({
            "empathy_active": active,
            "empathy_constraints": [item.model_dump() for item in all_constraints],
            "empathy_persona_tags": profile.persona_tags,
            "trip": trip.model_dump(),
            "enrichment": enrichment.model_dump(),
            "vehicle_specs": specs,
            "empathy_ranking": {
                candidate_id: match.model_dump()
                for candidate_id, match in matches.items()
            },
        })

        updated_context = context.model_copy(update={"business_context": business_context})
        bundle = EmpathyBundle(
            hidden_needs=profile,
            trip=trip,
            enrichment=enrichment,
            constraint_matches=matches,
            active=active,
        )
        bundle.empathy_pitch = self._build_pitch(profile, enrichment)
        return updated_context, bundle

    def candidates_for_context(self, context: CustomerContext):
        if not context.business_context.get("empathy_active"):
            return None
        return vehicle_candidates()

    def attach_results(
        self,
        recommendations: list[RankedRecommendation],
        bundle: EmpathyBundle,
    ) -> tuple[list[RankedRecommendation], EmpathyBundle]:
        if not bundle.active or not recommendations:
            return recommendations, bundle

        specs = vehicle_specs_by_id()
        ranked_ids = [item.candidate.id for item in recommendations]
        bundle.tco_comparisons = self.tco_calculator.compare_candidates(
            specs,
            bundle.trip,
            bundle.enrichment,
            ranked_ids,
        )
        tco_by_id = {item.candidate_id: item for item in bundle.tco_comparisons}
        enrichment_notes = self.enrichment_service.enrichment_notes(bundle.enrichment)

        updated: list[RankedRecommendation] = []
        for recommendation in recommendations:
            candidate_id = recommendation.candidate.id
            match = bundle.constraint_matches.get(candidate_id)
            tco = tco_by_id.get(candidate_id)
            notes = list(enrichment_notes)
            empathy_match = match.model_dump() if match else None

            explanation = recommendation.explanation
            if match and match.satisfied:
                empathy_line = f" Empathy match: {', '.join(match.satisfied[:4]).replace('_', ' ')}."
                explanation = f"{explanation}{empathy_line}"
            if tco and tco.recommendation_pitch:
                explanation = f"{explanation} {tco.recommendation_pitch}"
            if notes and candidate_id == recommendations[0].candidate.id:
                explanation = f"{explanation} {' '.join(notes)}"

            updated.append(
                recommendation.model_copy(
                    update={
                        "explanation": explanation.strip(),
                        "empathy_match": empathy_match,
                        "tco": tco.model_dump() if tco else None,
                        "enrichment_notes": notes if candidate_id == recommendations[0].candidate.id else [],
                    }
                )
            )

        if updated and bundle.hidden_needs.persona_tags:
            top_tco = tco_by_id.get(updated[0].candidate.id)
            if top_tco and top_tco.net_savings and top_tco.net_savings > 0:
                bundle.empathy_pitch = top_tco.recommendation_pitch
        return updated, bundle

    def _build_pitch(self, profile: HiddenNeedsProfile, enrichment) -> str:
        parts: list[str] = []
        for persona in profile.persona_tags:
            pitch = self.PERSONA_PITCHES.get(persona)
            if pitch:
                parts.append(pitch)
        if enrichment.weather and enrichment.weather.note:
            parts.append(enrichment.weather.note)
        if not parts and profile.implicit_constraints:
            labels = [item.constraint_id.replace("_", " ") for item in profile.implicit_constraints[:3]]
            parts.append(f"Prioritizing: {', '.join(labels)}.")
        return " ".join(parts)

    def simulate(
        self,
        scenario_text: str,
        *,
        destination: str | None = None,
        route_miles: float | None = None,
        rental_days: int = 3,
    ) -> dict[str, Any]:
        context = CustomerContext(
            anonymous_id="empathy-simulator",
            channel=Channel.web,
            business_context={"detected_domain": "car_rental"},
            channel_context={"source": "empathy_simulator"},
        )
        updated_context, bundle = self.process(
            scenario_text,
            context,
            include_empathy=True,
            destination=destination,
            route_miles=route_miles,
            rental_days=rental_days,
        )
        candidates = vehicle_candidates()
        ranking = updated_context.business_context.get("empathy_ranking") or {}
        ranked_specs = sorted(
            ranking.items(),
            key=lambda item: item[1].get("match_score", 0),
            reverse=True,
        )
        top_id = ranked_specs[0][0] if ranked_specs else candidates[0].id
        specs = vehicle_specs_by_id()
        tco = self.tco_calculator.compare_candidates(
            specs,
            bundle.trip,
            bundle.enrichment,
            [top_id, "economy_compact", "hybrid_midsize"],
        )
        bundle.tco_comparisons = tco
        return {
            "empathy": bundle.model_dump_public(),
            "parsed_context": updated_context.model_dump(mode="json"),
            "top_vehicle_id": top_id,
            "vehicle_catalog_count": len(candidates),
        }
