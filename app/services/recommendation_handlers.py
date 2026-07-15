import csv
from pathlib import Path
from typing import Optional

from app.api.schemas import (
    CandidatePreselectionSummary,
    CompareOutcomesResponseV1,
    CompareRequestSummary,
    ProfileLookupSummary,
    RecommendationResponseV1,
    RequestSummary,
    TrainingAlignmentSummary,
)
from app.catalog import DEFAULT_CANDIDATES
from app.container import ServiceContainer, container
from app.context_graph import ContextGraph
from app.observability.audit import log_recommendation_audit
from app.observability.metrics import record_feedback
from app.models import (
    BatchRecommendationRequest,
    Channel,
    CompareOutcomesRequest,
    CustomerContext,
    ExperienceMemorySnapshot,
    FeedbackEvent,
    IntentType,
    JourneyStage,
    RecommendationRequest,
    ScenarioRecommendationRequest,
    SimulationRequest,
    SyntheticTrainingRequest,
    EmpathySimulationRequest,
)


def _scenario_purpose(record):
    scenario_text = (record.get("scenario_text") or "").strip().lower()
    candidate_id = record.get("expected_candidate_id")
    purposes = {
        "vehicle_upgrade_suv": "Guide a family or airport rental shopper toward a relevant SUV upgrade or premium vehicle recommendation.",
        "early_booking_discount": "Support rental or travel shoppers who are comparing options with a timely booking incentive.",
        "hotel_reservation_assist": "Help a hotel shopper move from availability research to reservation completion.",
        "hotel_room_offer": "Present a relevant room or stay offer based on hotel browsing context.",
        "restaurant_reservation_assist": "Help a dining visitor find table availability or complete a restaurant reservation.",
        "restaurant_menu_recommendation": "Personalize menu or cuisine content for a restaurant visitor preparing to order.",
        "mobile_restaurant_qr_menu": "Serve a mobile-friendly QR or barcode menu experience for an in-restaurant diner.",
        "mobile_restaurant_dish_promo": "Recommend a relevant new dish, chef special, combo, or promotion after the diner opens the mobile QR menu.",
        "obesity_product_hcp_education": "Recommend approved obesity product education for a healthcare professional.",
        "hcp_education_content": "Recommend approved clinical or educational healthcare content.",
        "chatbot_booking_assist": "Guide a user through booking, reservation, or support next steps in conversation.",
        "connected_car_location_assist": "Provide location or return support in a connected vehicle context.",
        "wearable_health_nudge": "Deliver a short, trust-aware wearable nudge suitable for constrained channels.",
    }
    return purposes.get(candidate_id, "Match the scenario to the most relevant next best experience.")


def _normalized_scenario_text(text):
    return " ".join((text or "").strip().lower().split())


def _scenario_training_match(scenario_text):
    path = Path("data/scenario_training_master.csv")
    if not path.exists():
        return None
    target = _normalized_scenario_text(scenario_text)
    with path.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            if _normalized_scenario_text(record.get("scenario_text")) == target:
                record["purpose"] = record.get("purpose") or _scenario_purpose(record)
                return record
    return None


def _candidate_by_id(candidate_id):
    return next((candidate for candidate in DEFAULT_CANDIDATES if candidate.id == candidate_id), None)


def _profile_summary(raw: dict) -> ProfileLookupSummary:
    return ProfileLookupSummary(**raw)


def _inference_summary(engine) -> dict | None:
    if engine.last_inference is None:
        return None
    return engine.last_inference.model_dump_summary()


