from typing import Any

from app.catalog import vehicle_candidates, vehicle_specs_by_id
from app.empathy.constraint_matcher import ConstraintMatcher
from app.empathy.contracts import (
    EmpathyBundle,
    EmpathyVehicleRecommendation,
    HiddenNeedsProfile,
    ImplicitConstraint,
    TripModel,
)
from app.empathy.hidden_needs import HiddenNeedsExtractor, TripExtractor
from app.empathy.tco_calculator import TCOCalculator
from app.enrichment.enrichment_service import EnrichmentService
from app.models import CustomerContext, RankedRecommendation, Channel


class EmpathyEngine:
    """Orchestrates hidden needs, enrichment, constraint matching, and TCO."""

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

    def should_rank_with_empathy(
        self,
        profile: HiddenNeedsProfile,
        *,
        include_empathy: bool = False,
        force_disable: bool = False,
    ) -> bool:
        if force_disable:
            return False
        if include_empathy:
            return True
        return bool(profile.persona_tags or profile.implicit_constraints)

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
        profile = self.hidden_needs.extract(scenario_text)
        trip = self.trip_extractor.extract(scenario_text, destination, route_miles, rental_days)
        enrichment = self.enrichment_service.enrich(trip, scenario_text)

        if enrichment.route.distance_miles and not trip.distance_miles:
            trip = trip.model_copy(update={"distance_miles": enrichment.route.distance_miles})
        if not trip.distance_miles and "500" in (scenario_text or ""):
            trip = trip.model_copy(update={"distance_miles": 500.0})

        ranking_active = self.should_rank_with_empathy(profile, include_empathy=include_empathy)

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
        matches = self.constraint_matcher.score_all(specs, all_constraints) if all_constraints else {}

        business_context = dict(context.business_context)
        business_context.update({
            "empathy_active": ranking_active,
            "empathy_insights": True,
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
            active=ranking_active,
            insights_available=True,
        )
        bundle.empathy_pitch = self._build_pitch(profile, enrichment)
        bundle.vehicle_recommendation = self.build_vehicle_recommendation(
            bundle,
            scenario_text,
        )
        return updated_context, bundle

    @staticmethod
    def merge_candidate_pools(*pools) -> list:
        merged: dict[str, object] = {}
        for pool in pools:
            for candidate in pool or []:
                merged.setdefault(candidate.id, candidate)
        return list(merged.values())

    def resolve_top_vehicle_id(self, bundle: EmpathyBundle, scenario_text: str = "") -> str:
        specs = vehicle_specs_by_id()
        if not specs:
            return "economy_compact"

        if bundle.constraint_matches:
            ranked = sorted(
                bundle.constraint_matches.items(),
                key=lambda item: (item[1].match_score, item[0]),
                reverse=True,
            )
            top_id, top_match = ranked[0]
            if top_match.match_score > 0:
                return top_id

        text = (scenario_text or "").lower()
        keyword_defaults = (
            (("grandmother", "toddler", "family", "child", "elderly"), "family_friendly_suv"),
            (("dorm", "move", "cargo", "boxes", "furniture"), "cargo_suv"),
            (("denver", "mountain", "winter", "snow", "awd"), "awd_suv"),
            (("coast", "scenic", "convertible", "partner", "pch"), "convertible_premium"),
            (("suv", "airport", "rental", "vehicle", "car"), "standard_sedan"),
        )
        for keywords, candidate_id in keyword_defaults:
            if any(keyword in text for keyword in keywords) and candidate_id in specs:
                return candidate_id
        return "economy_compact"

    def build_vehicle_recommendation(
        self,
        bundle: EmpathyBundle,
        scenario_text: str = "",
    ) -> EmpathyVehicleRecommendation:
        specs = vehicle_specs_by_id()
        candidate_id = self.resolve_top_vehicle_id(bundle, scenario_text)
        spec = specs.get(candidate_id) or next(iter(specs.values()), {})
        match = bundle.constraint_matches.get(candidate_id)
        if match is None and spec:
            match = self.constraint_matcher.score_candidate(
                candidate_id,
                spec,
                list(bundle.hidden_needs.implicit_constraints),
            )

        tco = None
        if spec and bundle.trip.distance_miles:
            baseline = specs.get("economy_compact")
            tco = self.tco_calculator.breakdown(
                candidate_id,
                spec,
                bundle.trip,
                bundle.enrichment.gas_price_usd,
                baseline_spec=baseline,
                baseline_id="economy_compact",
            )

        pitch = bundle.empathy_pitch
        if not pitch and match and match.satisfied:
            labels = ", ".join(item.replace("_", " ") for item in match.satisfied[:4])
            pitch = f"Empathy Engine prioritizes {labels} for this scenario."
        elif not pitch:
            pitch = (
                f"{spec.get('title', candidate_id)} is the baseline empathy vehicle pick "
                "when no special hidden needs were detected."
            )
        if tco and tco.recommendation_pitch and tco.recommendation_pitch not in pitch:
            pitch = f"{pitch} {tco.recommendation_pitch}".strip()

        return EmpathyVehicleRecommendation(
            candidate_id=candidate_id,
            title=spec.get("title", candidate_id),
            description=spec.get("description", ""),
            match_score=match.match_score if match else 0.0,
            satisfied=list(match.satisfied) if match else [],
            gaps=list(match.gaps) if match else [],
            pitch=pitch.strip(),
            tco=tco,
        )

    def attach_results(
        self,
        recommendations: list[RankedRecommendation],
        bundle: EmpathyBundle,
    ) -> tuple[list[RankedRecommendation], EmpathyBundle]:
        if not recommendations:
            return recommendations, bundle

        specs = vehicle_specs_by_id()
        ranked_ids = [item.candidate.id for item in recommendations]
        vehicle_ids = [candidate_id for candidate_id in ranked_ids if candidate_id in specs]
        if bundle.vehicle_recommendation and bundle.vehicle_recommendation.candidate_id not in vehicle_ids:
            vehicle_ids.append(bundle.vehicle_recommendation.candidate_id)
        if vehicle_ids and bundle.trip.distance_miles:
            bundle.tco_comparisons = self.tco_calculator.compare_candidates(
                specs,
                bundle.trip,
                bundle.enrichment,
                vehicle_ids,
            )
        tco_by_id = {item.candidate_id: item for item in bundle.tco_comparisons}
        enrichment_notes = self.enrichment_service.enrichment_notes(bundle.enrichment)

        updated: list[RankedRecommendation] = []
        for index, recommendation in enumerate(recommendations):
            candidate_id = recommendation.candidate.id
            match = bundle.constraint_matches.get(candidate_id)
            tco = tco_by_id.get(candidate_id)
            notes = list(enrichment_notes) if index == 0 else []
            empathy_match = match.model_dump() if match else None

            explanation = recommendation.explanation
            if index == 0:
                explanation = self._build_unified_explanation(
                    recommendation,
                    bundle,
                    empathy_match,
                    tco,
                    notes,
                )

            updated.append(
                recommendation.model_copy(
                    update={
                        "explanation": explanation.strip(),
                        "empathy_match": empathy_match,
                        "tco": tco.model_dump() if tco else None,
                        "enrichment_notes": notes,
                    }
                )
            )

        if updated and bundle.hidden_needs.persona_tags:
            top_tco = tco_by_id.get(updated[0].candidate.id)
            if top_tco and top_tco.net_savings and top_tco.net_savings > 0:
                bundle.empathy_pitch = top_tco.recommendation_pitch

        if bundle.vehicle_recommendation and bundle.tco_comparisons:
            vehicle_tco = next(
                (
                    item
                    for item in bundle.tco_comparisons
                    if item.candidate_id == bundle.vehicle_recommendation.candidate_id
                ),
                None,
            )
            if vehicle_tco:
                bundle.vehicle_recommendation = bundle.vehicle_recommendation.model_copy(
                    update={"tco": vehicle_tco}
                )
        return updated, bundle

    def _build_unified_explanation(
        self,
        recommendation: RankedRecommendation,
        bundle: EmpathyBundle,
        empathy_match: dict | None,
        tco,
        enrichment_notes: list[str],
    ) -> str:
        parts = [recommendation.explanation.strip()]
        if bundle.empathy_pitch:
            parts.append(bundle.empathy_pitch)
        elif empathy_match and empathy_match.get("satisfied"):
            labels = ", ".join(item.replace("_", " ") for item in empathy_match["satisfied"][:4])
            parts.append(f"This recommendation reflects hidden needs we inferred: {labels}.")
        if enrichment_notes:
            parts.extend(enrichment_notes)
        if tco and tco.recommendation_pitch and tco.recommendation_pitch not in " ".join(parts):
            parts.append(tco.recommendation_pitch)
        return " ".join(part for part in parts if part).strip()

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
        ranking = updated_context.business_context.get("empathy_ranking") or {}
        ranked_specs = sorted(
            ranking.items(),
            key=lambda item: item[1].get("match_score", 0),
            reverse=True,
        )
        top_id = ranked_specs[0][0] if ranked_specs else vehicle_candidates()[0].id
        specs = vehicle_specs_by_id()
        bundle.tco_comparisons = self.tco_calculator.compare_candidates(
            specs,
            bundle.trip,
            bundle.enrichment,
            [top_id, "economy_compact", "hybrid_midsize"],
        )
        return {
            "empathy": bundle.model_dump_public(),
            "parsed_context": updated_context.model_dump(mode="json"),
            "top_vehicle_id": top_id,
            "vehicle_catalog_count": len(vehicle_candidates()),
        }
