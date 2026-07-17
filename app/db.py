import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def default_db_path() -> Path:
    return Path(os.getenv("EDTA_DB_PATH", "data/edta.db"))


class Database:
    """Shared SQLite store for EML, TKGE snapshots, TAPL audit, and HAOE telemetry."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or default_db_path())

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def init_schema(self) -> None:
        with self.transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS eml_subjects (
                    subject_id TEXT PRIMARY KEY,
                    subject_type TEXT NOT NULL,
                    trust_score REAL NOT NULL DEFAULT 0.65,
                    fatigue_score REAL NOT NULL DEFAULT 0.0,
                    linked_subject_id TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS eml_identity_aliases (
                    alias_key TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    alias_type TEXT NOT NULL,
                    alias_value TEXT NOT NULL,
                    FOREIGN KEY (subject_id) REFERENCES eml_subjects(subject_id)
                );

                CREATE TABLE IF NOT EXISTS eml_preferences (
                    subject_id TEXT NOT NULL,
                    pref_key TEXT NOT NULL,
                    pref_value TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    updated_at TEXT,
                    PRIMARY KEY (subject_id, pref_key),
                    FOREIGN KEY (subject_id) REFERENCES eml_subjects(subject_id)
                );

                CREATE TABLE IF NOT EXISTS eml_recommendation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    title TEXT,
                    channel TEXT,
                    shown_at TEXT,
                    score REAL,
                    outcome_json TEXT,
                    FOREIGN KEY (subject_id) REFERENCES eml_subjects(subject_id)
                );

                CREATE TABLE IF NOT EXISTS eml_outcomes (
                    subject_id TEXT PRIMARY KEY,
                    impressions INTEGER NOT NULL DEFAULT 0,
                    clicks INTEGER NOT NULL DEFAULT 0,
                    conversions INTEGER NOT NULL DEFAULT 0,
                    revenue REAL NOT NULL DEFAULT 0.0,
                    last_event_at TEXT,
                    FOREIGN KEY (subject_id) REFERENCES eml_subjects(subject_id)
                );

                CREATE TABLE IF NOT EXISTS tkge_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tkge_subject_created
                    ON tkge_snapshots(subject_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS tapl_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT,
                    candidate_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    trust_score REAL,
                    fatigue_score REAL,
                    policy_source TEXT,
                    recorded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rules_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_id TEXT,
                    domain TEXT,
                    provider TEXT NOT NULL,
                    intent_label TEXT NOT NULL,
                    journey_label TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    parser_confidence REAL,
                    tkge_confidence REAL,
                    rules_fired_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_rules_audit_recorded
                    ON rules_audit(recorded_at DESC);

                CREATE TABLE IF NOT EXISTS haoe_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tier TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    estimated_latency_ms INTEGER,
                    estimated_cost_units REAL,
                    llm_circuit_open INTEGER NOT NULL DEFAULT 0,
                    recorded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS provider_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    model TEXT,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_units REAL NOT NULL DEFAULT 0,
                    latency_ms INTEGER NOT NULL DEFAULT 0,
                    recorded_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_provider_telemetry_recorded
                    ON provider_telemetry(recorded_at DESC);

                CREATE TABLE IF NOT EXISTS async_jobs (
                    id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS webhook_subscriptions (
                    id TEXT PRIMARY KEY,
                    target_url TEXT NOT NULL,
                    event_types_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS feedback_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_events_recorded
                    ON feedback_events(recorded_at DESC);

                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    idempotency_key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_idempotency_expires
                    ON idempotency_keys(expires_at);
                """
            )

    @staticmethod
    def json_dumps(value: Any) -> str:
        return json.dumps(value, sort_keys=True, default=str)

    @staticmethod
    def json_loads(value: str | None, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
