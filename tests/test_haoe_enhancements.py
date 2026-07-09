from app.haoe_policy import HAOEPolicyEngine
from app.inference.contracts import PUBLIC_INFERENCE_TIERS
from app.models import Channel, CustomerContext, IntentType, JourneyStage
from app.orchestration import HybridAIOrchestrationEngine
from app.rules.confidence import combined_rules_confidence
from app.rules.loader import RulesConfig
from app.scenario_nlp import ScenarioNLPParser


def _scenario_context(*, parser_confidence: float, intent=IntentType.purchase, journey=JourneyStage.consideration):
    return CustomerContext(
        anonymous_id="anon-haoe",
        channel=Channel.web,
        current_intent=intent,
        journey_stage=journey,
        channel_context={
            "source": "free_text_scenario",
            "parser_confidence": parser_confidence,
        },
    )


def test_haoe_policy_loads_yaml(tmp_path):
    policy_file = tmp_path / "haoe.yaml"
    policy_file.write_text(
        "confidence:\n  rules_min_confidence: 0.8\ncosts:\n  llm: 2.0\n",
        encoding="utf-8",
    )
    engine = HAOEPolicyEngine(str(policy_file))
    assert engine.section("confidence")["rules_min_confidence"] == 0.8
    assert engine.cost("llm") == 2.0


def test_public_inference_tiers_are_four():
    assert PUBLIC_INFERENCE_TIERS == ("rules", "slm", "ml", "llm")


def test_high_confidence_scenario_uses_rules_tier():
    orchestrator = HybridAIOrchestrationEngine()
    context = _scenario_context(parser_confidence=0.9)
    route = orchestrator.choose_route(
        context=context,
        context_text="family suv rental purchase on web",
        use_ai_models=True,
        use_llm=False,
        use_slm=False,
        llm_enabled=False,
        slm_enabled=True,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.4,
        tkge_inferred_intent=IntentType.research.value,
        rules_engine_confidence=0.82,
    )
    assert route.tier == "rules"


def test_low_parser_confidence_escalates_from_rules():
    orchestrator = HybridAIOrchestrationEngine()
    context = _scenario_context(parser_confidence=0.6)
    route = orchestrator.choose_route(
        context=context,
        context_text="family suv rental purchase on web",
        use_ai_models=True,
        use_llm=False,
        use_slm=False,
        llm_enabled=False,
        slm_enabled=True,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.4,
        tkge_inferred_intent=IntentType.research.value,
        rules_engine_confidence=0.5,
    )
    assert route.tier == "ml"


def test_tkge_boosts_rules_instead_of_separate_tier():
    orchestrator = HybridAIOrchestrationEngine()
    context = _scenario_context(parser_confidence=0.6)
    combined = combined_rules_confidence(
        parser_confidence=0.6,
        tkge_intent_confidence=0.82,
        rules_engine_confidence=0.5,
    )
    assert combined >= 0.75
    route = orchestrator.choose_route(
        context=context,
        context_text="family suv rental purchase on web",
        use_ai_models=True,
        use_llm=False,
        use_slm=False,
        llm_enabled=False,
        slm_enabled=True,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.82,
        tkge_inferred_intent=IntentType.purchase.value,
        rules_engine_confidence=0.5,
    )
    assert route.tier == "rules"
    assert "TKGE" in route.reason or "rules confidence" in route.reason.lower()


def test_forced_distilled_pattern_alias_maps_to_slm():
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
        inference_mode="distilled_pattern",
    )
    assert route.tier == HybridAIOrchestrationEngine.SLM_TIER


def test_forced_tkge_alias_maps_to_rules():
    orchestrator = HybridAIOrchestrationEngine()
    route = orchestrator.choose_route(
        context=CustomerContext(anonymous_id="anon-rules"),
        context_text="family suv booking",
        use_ai_models=True,
        use_llm=False,
        use_slm=False,
        llm_enabled=False,
        slm_enabled=True,
        distilled_pattern_available=False,
        inference_mode="tkge",
    )
    assert route.tier == "rules"


def test_ambiguous_context_routes_to_llm_when_enabled():
    orchestrator = HybridAIOrchestrationEngine()
    context = CustomerContext(
        anonymous_id="anon-haoe",
        channel=Channel.web,
        current_intent=IntentType.unknown,
    )
    route = orchestrator.choose_route(
        context=context,
        context_text="unknown visitor with unclear needs",
        use_ai_models=True,
        use_llm=True,
        use_slm=False,
        llm_enabled=True,
        slm_enabled=True,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.2,
        tkge_inferred_intent=IntentType.unknown.value,
    )
    assert route.tier == "llm"
    assert route.used_teacher_signal is True


def test_rules_config_loads_shared_signal_maps():
    config = RulesConfig()
    intent_signals = config.signal_map("intent_signals")
    assert IntentType.purchase.value in intent_signals
    assert "book" in intent_signals[IntentType.purchase.value]


def test_scenario_parser_emits_confidence_for_rich_text():
    parser = ScenarioNLPParser()
    context, details = parser.parse(
        "A family traveler on the website is comparing SUV rental upgrade options at the airport before booking.",
    )
    assert context.channel_context.get("parser_confidence", 0) >= 0.75
    assert details["parser_confidence"] >= 0.75


def test_scenario_parser_low_confidence_for_sparse_text():
    parser = ScenarioNLPParser()
    context, details = parser.parse("Hello.")
    assert context.channel_context.get("parser_confidence", 1) < 0.75
    assert details["parser_confidence"] < 0.75
