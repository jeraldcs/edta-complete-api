import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import FeedbackEvent


class FeedbackStore:
    """Append-only durable store for recommendation feedback events."""

    def __init__(self, store_path: str | None = None):
        self.store_path = Path(
            store_path or os.getenv("FEEDBACK_STORE_FILE", "data/feedback_events.json")
        )

    def _load(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        try:
            data = json.loads(self.store_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, events: list[dict[str, Any]]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(events, indent=2, sort_keys=True), encoding="utf-8")

    def append(self, event: FeedbackEvent) -> dict[str, Any]:
        events = self._load()
        record = event.model_dump(mode="json")
        record["recorded_at"] = datetime.now(timezone.utc).isoformat()
        events.append(record)
        self._save(events)
        return record

    def count(self) -> int:
        return len(self._load())

    def is_writable(self) -> bool:
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.store_path.exists():
                self.store_path.write_text("[]", encoding="utf-8")
            probe = self.store_path.with_suffix(".probe")
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False
