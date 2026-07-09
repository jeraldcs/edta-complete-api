from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models import ModelPrediction

PublicInferenceTier = Literal["rules", "slm", "ml", "llm"]

PUBLIC_INFERENCE_TIERS: tuple[str, ...] = ("rules", "slm", "ml", "llm")


class RuleTrace(BaseModel):
    rule_id: str
    priority: int = 0
    matched: bool = True
    contribution: float = 0.0
    reason: str = ""


class InferenceResult(BaseModel):
    """Unified readout for the four public inference tiers."""

    tier: PublicInferenceTier
    provider: str
    intent: ModelPrediction
    journey_stage: ModelPrediction
    confidence: float
    signals: list[str] = Field(default_factory=list)
    rules_fired: list[RuleTrace] = Field(default_factory=list)
    sub_source: str | None = None
    fallback_from: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def model_dump_summary(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "provider": self.provider,
            "confidence": self.confidence,
            "intent_label": self.intent.label,
            "intent_source": self.intent.source,
            "journey_label": self.journey_stage.label,
            "journey_source": self.journey_stage.source,
            "signals": self.signals,
            "sub_source": self.sub_source,
            "fallback_from": self.fallback_from,
            "domain": self.metadata.get("domain"),
            "rules_fired": [item.model_dump() for item in self.rules_fired],
        }
