import json
import os
from datetime import datetime, timezone
from typing import Any

from app.db import Database
from app.models import FeedbackEvent


class FeedbackStore:
    """Durable store for recommendation feedback events (SQLite-backed)."""

    def __init__(self, store_path: str | None = None, db: Database | None = None):
        self.store_path = store_path or os.getenv("FEEDBACK_STORE_FILE", "data/feedback_events.json")
        self.db = db or Database()
        self.db.init_schema()
        self._migrate_legacy_json_if_needed()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _migrate_legacy_json_if_needed(self) -> None:
        from pathlib import Path

        legacy_path = Path(self.store_path)
        if not legacy_path.exists():
            return
        with self.db.transaction() as connection:
            existing = connection.execute("SELECT COUNT(*) AS count FROM feedback_events").fetchone()
            if existing and existing["count"] > 0:
                return
        try:
            data = json.loads(legacy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, list) or not data:
            return
        with self.db.transaction() as connection:
            for record in data:
                connection.execute(
                    "INSERT INTO feedback_events (event_json, recorded_at) VALUES (?, ?)",
                    (json.dumps(record, default=str), record.get("recorded_at") or self._now()),
                )

    def append(self, event: FeedbackEvent) -> dict[str, Any]:
        record = event.model_dump(mode="json")
        record["recorded_at"] = self._now()
        with self.db.transaction() as connection:
            connection.execute(
                "INSERT INTO feedback_events (event_json, recorded_at) VALUES (?, ?)",
                (json.dumps(record, default=str), record["recorded_at"]),
            )
        return record

    def count(self) -> int:
        with self.db.transaction() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM feedback_events").fetchone()
        return int(row["count"]) if row else 0

    def is_writable(self) -> bool:
        try:
            with self.db.transaction() as connection:
                connection.execute(
                    "INSERT INTO feedback_events (event_json, recorded_at) VALUES (?, ?)",
                    ('{"probe": true}', self._now()),
                )
                connection.execute("DELETE FROM feedback_events WHERE event_json = ?", ('{"probe": true}',))
            return True
        except OSError:
            return False
