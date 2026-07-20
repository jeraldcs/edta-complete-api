"""Regression tests for review fixes 1–5."""

from contextvars import copy_context

from app.empathy.hidden_needs import HiddenNeedsExtractor
from app.inference.providers.distilled_slm_provider import DistilledSLMProvider
from app.models import Channel, CustomerContext, IntentType, JourneyStage, ModelPrediction
from app.recommender import RecommendationEngine
from app.scenario_nlp import ScenarioNLPParser
from app.services.recommendation_handlers import RecommendationHandlers


def test_automobile_does_not_infer_mobile_channel():
    parser = ScenarioNLPParser()
    context, summary = parser.parse(
        "Looking for an automobile rental at the airport for a snowstorm trip"
    )
    assert summary["detected_domain"] == "travel"
    assert context.channel == Channel.web


def test_travel_automobile_uses_vehicle_catalog_not_restaurants():
    from app.catalog import vehicle_candidates

    handlers = RecommendationHandlers()
    context = CustomerContext(
        anonymous_id="auto-mobile-test",
        channel=Channel.mobile,  # simulate legacy mis-parse
        journey_stage=JourneyStage.research,
        current_intent=IntentType.research,
        business_context={"detected_domain": "travel"},
        consent={"personalization": True, "profile_lookup": True},
    )
    nlp_summary = {"detected_domain": "travel"}
    resolved, candidates = handlers._resolve_scenario_candidates(context, None, nlp_summary)
    assert resolved.channel == Channel.web
    vehicle_ids = {c.id for c in vehicle_candidates()}
    assert candidates
    assert {c.id for c in candidates} == vehicle_ids
    assert not any(c.id.startswith("mobile_restaurant") for c in candidates)


def test_distilled_slm_tolerates_malformed_remote_json():
    def _bad_enrich(_text, catalog=None):
        return {
            "intent": "not_a_real_intent",
            "journey_stage": "not_a_stage",
            "confidence": "high",
            "candidate_id": "hybrid_midsize",
            "vehicle_confidence": "maybe",
            "reason": "bad payload",
        }

    provider = DistilledSLMProvider(remote_enricher=_bad_enrich)
    intent, journey, result = provider.infer("need a car", catalog=[{"id": "hybrid_midsize"}])
    assert intent.label == IntentType.unknown.value
    assert journey.label == JourneyStage.research.value
    assert intent.confidence == 0.0
    assert result.sub_source == "slm_endpoint"
    assert result.metadata["vehicle_proposal"]["candidate_id"] == "hybrid_midsize"
    # Ranking must accept the coerced journey label.
    JourneyStage(journey.label)


def test_rank_candidate_tolerates_invalid_journey_label():
    from app.catalog import vehicle_candidates
    from app.context_graph import ContextGraph
    from app.orchestration import OrchestrationDecision

    engine = RecommendationEngine()
    context = CustomerContext(
        anonymous_id="journey-guard",
        channel=Channel.web,
        journey_stage=JourneyStage.research,
        current_intent=IntentType.research,
        consent={"personalization": True, "profile_lookup": True},
    )

    candidate = vehicle_candidates()[0]
    graph = ContextGraph(context)
    intent = ModelPrediction(label=IntentType.research.value, confidence=0.5, source="test")
    journey = ModelPrediction(label="not_a_stage", confidence=0.5, source="test")
    route = OrchestrationDecision(
        tier="rules",
        reason="test",
        estimated_latency_ms=1,
        estimated_cost_units=0.0,
    )

    ranked = engine._rank_candidate(
        context,
        candidate,
        graph,
        graph.to_text(),
        intent,
        journey,
        route,
        use_ai_models=False,
        use_llm_explanation=False,
    )
    assert ranked is not None
    assert ranked.ai_score.journey_stage.label == JourneyStage.research.value


def test_eighty_year_old_does_not_trigger_toddler_family():
    profile = HiddenNeedsExtractor().extract(
        "Traveling with my 80-year-old grandmother only. No kids."
    )
    assert "elderly_passenger" in profile.persona_tags
    assert "toddler_family" not in profile.persona_tags


def test_year_old_daughter_still_triggers_toddler_family():
    profile = HiddenNeedsExtractor().extract(
        "i will be traveling with my wife and year-old daughter"
    )
    assert "toddler_family" in profile.persona_tags


def test_family_of_children_triggers_toddler_family():
    profile = HiddenNeedsExtractor().extract(
        "We are a family of five with three children, multiple suitcases, a stroller"
    )
    assert "toddler_family" in profile.persona_tags


def test_engine_inference_state_is_request_isolated():
    engine = RecommendationEngine()
    from app.inference.contracts import InferenceResult

    def _set_and_read(label: str):
        engine.last_inference = InferenceResult(
            tier="rules",
            provider="test",
            intent=ModelPrediction(label=label, confidence=1.0, source="test"),
            journey_stage=ModelPrediction(label=JourneyStage.research.value, confidence=1.0, source="test"),
            confidence=1.0,
        )
        return engine.last_inference.intent.label if engine.last_inference else None

    ctx_a = copy_context()
    ctx_b = copy_context()
    label_a = ctx_a.run(_set_and_read, "purchase")
    label_b = ctx_b.run(_set_and_read, "support")
    assert label_a == "purchase"
    assert label_b == "support"
    # Parent context should remain untouched by child contexts.
    assert engine.last_inference is None
