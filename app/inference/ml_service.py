from __future__ import annotations

from dataclasses import dataclass, field

from app.ai.channel_model import ChannelFitModel
from app.ai.intent_model import IntentModel
from app.ai.journey_model import JourneyStageModel
from app.ai.outcome_model import OutcomeSimulationModel
from app.ai.ranker_model import FinalRankerModel
from app.ai.semantic_similarity import SemanticSimilarityModel
from app.ai.tapl_model import TAPLModel
from app.catalog import DEFAULT_CANDIDATES
from app.context_graph import ContextGraph
from app.inference.contracts import InferenceResult
from app.models import IntentType, JourneyStage, ModelPrediction, RecommendationCandidate


@dataclass
class MLInferenceResult:
    intent: ModelPrediction
    journey: ModelPrediction
    confidence: float
    tkge_augmented: bool = False
    models_used: list[str] = field(default_factory=list)


class MLInferenceService:
    """Unified local ML inference for intent, journey, ranking, and semantic scoring."""

    def __init__(self, candidates: list[RecommendationCandidate] | None = None):
        self.intent_model = IntentModel()
        self.journey_model = JourneyStageModel()
        self.tapl_model = TAPLModel()
        self.channel_model = ChannelFitModel()
        self.semantic_model = SemanticSimilarityModel()
        self.outcome_model = OutcomeSimulationModel()
        self.ranker_model = FinalRankerModel()
        self._catalog_warmed = False
        self.warm_catalog(candidates or DEFAULT_CANDIDATES)

    @staticmethod
    def candidate_text(candidate: RecommendationCandidate) -> str:
        return " ".join([
            candidate.title,
            candidate.description,
            " ".join(candidate.content_tags),
        ])

    def warm_catalog(self, candidates: list[RecommendationCandidate]) -> None:
        documents = [self.candidate_text(candidate) for candidate in candidates]
        self.semantic_model.warm_start(documents)
        self._catalog_warmed = bool(documents)

    def infer_intent_journey(
        self,
        context_text: str,
        graph: ContextGraph,
    ) -> MLInferenceResult:
        intent = self.intent_model.predict(context_text)
        journey = self.journey_model.predict(context_text)
        models_used = ["intent_model", "journey_model"]
        tkge_augmented = False

        if intent.label == IntentType.unknown.value:
            inferred_intent, inferred_confidence = graph.infer_intent()
            if inferred_intent != IntentType.unknown.value:
                intent = ModelPrediction(label=inferred_intent, confidence=inferred_confidence, source="ml+tkge")
                models_used.append("tkge_intent")
                tkge_augmented = True

        if journey.confidence < 0.5 or journey.label == JourneyStage.research.value:
            inferred_journey, inferred_confidence = graph.infer_journey_stage()
            if inferred_confidence >= journey.confidence:
                journey = ModelPrediction(label=inferred_journey, confidence=inferred_confidence, source="ml+tkge")
                models_used.append("tkge_journey")
                tkge_augmented = True

        confidence = round(max(intent.confidence, journey.confidence), 4)
        return MLInferenceResult(
            intent=intent,
            journey=journey,
            confidence=confidence,
            tkge_augmented=tkge_augmented,
            models_used=models_used,
        )

    def to_inference_result(self, ml_result: MLInferenceResult) -> InferenceResult:
        signals = ["local_classifiers"]
        if ml_result.tkge_augmented:
            signals.append("tkge_timeline")
        return InferenceResult(
            tier="ml",
            provider="ml_inference_service",
            intent=ml_result.intent,
            journey_stage=ml_result.journey,
            confidence=ml_result.confidence,
            signals=signals,
            metadata={"models_used": ml_result.models_used},
        )

    def status(self) -> dict:
        return {
            "provider": "ml_inference_service",
            "catalog_warmed": self._catalog_warmed,
            "models": {
                "intent": self.intent_model.classifier.model is not None,
                "journey": self.journey_model.classifier.model is not None,
                "tapl": self.tapl_model.classifier.model is not None,
                "outcome_conversion": self.outcome_model.conversion_model is not None,
                "outcome_revenue": self.outcome_model.revenue_model is not None,
                "ranker": self.ranker_model.model is not None,
            },
        }
