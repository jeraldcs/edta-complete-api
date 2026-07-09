from __future__ import annotations

import re
from typing import Any

from app.inference.contracts import RuleTrace
from app.models import Channel, CustomerContext, IntentType, JourneyStage, ModelPrediction
from app.rules.confidence import combined_rules_confidence, scenario_rules_ready
from app.rules.loader import RulesConfig, get_rules_config
from app.rules.packs import RulePackRegistry, get_rule_pack_registry
from app.rules.result import RulesInferenceResult


class RulesEngine:
    """Deterministic intent and journey inference from structured visitor context."""

    def __init__(
        self,
        rules_config: RulesConfig | None = None,
        pack_registry: RulePackRegistry | None = None,
    ):
        self.rules_config = rules_config or get_rules_config()
        self.pack_registry = pack_registry or get_rule_pack_registry()
        self._base_intent = self.rules_config.signal_map("intent_signals")
        self._base_journey = self.rules_config.signal_map("journey_signals")
        self._base_channel = self.rules_config.signal_map("channel_event_boosts")
        self._confidence = self.rules_config.confidence()

    def _signal_maps(self, context: CustomerContext):
        pack_intent, pack_journey, pack_channel = self.pack_registry.merged_signal_maps(context)
        intent = {**self._base_intent}
        journey = {**self._base_journey}
        channel = {**self._base_channel}
        for label, signals in pack_intent.items():
            intent[label] = intent.get(label, ()) + signals
        for label, signals in pack_journey.items():
            journey[label] = journey.get(label, ()) + signals
        for label, signals in pack_channel.items():
            channel[label] = channel.get(label, ()) + signals
        return intent, journey, channel

    def infer_from_context(self, context: CustomerContext) -> tuple[ModelPrediction, ModelPrediction, float]:
        result = self.infer_with_trace(context)
        return result.intent, result.journey, result.confidence

    def infer_from_text(self, context_text: str) -> tuple[ModelPrediction, ModelPrediction, float]:
        context = CustomerContext(anonymous_id="rules-text", channel=Channel.web)
        intent, journey, channel = self._signal_maps(context)
        intent_label, intent_score = self._score_label(context_text, intent)
        journey_label, journey_score = self._score_label(context_text, journey)
        confidence = round(min(0.96, max(intent_score, journey_score)), 4)
        return (
            ModelPrediction(label=intent_label, confidence=confidence, source="rules_engine"),
            ModelPrediction(label=journey_label, confidence=confidence, source="rules_engine"),
            confidence,
        )

    def infer_with_trace(
        self,
        context: CustomerContext,
        *,
        parser_confidence: float | None = None,
        tkge_intent_confidence: float | None = None,
    ) -> RulesInferenceResult:
        text = self._context_text(context)
        intent_signals, journey_signals, channel_boosts = self._signal_maps(context)
        intent_label, intent_score = self._infer_label(context.current_intent, text, intent_signals)
        journey_label, journey_score = self._infer_label(context.journey_stage, text, journey_signals)
        channel_boost = self._channel_boost(context, channel_boosts)
        rules_engine_confidence = round(min(0.96, max(intent_score, journey_score) + channel_boost), 4)

        parser_score = self._parser_confidence(context, parser_confidence)
        combined = combined_rules_confidence(
            parser_confidence=parser_score,
            tkge_intent_confidence=tkge_intent_confidence,
            rules_engine_confidence=rules_engine_confidence,
        )

        if scenario_rules_ready(context):
            intent_label = context.current_intent.value
            journey_label = context.journey_stage.value

        rules_fired = self._evaluate_explicit_rules(context, text, intent_label, journey_label)
        if parser_score > 0:
            rules_fired.insert(0, RuleTrace(
                rule_id="scenario_parser",
                priority=200,
                contribution=parser_score,
                reason="Scenario parser confidence merged into rules pipeline",
            ))
        if channel_boost > 0:
            rules_fired.append(RuleTrace(
                rule_id="channel.event_boost",
                priority=50,
                contribution=channel_boost,
                reason=f"Channel {context.channel.value} event boost",
            ))
        if tkge_intent_confidence is not None and tkge_intent_confidence > 0:
            rules_fired.append(RuleTrace(
                rule_id="tkge_timeline",
                priority=40,
                contribution=tkge_intent_confidence,
                reason="TKGE timeline confidence boost",
            ))

        provider = self.pack_registry.provider_name(context)
        return RulesInferenceResult(
            intent=ModelPrediction(label=intent_label, confidence=combined, source="rules"),
            journey=ModelPrediction(label=journey_label, confidence=combined, source="rules"),
            confidence=combined,
            rules_fired=rules_fired,
            provider=provider,
            domain=self.pack_registry.detect_domain(context),
            parser_confidence=parser_score,
            rules_engine_confidence=rules_engine_confidence,
        )

    @staticmethod
    def _parser_confidence(context: CustomerContext, parser_confidence: float | None) -> float:
        if parser_confidence is not None:
            return max(0.0, min(1.0, float(parser_confidence)))
        channel_context = context.channel_context if isinstance(context.channel_context, dict) else {}
        stored = channel_context.get("parser_confidence")
        if stored is not None:
            return max(0.0, min(1.0, float(stored)))
        return 0.0

    def _evaluate_explicit_rules(
        self,
        context: CustomerContext,
        text: str,
        intent_label: str,
        journey_label: str,
    ) -> list[RuleTrace]:
        traces: list[RuleTrace] = []
        tokens = set(re.findall(r"[a-z0-9_]+", text.lower()))
        for rule in self.pack_registry.explicit_rules(context):
            rule_id = str(rule.get("id", "unknown.rule"))
            priority = int(rule.get("priority", 0))
            rule_type = str(rule.get("type", "boost"))
            signals_raw = rule.get("signals", [])
            signals = tuple(str(signal) for signal in signals_raw) if isinstance(signals_raw, list) else ()
            matched = any(signal in text or signal.replace(" ", "_") in tokens for signal in signals)
            if rule_type == "channel_boost":
                matched = matched and str(rule.get("channel", "")) == context.channel.value
            if rule_type == "intent_match":
                matched = matched and str(rule.get("label", "")) == intent_label
            if not matched:
                continue
            weight = float(rule.get("weight", 0.1))
            traces.append(RuleTrace(
                rule_id=rule_id,
                priority=priority,
                contribution=round(weight, 4),
                reason=f"Matched {rule_type} rule in {rule.get('pack_id', 'base')} pack",
            ))
        traces.sort(key=lambda item: item.priority, reverse=True)
        return traces

    @staticmethod
    def _context_text(context: CustomerContext) -> str:
        parts = [
            context.channel.value,
            context.current_intent.value if context.current_intent else "",
            context.journey_stage.value if context.journey_stage else "",
            " ".join(context.session_events),
            " ".join(context.search_terms),
        ]
        for group in (
            context.profile_attributes,
            context.business_context,
            context.channel_context,
            context.device_context,
        ):
            if isinstance(group, dict):
                parts.extend(str(value).replace("_", " ") for value in group.values())
        return " ".join(part for part in parts if part).lower()

    def _infer_label(
        self,
        explicit: IntentType | JourneyStage | None,
        text: str,
        signal_map: dict[str, tuple[str, ...]],
    ) -> tuple[str, float]:
        if explicit is not None:
            explicit_value = explicit.value
            bonus = (
                self._confidence.get("explicit_signal_bonus", 0.12)
                if any(token in text for token in signal_map.get(explicit_value, ()))
                else 0.0
            )
            base = self._confidence.get("explicit_intent_base", 0.82)
            return explicit_value, round(min(0.96, base + bonus), 4)
        return self._score_label(text, signal_map)

    def _score_label(self, text: str, signal_map: dict[str, tuple[str, ...]]) -> tuple[str, float]:
        tokens = set(re.findall(r"[a-z0-9_]+", text.lower()))
        best_label = IntentType.unknown.value if "unknown" in signal_map else next(iter(signal_map))
        hit_base = self._confidence.get("keyword_hit_base", 0.45)
        hit_increment = self._confidence.get("keyword_hit_increment", 0.12)
        best_score = hit_base - 0.1
        for label, signals in signal_map.items():
            hits = sum(1 for signal in signals if signal in text or signal.replace(" ", "_") in tokens)
            if hits == 0:
                continue
            score = min(0.94, hit_base + hits * hit_increment)
            if score > best_score:
                best_label = label
                best_score = score
        return best_label, round(best_score, 4)

    def _channel_boost(self, context: CustomerContext, channel_boosts: dict[str, tuple[str, ...]]) -> float:
        text = self._context_text(context)
        boosts = channel_boosts.get(context.channel.value, ())
        if any(token in text for token in boosts):
            return self._confidence.get("channel_boost", 0.05)
        return 0.0

    def explain(self, context_text: str, recommendation_payload: dict[str, Any]) -> str:
        candidate_title = recommendation_payload.get("candidate_title", "this recommendation")
        intent = recommendation_payload.get("intent", "unknown")
        journey = recommendation_payload.get("journey_stage", "unknown")
        tapl_action = recommendation_payload.get("tapl_action", "show")
        outcome = recommendation_payload.get("expected_outcome", 0)
        return (
            f"{candidate_title} was selected because rules inference detected intent={intent}, "
            f"journey={journey}, TAPL={tapl_action}, and expected outcome={outcome:.2f}."
        )
