import asyncio
import json
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings
from app.db import Database
from app.observability.metrics import record_webhook_delivery
from app.webhook_validation import WebhookValidationError, validate_webhook_target_url


class EventBus:
    """In-process event bus with SSE fan-out and webhook delivery."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.init_schema()
        self.subscribers: set[asyncio.Queue] = set()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def register_webhook(self, target_url: str, event_types: list[str]) -> dict[str, Any]:
        try:
            validated_url = validate_webhook_target_url(target_url)
        except WebhookValidationError as error:
            raise ValueError(str(error)) from error
        webhook_id = str(uuid.uuid4())
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO webhook_subscriptions (id, target_url, event_types_json, created_at, active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (webhook_id, validated_url, Database.json_dumps(event_types), self._now()),
            )
        return {
            "id": webhook_id,
            "target_url": validated_url,
            "event_types": event_types,
            "active": True,
        }

    def list_webhooks(self) -> list[dict[str, Any]]:
        with self.db.transaction() as connection:
            rows = connection.execute(
                "SELECT id, target_url, event_types_json, created_at, active FROM webhook_subscriptions ORDER BY id DESC"
            ).fetchall()
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "target_url": row["target_url"],
                "event_types": Database.json_loads(row["event_types_json"], []),
                "created_at": row["created_at"],
                "active": bool(row["active"]),
            })
        return results

    def deactivate_webhook(self, webhook_id: str) -> bool:
        with self.db.transaction() as connection:
            cursor = connection.execute(
                "UPDATE webhook_subscriptions SET active = 0 WHERE id = ?",
                (webhook_id,),
            )
            return cursor.rowcount > 0

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.discard(queue)

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "payload": payload,
            "occurred_at": self._now(),
        }
        dead = []
        for queue in self.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(queue)
        for queue in dead:
            self.subscribers.discard(queue)
        await self._dispatch_webhooks(event)

    async def _dispatch_webhooks(self, event: dict[str, Any]) -> None:
        with self.db.transaction() as connection:
            rows = connection.execute(
                "SELECT id, target_url, event_types_json FROM webhook_subscriptions WHERE active = 1"
            ).fetchall()

        if not rows:
            return

        timeout = settings.webhook_timeout_seconds
        async with httpx.AsyncClient(timeout=timeout) as client:
            for row in rows:
                event_types = Database.json_loads(row["event_types_json"], [])
                if event_types and event["event_type"] not in event_types:
                    continue
                delivered = await self._post_with_retry(client, row["target_url"], event)
                record_webhook_delivery(success=delivered, event_type=event["event_type"])

    @staticmethod
    async def _post_with_retry(client: httpx.AsyncClient, target_url: str, event: dict[str, Any]) -> bool:
        delays = (0.0, 0.5, 1.5)
        for delay in delays:
            if delay:
                await asyncio.sleep(delay)
            try:
                response = await client.post(target_url, json=event)
                if response.status_code < 500:
                    return response.is_success
            except httpx.HTTPError:
                continue
        return False

    async def stream_events(self, history_limit: int = 20):
        queue = self.subscribe()
        try:
            yield f"event: connected\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                event = await queue.get()
                yield f"event: {event['event_type']}\ndata: {json.dumps(event)}\n\n"
        finally:
            self.unsubscribe(queue)


class JobStore:
    """SQLite-backed async job tracking."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.init_schema()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, job_type: str, payload: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO async_jobs (id, job_type, status, payload_json, created_at)
                VALUES (?, ?, 'queued', ?, ?)
                """,
                (job_id, job_type, Database.json_dumps(payload), self._now()),
            )
        return job_id

    def mark_running(self, job_id: str) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                "UPDATE async_jobs SET status = 'running', started_at = ? WHERE id = ?",
                (self._now(), job_id),
            )

    def mark_completed(self, job_id: str, result: dict[str, Any]) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                """
                UPDATE async_jobs
                SET status = 'completed', result_json = ?, completed_at = ?
                WHERE id = ?
                """,
                (Database.json_dumps(result), self._now(), job_id),
            )

    def mark_failed(self, job_id: str, error: str) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                """
                UPDATE async_jobs
                SET status = 'failed', error = ?, completed_at = ?
                WHERE id = ?
                """,
                (error, self._now(), job_id),
            )

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self.db.transaction() as connection:
            row = connection.execute("SELECT * FROM async_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return {
            "job_id": row["id"],
            "job_type": row["job_type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "result": Database.json_loads(row["result_json"], None),
            "error": row["error"],
        }
