from app.ai.model_utils import TextClassifier
from app.models import JourneyStage, ModelPrediction


class JourneyStageModel:
    def __init__(self):
        self.classifier = TextClassifier(
            model_path="models/journey_model.joblib",
            labels=[x.value for x in JourneyStage],
            fallback_label=JourneyStage.research.value,
        )

    def predict(self, context_text: str) -> ModelPrediction:
        label, confidence, source = self.classifier.predict(context_text)
        return ModelPrediction(label=label, confidence=confidence, source=source)
