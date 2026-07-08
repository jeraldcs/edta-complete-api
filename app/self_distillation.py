import json
import os
from pathlib import Path
from typing import Any

from app.models import IntentType, JourneyStage, ModelPrediction


class SelfDistillationStore:
    """Tiny local SLM strategy: persist high-confidence teacher labels as reusable patterns."""

    def __init__(self, store_path: str | None = None):
        self.store_path = Path(
            store_path
            or os.getenv("DISTILLED_SLM_FILE", "data/distilled_slm_memory.json")
        )

    def _load(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(records[-500:], indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token
            for token in text.lower().replace("_", " ").replace("-", " ").split()
            if len(token) > 2
        }

    def predict(self, context_text: str) -> tuple[ModelPrediction, ModelPrediction] | None:
        query = self._tokens(context_text)
        if not query:
            return None

        best_record = None
        best_score = 0.0
        for record in self._load():
            tokens = set(record.get("tokens", []))
            if not tokens:
                continue
            score = len(query.intersection(tokens)) / max(1, len(query.union(tokens)))
            if score > best_score:
                best_record = record
                best_score = score

        if not best_record or best_score < 0.35:
            return None

        return (
            ModelPrediction(
                label=best_record.get("intent", IntentType.unknown.value),
                confidence=round(min(0.92, 0.55 + best_score), 4),
                source="distilled_slm",
            ),
            ModelPrediction(
                label=best_record.get("journey_stage", JourneyStage.research.value),
                confidence=round(min(0.92, 0.55 + best_score), 4),
                source="distilled_slm",
            ),
        )

    def learn(
        self,
        context_text: str,
        intent: ModelPrediction,
        journey: ModelPrediction,
        teacher: str,
    ) -> dict[str, Any]:
        if intent.confidence < 0.75 or journey.confidence < 0.75:
            return {"stored": False, "reason": "confidence_below_distillation_threshold"}

        tokens = sorted(self._tokens(context_text))
        if not tokens:
            return {"stored": False, "reason": "no_distillable_tokens"}

        records = self._load()
        fingerprint = " ".join(tokens[:80])
        for record in records:
            if record.get("fingerprint") == fingerprint:
                record["uses"] = int(record.get("uses", 1)) + 1
                self._save(records)
                return {"stored": True, "reason": "updated_existing_pattern", "pattern_count": len(records)}

        records.append({
            "fingerprint": fingerprint,
            "tokens": tokens[:80],
            "intent": intent.label,
            "journey_stage": journey.label,
            "teacher": teacher,
            "uses": 1,
        })
        self._save(records)
        return {"stored": True, "reason": "stored_teacher_pattern", "pattern_count": len(records)}

    def status(self) -> dict[str, Any]:
        records = self._load()
        return {
            "enabled": True,
            "store": str(self.store_path),
            "pattern_count": len(records),
            "strategy": "high_confidence_labels_distilled_to_local_pattern_memory",
            "tier_name": "distilled_pattern",
        }