class RecommendationHandlers:
    def __init__(self, services: ServiceContainer | None = None):
        self.services = services or container

    def _build_graph(
        self,
        enriched_context: CustomerContext,
        memory_snapshot: ExperienceMemorySnapshot,
        recommendations=None,
    ) -> ContextGraph:
        prior_snapshot = self.services.graph_store.latest_snapshot(memory_snapshot.subject_id)
        graph = ContextGraph(enriched_context, prior_snapshot=prior_snapshot)
        if recommendations:
            for recommendation in recommendations[:3]:
                graph.record_recommendation(
                    candidate_id=recommendation.candidate.id,
                    title=recommendation.candidate.title,
                    tapl_action=recommendation.ai_score.tapl.action,
                    channel=str(enriched_context.channel.value),
                )
        self.services.graph_store.save_snapshot(memory_snapshot.subject_id, graph.export())
        return graph

    def _record_feedback_graph(self, event: FeedbackEvent, memory_snapshot: ExperienceMemorySnapshot) -> ContextGraph:
        prior_snapshot = self.services.graph_store.latest_snapshot(memory_snapshot.subject_id)
        context = CustomerContext(
            customer_id=event.customer_id,
            anonymous_id=event.anonymous_id,
            channel=event.channel,
        )
        graph = ContextGraph(context, prior_snapshot=prior_snapshot)
        graph.record_feedback(
            recommendation_id=event.recommendation_id,
            event_type=event.event_type,
            converted=bool(event.converted),
            revenue=float(event.revenue or 0.0),
            channel=str(event.channel.value),
        )
        self.services.graph_store.save_snapshot(memory_snapshot.subject_id, graph.export())
        return graph

    def _recommendation_runtime(self, enriched_context: CustomerContext, memory_snapshot: ExperienceMemorySnapshot):
        prior_snapshot = self.services.graph_store.latest_snapshot(memory_snapshot.subject_id)
        calibration = self.services.experience_memory.get_calibration(enriched_context)
        return prior_snapshot, calibration

    def _scenario_candidates(self, context):
        graph = ContextGraph(context)
        context_words = set(graph.keywords())
        primary_words = set()
        for source in [context.profile_attributes, context.business_context, context.channel_context]:
            keywords = source.get("scenario_keywords") if isinstance(source, dict) else None
            if isinstance(keywords, list):
                extracted = {str(keyword).lower() for keyword in keywords}
                primary_words.update(extracted)
                context_words.update(extracted)

        scored = []
        for candidate in DEFAULT_CANDIDATES:
            if candidate.channel != context.channel:
                continue
            candidate_words = set()
            candidate_words.update(candidate.title.lower().replace("_", " ").split())
            candidate_words.update(candidate.description.lower().replace("_", " ").split())
            candidate_words.add(candidate.type.lower())
            for tag in candidate.content_tags:
                candidate_words.update(tag.lower().replace("_", " ").split())
            for tag in candidate.intent_tags:
                candidate_words.add(tag.value)
            for tag in candidate.journey_tags:
                candidate_words.add(tag.value)
            primary_overlap = primary_words.intersection(candidate_words)
            overlap = primary_overlap or context_words.intersection(candidate_words)
            if overlap:
                scored.append((1 if primary_overlap else 0, len(overlap), candidate.business_value, candidate))

        if not scored:
            return None
        if any(primary_match for primary_match, _, _, _ in scored):
            scored = [item for item in scored if item[0]]
        scored.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
        return [candidate for _, _, _, candidate in scored]

    def recommend(self, request: RecommendationRequest, request_id: str) -> RecommendationResponseV1:
        enriched_context, profile_summary = self.services.profile_service.enrich_context(request.context)
        enriched_context, memory_before = self.services.experience_memory.enrich_context(enriched_context)
        prior_snapshot, calibration = self._recommendation_runtime(enriched_context, memory_before)
        recommendations = self.services.engine.recommend(
            enriched_context,
            request.candidates,
            request.limit,
            request.use_ai_models,
            use_llm=request.use_llm,
            use_slm=request.use_slm,
            use_llm_explanation=request.use_llm_explanation,
            inference_mode=request.inference_mode,
            calibration=calibration,
            prior_graph_snapshot=prior_snapshot,
        )
        memory_after = self.services.experience_memory.record_recommendations(enriched_context, recommendations)
        graph = self._build_graph(enriched_context, memory_after, recommendations)
        if recommendations:
            top = recommendations[0]
            log_recommendation_audit(
                request_id=request_id,
                route="recommend",
                channel=str(enriched_context.channel.value),
                candidate_id=top.candidate.id,
                tapl_action=top.ai_score.tapl.action,
                intent=top.ai_score.intent.label,
                journey_stage=top.ai_score.journey_stage.label,
                llm_enabled=self.services.llm_client.enabled,
                recommendation_count=len(recommendations),
            )
        return RecommendationResponseV1(
            request_summary=RequestSummary(
                request_id=request_id,
                channel=enriched_context.channel,
                journey_stage_input=enriched_context.journey_stage,
                intent_input=enriched_context.current_intent,
                customer_id=enriched_context.customer_id,
                profile=_profile_summary(profile_summary),
                experience_memory={"before": memory_before.model_dump(mode="json"), "after": memory_after.model_dump(mode="json")},
                use_ai_models=request.use_ai_models,
                use_llm=request.use_llm,
                use_slm=request.use_slm,
                use_llm_explanation=request.use_llm_explanation,
                inference_mode=request.inference_mode,
                inference=_inference_summary(self.services.engine),
                ml_inference=self.services.engine.ml.status(),
                provider_telemetry=self.services.provider_telemetry.summary(),
                explanation_routing=self.services.engine.explanation_router.status(),
                llm_enabled=self.services.llm_client.enabled,
                llm_status={
                    "recommendation_engine": self.services.engine.llm.status(),
                    "slm_engine": self.services.engine.slm.status(),
                },
                self_distillation=self.services.engine.distillation.status(),
                haoe=self.services.engine.orchestrator.status(),
                ose_calibration=calibration,
                context_graph=graph.summary(),
            ),
            recommendations=recommendations,
        )

    def recommend_from_scenario(self, request: ScenarioRecommendationRequest, request_id: str) -> RecommendationResponseV1:
        parsed_context, nlp_summary = self.services.scenario_parser.parse(
            request.scenario_text,
            use_llm=request.use_llm,
        )
        enriched_context, profile_summary = self.services.profile_service.enrich_context(parsed_context)
        enriched_context, memory_before = self.services.experience_memory.enrich_context(enriched_context)
        training_match = _scenario_training_match(request.scenario_text)
        if training_match:
            business_context = dict(enriched_context.business_context)
            business_context.update({
                "training_domain": training_match.get("domain"),
                "expected_candidate_id": training_match.get("expected_candidate_id"),
                "scenario_purpose": training_match.get("purpose"),
                "training_row_match": True,
            })
            channel_context = dict(enriched_context.channel_context)
            channel_context.update({
                "training_reference": True,
                "training_expected_candidate_id": training_match.get("expected_candidate_id"),
            })
            enriched_context = enriched_context.model_copy(update={
                "business_context": business_context,
                "channel_context": channel_context,
            })
            nlp_summary["training_reference"] = {
                "matched": True,
                "expected_candidate_id": training_match.get("expected_candidate_id"),
                "note": "Training row used for alignment metadata only; NLP context drives ranking.",
            }
        else:
            nlp_summary["training_reference"] = {
                "matched": False,
                "note": "Scenario parsed by NLP without exact training-row override.",
            }

        prior_snapshot, calibration = self._recommendation_runtime(enriched_context, memory_before)

        empathy_bundle = None
        enriched_context, empathy_bundle = self.services.empathy_engine.process(
            request.scenario_text,
            enriched_context,
            include_empathy=request.include_empathy,
            destination=request.destination,
            route_miles=request.route_miles,
            rental_days=request.rental_days,
        )
        if empathy_bundle.active:
            nlp_summary["empathy"] = {
                "active": True,
                "persona_tags": empathy_bundle.hidden_needs.persona_tags,
                "standard_filter_match": empathy_bundle.hidden_needs.standard_filter_match,
            }

        empathy_candidates = self.services.empathy_engine.candidates_for_context(enriched_context)
        preselected = empathy_candidates or self._scenario_candidates(enriched_context)
        candidates = preselected if preselected is not None else [
            candidate for candidate in DEFAULT_CANDIDATES if candidate.channel == enriched_context.channel
        ]
        recommendations = self.services.engine.recommend(
            enriched_context,
            candidates,
            request.limit,
            request.use_ai_models,
            use_llm=request.use_llm,
            use_slm=request.use_slm,
            use_llm_explanation=request.use_llm_explanation,
            inference_mode=request.inference_mode,
            calibration=calibration,
            prior_graph_snapshot=prior_snapshot,
        )
        if empathy_bundle and empathy_bundle.active:
            recommendations, empathy_bundle = self.services.empathy_engine.attach_results(
                recommendations,
                empathy_bundle,
            )
        memory_after = self.services.experience_memory.record_recommendations(enriched_context, recommendations)
        graph = self._build_graph(enriched_context, memory_after, recommendations)
        if recommendations:
            top = recommendations[0]
            log_recommendation_audit(
                request_id=request_id,
                route="recommend-from-scenario",
                channel=str(enriched_context.channel.value),
                candidate_id=top.candidate.id,
                tapl_action=top.ai_score.tapl.action,
                intent=top.ai_score.intent.label,
                journey_stage=top.ai_score.journey_stage.label,
                llm_enabled=self.services.llm_client.enabled,
                recommendation_count=len(recommendations),
                extra={"parser": nlp_summary.get("parser")},
            )
        return RecommendationResponseV1(
            request_summary=RequestSummary(
                request_id=request_id,
                scenario_text=request.scenario_text,
                nlp=nlp_summary,
                parsed_context=enriched_context.model_dump(mode="json"),
                channel=enriched_context.channel,
                journey_stage_input=enriched_context.journey_stage,
                intent_input=enriched_context.current_intent,
                customer_id=enriched_context.customer_id,
                profile=_profile_summary(profile_summary),
                experience_memory={"before": memory_before.model_dump(mode="json"), "after": memory_after.model_dump(mode="json")},
                training_alignment=TrainingAlignmentSummary(
                    matched=training_match is not None,
                    expected_candidate_id=training_match.get("expected_candidate_id") if training_match else None,
                    purpose=training_match.get("purpose") if training_match else None,
                ),
                candidate_preselection=CandidatePreselectionSummary(
                    enabled=preselected is not None,
                    candidate_count=len(candidates),
                ),
                empathy=empathy_bundle.model_dump_public() if empathy_bundle and empathy_bundle.active else None,
                enrichment=empathy_bundle.enrichment.model_dump() if empathy_bundle and empathy_bundle.active else None,
                tco={
                    "comparisons": [item.model_dump() for item in empathy_bundle.tco_comparisons],
                    "top_pitch": empathy_bundle.empathy_pitch,
                } if empathy_bundle and empathy_bundle.active and empathy_bundle.tco_comparisons else None,
                use_ai_models=request.use_ai_models,
                use_llm=request.use_llm,
                use_slm=request.use_slm,
                use_llm_explanation=request.use_llm_explanation,
                inference_mode=request.inference_mode,
                inference=_inference_summary(self.services.engine),
                ml_inference=self.services.engine.ml.status(),
                provider_telemetry=self.services.provider_telemetry.summary(),
                explanation_routing=self.services.engine.explanation_router.status(),
                llm_enabled=self.services.llm_client.enabled,
                self_distillation=self.services.engine.distillation.status(),
                haoe=self.services.engine.orchestrator.status(),
                ose_calibration=calibration,
                context_graph=graph.summary(),
            ),
            recommendations=recommendations,
        )

    def simulate(self, request: SimulationRequest, request_id: str) -> RecommendationResponseV1:
        enriched_context, profile_summary = self.services.profile_service.enrich_context(request.context)
        enriched_context, memory_snapshot = self.services.experience_memory.enrich_context(enriched_context)
        prior_snapshot, calibration = self._recommendation_runtime(enriched_context, memory_snapshot)
        recommendations = self.services.engine.simulate(
            enriched_context,
            request.candidates,
            calibration=calibration,
            prior_graph_snapshot=prior_snapshot,
        )
        graph = self._build_graph(enriched_context, memory_snapshot, recommendations)
        return RecommendationResponseV1(
            request_summary=RequestSummary(
                request_id=request_id,
                simulation="all candidate outcomes for this context",
                channel=enriched_context.channel,
                customer_id=enriched_context.customer_id,
                profile=_profile_summary(profile_summary),
                experience_memory=memory_snapshot.model_dump(mode="json"),
                self_distillation=self.services.engine.distillation.status(),
                haoe=self.services.engine.orchestrator.status(),
                ose_calibration=calibration,
                context_graph=graph.summary(),
            ),
            recommendations=recommendations,
        )

    def compare_outcomes(self, request: CompareOutcomesRequest, request_id: str) -> CompareOutcomesResponseV1:
        enriched_context, profile_summary = self.services.profile_service.enrich_context(request.context)
        enriched_context, memory_snapshot = self.services.experience_memory.enrich_context(enriched_context)
        prior_snapshot, calibration = self._recommendation_runtime(enriched_context, memory_snapshot)
        ranked_a, ranked_b, graph = self.services.engine.compare_candidates(
            enriched_context,
            request.candidate_id_a,
            request.candidate_id_b,
            use_ai_models=request.use_ai_models,
            calibration=calibration,
            prior_graph_snapshot=prior_snapshot,
        )
        winner = (
            request.candidate_id_a
            if ranked_a.ai_score.final_hybrid_score >= ranked_b.ai_score.final_hybrid_score
            else request.candidate_id_b
        )
        return CompareOutcomesResponseV1(
            request_summary=CompareRequestSummary(
                request_id=request_id,
                comparison="counterfactual candidate outcome comparison",
                channel=enriched_context.channel,
                customer_id=enriched_context.customer_id,
                profile=_profile_summary(profile_summary),
                experience_memory=memory_snapshot,
                ose_calibration=calibration,
                context_graph=graph.summary(),
                winner_candidate_id=winner,
            ),
            candidate_a=ranked_a,
            candidate_b=ranked_b,
            winner_candidate_id=winner,
        )

    def get_context_graph(
        self,
        customer_id: Optional[str],
        anonymous_id: Optional[str],
        include_live: bool,
    ):
        context = CustomerContext(customer_id=customer_id, anonymous_id=anonymous_id)
        memory_snapshot = self.services.experience_memory.get_snapshot(context)
        stored = self.services.graph_store.latest_snapshot(memory_snapshot.subject_id)
        payload = {"subject_id": memory_snapshot.subject_id, "stored_snapshot": stored}
        if include_live:
            enriched_context, _ = self.services.experience_memory.enrich_context(context)
            graph = ContextGraph(enriched_context, prior_snapshot=stored)
            payload["live_graph"] = graph.export()
        return payload

    def feedback(self, event: FeedbackEvent):
        self.services.feedback_store.append(event)
        memory_snapshot = self.services.experience_memory.record_feedback(event)
        graph = self._record_feedback_graph(event, memory_snapshot)
        record_feedback(event_type=event.event_type, converted=bool(event.converted))
        return {
            "status": "saved",
            "message": "Feedback captured and experience memory updated.",
            "feedback_count": self.services.feedback_store.count(),
            "experience_memory": memory_snapshot.model_dump(mode="json"),
            "context_graph": graph.summary(),
        }

    def scenario_examples(self):
        path = Path("data/scenario_training_master.csv")
        if not path.exists():
            return {"records": []}
        with path.open(newline="", encoding="utf-8") as handle:
            records = list(csv.DictReader(handle))
        for record in records:
            record["purpose"] = record.get("purpose") or _scenario_purpose(record)
        return {"count": len(records), "records": records}

    def empathy_simulate(self, request: EmpathySimulationRequest, request_id: str) -> dict:
        payload = self.services.empathy_engine.simulate(
            request.scenario_text,
            destination=request.destination,
            route_miles=request.route_miles,
            rental_days=request.rental_days,
        )
        payload["request_id"] = request_id
        return payload

    def process_batch(self, job_id: str, batch: BatchRecommendationRequest) -> None:
        self.services.job_store.mark_running(job_id)
        try:
            results = []
            for item in batch.requests:
                response = self.recommend(item, request_id=job_id)
                results.append(response.model_dump(mode="json"))
            self.services.job_store.mark_completed(job_id, {"responses": results, "count": len(results)})
        except Exception as error:
            self.services.job_store.mark_failed(job_id, str(error))


handlers = RecommendationHandlers()
