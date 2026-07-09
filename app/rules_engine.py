from __future__ import annotations

import re
from typing import Any

from app.models import Channel, CustomerContext, IntentType, JourneyStage, ModelPrediction
from app.rules.loader import RulesConfig, get_rules_config


class RulesEngine:
    """Deterministic intent and journey inference from structured visitor context."""

    def __init__(self, rules_config: RulesConfig | None = None):
        self.rules_config = rules_config or get_rules_config()
        self.INTENT_SIGNALS = self.rules_config.signal_map("intent_signals")
        self.JOURNEY_SIGNALS = self.rules_config.signal_map("journey_signals")
        self.CHANNEL_EVENT_BOOSTS = self.rules_config.signal_map("channel_event_boosts")
        self._confidence = self.rules_config.confidence()

    def infer_from_context(self, context: CustomerContext) -> tuple[ModelPrediction, ModelPrediction, float]:
        text = self._context_text(context)
        intent_label, intent_score = self._infer_label(context.current_intent, text, self.INTENT_SIGNALS)
        journey_label, journey_score = self._infer_label(context.journey_stage, text, self.JOURNEY_SIGNALS)
        channel_boost = self._channel_boost(context)
        confidence = round(min(0.96, max(intent_score, journey_score) + channel_boost), 4)
        return (
            ModelPrediction(label=intent_label, confidence=confidence, source="rules_engine"),
            ModelPrediction(label=journey_label, confidence=confidence, source="rules_engine"),
            confidence,
        )

    def infer_from_text(self, context_text: str) -> tuple[ModelPrediction, ModelPrediction, float]:
        intent_label, intent_score = self._score_label(context_text, self.INTENT_SIGNALS)
        journey_label, journey_score = self._score_label(context_text, self.JOURNEY_SIGNALS)
        confidence = round(min(0.96, max(intent_score, journey_score)), 4)
        return (
            ModelPrediction(label=intent_label, confidence=confidence, source="rules_engine"),
            ModelPrediction(label=journey_label, confidence=confidence, source="rules_engine"),
            confidence,
        )

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

    def _channel_boost(self, context: CustomerContext) -> float:
        text = self._context_text(context)
        boosts = self.CHANNEL_EVENT_BOOSTS.get(context.channel.value, ())
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
