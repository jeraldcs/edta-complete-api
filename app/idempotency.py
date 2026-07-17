from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.db import Database


class IdempotencyStore:
    """SQLite-backed idempotency cache for mutating API requests."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.init_schema()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def get(self, key: str) -> dict[str, Any] | None:
        with self.db.transaction() as connection:
            row = connection.execute(
                "SELECT response_json, expires_at FROM idempotency_keys WHERE idempotency_key = ?",
                (key,),
            ).fetchone()
        if not row:
            return None
        if row["expires_at"] and row["expires_at"] < self._now():
            return None
        return Database.json_loads(row["response_json"], None)

    def save(self, key: str, response: dict[str, Any]) -> None:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(seconds=settings.idempotency_ttl_seconds)
        ).isoformat()
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO idempotency_keys (idempotency_key, response_json, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(idempotency_key) DO UPDATE SET
                    response_json = excluded.response_json,
                    expires_at = excluded.expires_at
                """,
                (key, json.dumps(response, default=str), self._now(), expires_at),
            )


def read_idempotency_key(request) -> str | None:
    from fastapi import HTTPException

    raw = request.headers.get("Idempotency-Key")
    if raw is None:
        return None
    key = raw.strip()
    if not key or len(key) > 128:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be 1-128 characters.")
    return key
