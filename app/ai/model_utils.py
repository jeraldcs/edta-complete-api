from pathlib import Path
from typing import Tuple, List, Optional
import joblib


class TextClassifier:
    def __init__(self, model_path: str, labels: List[str], fallback_label: str):
        self.model_path = Path(model_path)
        self.labels = labels
        self.fallback_label = fallback_label
        self.model = joblib.load(self.model_path) if self.model_path.exists() else None

    def predict(self, text: str) -> Tuple[str, float, str]:
        text = text.strip()
        if not text:
            return self.fallback_label, 0.0, "empty_input"

        if self.model is None:
            return self.fallback_label, 0.35, "fallback_no_model"

        label = self.model.predict([text])[0]
        confidence = 0.70
        if hasattr(self.model, "predict_proba"):
            confidence = float(max(self.model.predict_proba([text])[0]))

        if label not in self.labels:
            label = self.fallback_label

        return label, round(confidence, 4), "trained_model"
