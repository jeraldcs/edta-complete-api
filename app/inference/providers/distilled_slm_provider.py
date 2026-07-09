from __future__ import annotations

from typing import Any

from app.inference.contracts import InferenceResult, RuleTrace
from app.models import ModelPrediction
from app.rules_engine import RulesEngine
from app.self_distillation import SelfDistillationStore


class DistilledSLMProvider:
    """Unified Distilled/SLM tier: distilled memory -> optional SLM endpoint -> rules fallback."""

    def __init__(
        self,
        distillation: SelfDistillationStore | None = None,
        rules: RulesEngine | None = None,
        remote_enricher=None,
    ):
        self.distillation = distillation or SelfDistillationStore()
        self.rules = rules or RulesEngine()
        self.remote_enricher = remote_enricher

    def infer(
        self,
        context_text: str,
        *,
        min_overlap: float = 0.35,
    ) -> tuple[ModelPrediction, ModelPrediction, InferenceResult]:
        distilled = self.distillation.predict(context_text, min_overlap=min_overlap)
        if distilled is not None:
            intent, journey = distilled
            confidence = max(intent.confidence, journey.confidence)
            return intent, journey, InferenceResult(
                tier="slm",
                provider="distilled_slm",
                intent=intent,
                journey_stage=journey,
                confidence=confidence,
                signals=["distilled_pattern"],
                sub_source="distilled_pattern",
                rules_fired=[RuleTrace(rule_id="distilled_pattern", contribution=confidence, reason="Pattern memory hit")],
            )

        if self.remote_enricher is not None:
            enriched = self.remote_enricher(context_text)
            if enriched:
                intent = ModelPrediction(
                    label=str(enriched.get("intent", "unknown")),
                    confidence=round(float(enriched.get("confidence", 0.0)), 4),
                    source="slm_endpoint",
                )
                journey = ModelPrediction(
                    label=str(enriched.get("journey_stage", "research")),
                    confidence=round(float(enriched.get("confidence", 0.0)), 4),
                    source="slm_endpoint",
                )
                confidence = max(intent.confidence, journey.confidence)
                return intent, journey, InferenceResult(
                    tier="slm",
                    provider="distilled_slm",
                    intent=intent,
                    journey_stage=journey,
                    confidence=confidence,
                    signals=["slm_endpoint"],
                    sub_source="slm_endpoint",
                    metadata={"reason": enriched.get("reason")},
                )

        intent, journey, confidence = self.rules.infer_from_text(context_text)
        return intent, journey, InferenceResult(
            tier="slm",
            provider="distilled_slm",
            intent=intent,
            journey_stage=journey,
            confidence=confidence,
            signals=["rules_fallback"],
            sub_source="rules_fallback",
            fallback_from="slm_endpoint",
            rules_fired=[RuleTrace(rule_id="rules_engine", contribution=confidence, reason="SLM rules fallback")],
        )

    def status(self) -> dict[str, Any]:
        return {
            "provider": "distilled_slm",
            "pattern_count": self.distillation.status().get("pattern_count", 0),
            "remote_enabled": self.remote_enricher is not None,
        }
