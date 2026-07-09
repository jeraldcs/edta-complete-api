from __future__ import annotations

from app.models import CustomerContext, IntentType


def combined_rules_confidence(
    *,
    parser_confidence: float,
    tkge_intent_confidence: float | None,
    rules_engine_confidence: float = 0.0,
) -> float:
    """Merge parser, TKGE timeline, and rules-engine scores into one rules-tier confidence."""
    scores = [max(0.0, min(1.0, parser_confidence)), max(0.0, min(1.0, rules_engine_confidence))]
    if tkge_intent_confidence is not None:
        scores.append(max(0.0, min(1.0, tkge_intent_confidence)))
    return round(min(0.96, max(scores)), 4)


def rules_signals_used(
    *,
    parser_confidence: float,
    tkge_intent_confidence: float | None,
    rules_engine_confidence: float,
) -> list[str]:
    signals: list[str] = []
    if parser_confidence > 0:
        signals.append("scenario_parser")
    if rules_engine_confidence > 0:
        signals.append("rules_engine")
    if tkge_intent_confidence is not None and tkge_intent_confidence > 0:
        signals.append("tkge_timeline")
    return signals


def scenario_rules_ready(context: CustomerContext) -> bool:
    return (
        context.current_intent is not None
        and context.journey_stage is not None
        and context.current_intent != IntentType.unknown
        and isinstance(context.channel_context, dict)
        and context.channel_context.get("source") == "free_text_scenario"
    )
