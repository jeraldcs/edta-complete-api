from __future__ import annotations

from dataclasses import dataclass

from app.inference.contracts import RuleTrace
from app.models import ModelPrediction


@dataclass
class RulesInferenceResult:
    intent: ModelPrediction
    journey: ModelPrediction
    confidence: float
    rules_fired: list[RuleTrace]
    provider: str
    domain: str | None
    parser_confidence: float
    rules_engine_confidence: float
