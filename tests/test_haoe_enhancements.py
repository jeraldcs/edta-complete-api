from app.haoe_policy import HAOEPolicyEngine
from app.models import Channel, CustomerContext, IntentType, JourneyStage
from app.orchestration import HybridAIOrchestrationEngine
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


def test_high_confidence_scenario_uses_rules_tier():
    orchestrator = HybridAIOrchestrationEngine()
    context = _scenario_context(parser_confidence=0.9)
    route = orchestrator.choose_route(
        context=context,
        context_text="family suv rental purchase on web",
        use_ai_models=True,
        use_llm=False,
        llm_enabled=False,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.4,
        tkge_inferred_intent=IntentType.research.value,
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
        llm_enabled=False,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.4,
        tkge_inferred_intent=IntentType.research.value,
    )
    assert route.tier == "ml"


def test_tkge_tier_when_parser_weak_and_graph_confident():
    orchestrator = HybridAIOrchestrationEngine()
    context = _scenario_context(parser_confidence=0.6)
    route = orchestrator.choose_route(
        context=context,
        context_text="family suv rental purchase on web",
        use_ai_models=True,
        use_llm=False,
        llm_enabled=False,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.72,
        tkge_inferred_intent=IntentType.purchase.value,
    )
    assert route.tier == HybridAIOrchestrationEngine.TKGE_TIER


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
        llm_enabled=True,
        distilled_pattern_available=False,
        tkge_intent_confidence=0.2,
        tkge_inferred_intent=IntentType.unknown.value,
    )
    assert route.tier == "llm"
    assert route.used_teacher_signal is True


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
