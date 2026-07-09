from app.inference.contracts import PUBLIC_INFERENCE_TIERS
from app.inference.providers.distilled_slm_provider import DistilledSLMProvider
from app.llm.slm_client import SLMClient
from app.models import Channel, CustomerContext, IntentType, JourneyStage
from app.orchestration import HybridAIOrchestrationEngine
from app.rules.loader import RulesConfig
from app.rules_engine import RulesEngine


def test_rules_engine_loads_shared_yaml_signals(tmp_path):
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "intent_signals:\n  purchase: [buy, checkout]\n",
        encoding="utf-8",
    )
    engine = RulesEngine(RulesConfig(str(rules_file)))
    intent, _, _ = engine.infer_from_text("customer wants to buy now")
    assert intent.label == IntentType.purchase.value


def test_rules_engine_infers_purchase_from_booking_signals():
    engine = RulesEngine()
    context = CustomerContext(
        anonymous_id="anon-rules",
        channel=Channel.web,
        current_intent=IntentType.purchase,
        journey_stage=JourneyStage.consideration,
        session_events=["viewed_vehicle_page", "started_booking"],
        search_terms=["family SUV airport rental"],
    )
    intent, journey, confidence = engine.infer_from_context(context)
    assert intent.label == IntentType.purchase.value
    assert journey.label == JourneyStage.consideration.value
    assert confidence >= 0.8


def test_distilled_slm_provider_rules_fallback():
    provider = DistilledSLMProvider()
    intent, journey, result = provider.infer("family suv airport rental started booking")
    assert result.tier == "slm"
    assert result.sub_source == "rules_fallback"
    assert intent.label in {
        IntentType.purchase.value,
        IntentType.research.value,
        IntentType.upgrade.value,
    }
    assert journey.confidence > 0


def test_slm_client_enriches_intent_without_external_api():
    client = SLMClient()
    enriched = client.enrich_intent(
        "web purchase family suv airport rental started booking vehicle page"
    )
    assert enriched is not None
    assert enriched["intent"] in {
        IntentType.purchase.value,
        IntentType.research.value,
        IntentType.upgrade.value,
    }
    assert enriched["confidence"] > 0


def test_forced_slm_inference_mode():
    orchestrator = HybridAIOrchestrationEngine()
    route = orchestrator.choose_route(
        context=CustomerContext(anonymous_id="anon-slm"),
        context_text="family suv booking",
        use_ai_models=True,
        use_llm=False,
        use_slm=True,
        llm_enabled=False,
        slm_enabled=True,
        distilled_pattern_available=False,
        inference_mode="slm",
    )
    assert route.tier == HybridAIOrchestrationEngine.SLM_TIER


def test_public_inference_tiers_constant():
    assert PUBLIC_INFERENCE_TIERS == ("rules", "slm", "ml", "llm")


def test_load_test_payload_files_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    for tier in ("rules", "ml", "slm", "llm"):
        payload_path = root / "sample_requests" / "load_test" / f"{tier}.json"
        assert payload_path.exists(), payload_path
