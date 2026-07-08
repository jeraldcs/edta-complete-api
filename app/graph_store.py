from datetime import datetime, timezone
from typing import Any

from app.db import Database


class GraphStore:
    """Persist TKGE snapshots per EML subject."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.init_schema()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save_snapshot(self, subject_id: str, snapshot: dict[str, Any]) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tkge_snapshots (subject_id, snapshot_json, created_at)
                VALUES (?, ?, ?)
                """,
                (subject_id, Database.json_dumps(snapshot), self._now()),
            )

    def latest_snapshot(self, subject_id: str) -> dict[str, Any] | None:
        with self.db.transaction() as connection:
            row = connection.execute(
                """
                SELECT snapshot_json FROM tkge_snapshots
                WHERE subject_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (subject_id,),
            ).fetchone()
            if not row:
                return None
            return Database.json_loads(row["snapshot_json"], None)

    def is_writable(self) -> bool:
        try:
            self.db.init_schema()
            with self.db.transaction() as connection:
                connection.execute("SELECT 1")
            return True
        except OSError:
            return False
