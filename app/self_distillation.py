import json
import os
import threading
from pathlib import Path
from typing import Any

from app.models import IntentType, JourneyStage, ModelPrediction

# One lock per store path so concurrent learn() calls cannot corrupt JSON RMW.
_STORE_LOCKS: dict[str, threading.Lock] = {}
_STORE_LOCKS_GUARD = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve()) if path.exists() or path.parent.exists() else str(path)
    with _STORE_LOCKS_GUARD:
        lock = _STORE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _STORE_LOCKS[key] = lock
        return lock


class SelfDistillationStore:
    """Tiny local SLM strategy: persist high-confidence teacher labels as reusable patterns."""

    def __init__(self, store_path: str | None = None):
        self.store_path = Path(
            store_path
            or os.getenv("DISTILLED_SLM_FILE", "data/distilled_slm_memory.json")
        )
        self._lock = _lock_for(self.store_path)

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

    def predict(self, context_text: str, min_overlap: float | None = None) -> tuple[ModelPrediction, ModelPrediction] | None:
        query = self._tokens(context_text)
        if not query:
            return None

        threshold = 0.35 if min_overlap is None else float(min_overlap)
        best_record = None
        best_score = 0.0
        with self._lock:
            records = self._load()
        for record in records:
            tokens = set(record.get("tokens", []))
            if not tokens:
                continue
            score = len(query.intersection(tokens)) / max(1, len(query.union(tokens)))
            if score > best_score:
                best_record = record
                best_score = score

        if not best_record or best_score < threshold:
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
        min_confidence: float | None = None,
    ) -> dict[str, Any]:
        threshold = 0.75 if min_confidence is None else float(min_confidence)
        if intent.confidence < threshold or journey.confidence < threshold:
            return {"stored": False, "reason": "confidence_below_distillation_threshold"}

        tokens = sorted(self._tokens(context_text))
        if not tokens:
            return {"stored": False, "reason": "no_distillable_tokens"}

        fingerprint = " ".join(tokens[:80])
        with self._lock:
            records = self._load()
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
        with self._lock:
            records = self._load()
        return {
            "enabled": True,
            "store": str(self.store_path),
            "pattern_count": len(records),
            "strategy": "high_confidence_labels_distilled_to_local_pattern_memory",
            "tier_name": "distilled_pattern",
        }
