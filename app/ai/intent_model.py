from app.ai.model_utils import TextClassifier
from app.models import IntentType, ModelPrediction


class IntentModel:
    def __init__(self):
        self.classifier = TextClassifier(
            model_path="models/intent_model.joblib",
            labels=[x.value for x in IntentType],
            fallback_label=IntentType.unknown.value,
        )

    def predict(self, context_text: str) -> ModelPrediction:
        label, confidence, source = self.classifier.predict(context_text)
        return ModelPrediction(label=label, confidence=confidence, source=source)
