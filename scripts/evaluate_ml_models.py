from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ai.intent_model import IntentModel
from app.ai.journey_model import JourneyStageModel
from app.ai.tapl_model import TAPLModel
from scripts.train_all_models import sync_training_data_from_master

OUTPUT_PATH = ROOT / "data" / "generated" / "ml_eval_summary.json"


def _calibration_bins(y_true: list[int], confidences: list[float], n_bins: int = 5) -> list[dict]:
    if not y_true:
        return []
    frame = pd.DataFrame({"y_true": y_true, "confidence": confidences})
    frame["bin"] = pd.cut(frame["confidence"], bins=n_bins, labels=False, include_lowest=True)
    bins: list[dict] = []
    for bin_index in sorted(frame["bin"].dropna().unique()):
        subset = frame[frame["bin"] == bin_index]
        avg_confidence = float(subset["confidence"].mean())
        accuracy = float(subset["y_true"].mean())
        bins.append({
            "bin": int(bin_index),
            "count": int(len(subset)),
            "avg_confidence": round(avg_confidence, 4),
            "accuracy": round(accuracy, 4),
            "calibration_gap": round(abs(avg_confidence - accuracy), 4),
        })
    return bins


def _evaluate_text_classifier(model, csv_path: Path, label_col: str) -> dict:
    frame = pd.read_csv(csv_path)
    texts = frame["text"].astype(str).tolist()
    labels = frame[label_col].astype(str).tolist()
    predictions = []
    confidences = []
    for text in texts:
        label, confidence, source = model.classifier.predict(text)
        predictions.append(label)
        confidences.append(confidence)
    y_true = [1 if pred == gold else 0 for pred, gold in zip(predictions, labels)]
    return {
        "samples": len(texts),
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "macro_f1": round(float(f1_score(labels, predictions, average="macro", zero_division=0)), 4),
        "source": source if texts else "empty",
        "calibration_bins": _calibration_bins(y_true, confidences),
    }


def build_report() -> dict:
    generated_paths = sync_training_data_from_master()
    intent_model = IntentModel()
    journey_model = JourneyStageModel()
    tapl_model = TAPLModel()

    intent_eval = _evaluate_text_classifier(intent_model, Path(generated_paths["intent"]), "intent")
    journey_eval = _evaluate_text_classifier(journey_model, Path(generated_paths["journey"]), "journey_stage")
    tapl_eval = _evaluate_text_classifier(tapl_model, Path(generated_paths["tapl"]), "action")

    return {
        "dataset": "scenario_training_master",
        "models_loaded": {
            "intent": intent_model.classifier.model is not None,
            "journey": journey_model.classifier.model is not None,
            "tapl": tapl_model.classifier.model is not None,
        },
        "intent": intent_eval,
        "journey": journey_eval,
        "tapl": tapl_eval,
        "overall": {
            "intent_accuracy": intent_eval["accuracy"],
            "journey_accuracy": journey_eval["accuracy"],
            "tapl_accuracy": tapl_eval["accuracy"],
            "avg_macro_f1": round(
                (intent_eval["macro_f1"] + journey_eval["macro_f1"] + tapl_eval["macro_f1"]) / 3,
                4,
            ),
        },
    }


def main() -> int:
    report = build_report()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
