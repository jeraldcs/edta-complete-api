import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.db import Database
from app.models import CustomerContext, ExperienceMemorySnapshot, FeedbackEvent


class EMLStore:
    """SQLite-backed Experience Memory Layer with identity resolution."""

    def __init__(self, db: Database | None = None, legacy_json_path: str | Path | None = None):
        self.db = db or Database()
        self.legacy_json_path = Path(legacy_json_path) if legacy_json_path else None
        self.db.init_schema()
        self._migrate_legacy_json()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def alias_key(alias_type: str, alias_value: str) -> str:
        return f"{alias_type}:{alias_value}"

    @staticmethod
    def subject_key(context: CustomerContext | FeedbackEvent) -> tuple[str, str]:
        if getattr(context, "customer_id", None):
            return f"customer:{context.customer_id}", "known"
        if getattr(context, "anonymous_id", None):
            return f"anonymous:{context.anonymous_id}", "anonymous"
        return "anonymous:sessionless", "anonymous"

    def _migrate_legacy_json(self) -> None:
        if not self.legacy_json_path or not self.legacy_json_path.exists():
            return

        with self.db.transaction() as connection:
            existing = connection.execute("SELECT COUNT(*) AS count FROM eml_subjects").fetchone()["count"]
            if existing:
                return

            try:
                legacy = json.loads(self.legacy_json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return

            for subject_id, record in legacy.items():
                self._upsert_subject(connection, subject_id, record.get("subject_type", "anonymous"), record)
                outcomes = record.get("outcomes", {})
                connection.execute(
                    """
                    INSERT INTO eml_outcomes (subject_id, impressions, clicks, conversions, revenue, last_event_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        subject_id,
                        int(outcomes.get("impressions", 0)),
                        int(outcomes.get("clicks", 0)),
                        int(outcomes.get("conversions", 0)),
                        float(outcomes.get("revenue", 0.0)),
                        outcomes.get("last_event_at"),
                    ),
                )
                for item in record.get("recommendation_history", []):
                    connection.execute(
                        """
                        INSERT INTO eml_recommendation_history
                        (subject_id, candidate_id, title, channel, shown_at, score, outcome_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            subject_id,
                            item.get("candidate_id"),
                            item.get("title"),
                            item.get("channel"),
                            item.get("shown_at"),
                            item.get("score"),
                            Database.json_dumps(item.get("outcome")) if item.get("outcome") else None,
                        ),
                    )
                for key, value in record.get("preferences", {}).items():
                    connection.execute(
                        """
                        INSERT INTO eml_preferences (subject_id, pref_key, pref_value, weight, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (subject_id, key, Database.json_dumps(value), 1.0, self._now()),
                    )

    def _upsert_subject(
        self,
        connection,
        subject_id: str,
        subject_type: str,
        record: dict[str, Any] | None = None,
    ) -> None:
        record = record or {}
        connection.execute(
            """
            INSERT INTO eml_subjects (subject_id, subject_type, trust_score, fatigue_score, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(subject_id) DO UPDATE SET
                subject_type=excluded.subject_type,
                trust_score=excluded.trust_score,
                fatigue_score=excluded.fatigue_score,
                updated_at=excluded.updated_at
            """,
            (
                subject_id,
                subject_type,
                float(record.get("trust_score", 0.65)),
                float(record.get("fatigue_score", 0.0)),
                self._now(),
            ),
        )

    def _ensure_outcomes_row(self, connection, subject_id: str) -> None:
        connection.execute(
            """
            INSERT INTO eml_outcomes (subject_id)
            VALUES (?)
            ON CONFLICT(subject_id) DO NOTHING
            """,
            (subject_id,),
        )

    def resolve_subject(self, context: CustomerContext | FeedbackEvent) -> tuple[str, str]:
        customer_id = getattr(context, "customer_id", None)
        anonymous_id = getattr(context, "anonymous_id", None)

        if customer_id and anonymous_id:
            return self._link_identities(customer_id, anonymous_id)
        return self.subject_key(context)

    def _link_identities(self, customer_id: str, anonymous_id: str) -> tuple[str, str]:
        customer_subject = f"customer:{customer_id}"
        anonymous_subject = f"anonymous:{anonymous_id}"

        with self.db.transaction() as connection:
            self._upsert_subject(connection, customer_subject, "known")
            self._ensure_outcomes_row(connection, customer_subject)

            anonymous_row = connection.execute(
                "SELECT * FROM eml_subjects WHERE subject_id = ?",
                (anonymous_subject,),
            ).fetchone()

            if anonymous_row:
                customer_row = connection.execute(
                    "SELECT * FROM eml_subjects WHERE subject_id = ?",
                    (customer_subject,),
                ).fetchone()
                merged_trust = max(customer_row["trust_score"], anonymous_row["trust_score"])
                merged_fatigue = max(customer_row["fatigue_score"], anonymous_row["fatigue_score"])
                connection.execute(
                    """
                    UPDATE eml_subjects
                    SET trust_score = ?, fatigue_score = ?, linked_subject_id = ?, updated_at = ?
                    WHERE subject_id = ?
                    """,
                    (merged_trust, merged_fatigue, anonymous_subject, self._now(), customer_subject),
                )

                anon_outcomes = connection.execute(
                    "SELECT * FROM eml_outcomes WHERE subject_id = ?",
                    (anonymous_subject,),
                ).fetchone()
                if anon_outcomes:
                    connection.execute(
                        """
                        UPDATE eml_outcomes
                        SET impressions = impressions + ?,
                            clicks = clicks + ?,
                            conversions = conversions + ?,
                            revenue = revenue + ?,
                            last_event_at = COALESCE(?, last_event_at)
                        WHERE subject_id = ?
                        """,
                        (
                            anon_outcomes["impressions"],
                            anon_outcomes["clicks"],
                            anon_outcomes["conversions"],
                            anon_outcomes["revenue"],
                            anon_outcomes["last_event_at"],
                            customer_subject,
                        ),
                    )

                connection.execute(
                    """
                    UPDATE eml_recommendation_history
                    SET subject_id = ?
                    WHERE subject_id = ?
                    """,
                    (customer_subject, anonymous_subject),
                )
                connection.execute(
                    """
                    INSERT INTO eml_preferences (subject_id, pref_key, pref_value, weight, updated_at)
                    SELECT ?, pref_key, pref_value, weight, updated_at
                    FROM eml_preferences
                    WHERE subject_id = ?
                    ON CONFLICT(subject_id, pref_key) DO UPDATE SET
                        weight = MAX(eml_preferences.weight, excluded.weight),
                        updated_at = excluded.updated_at
                    """,
                    (customer_subject, anonymous_subject),
                )

            connection.execute(
                """
                INSERT INTO eml_identity_aliases (alias_key, subject_id, alias_type, alias_value)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(alias_key) DO UPDATE SET subject_id = excluded.subject_id
                """,
                (
                    self.alias_key("customer", customer_id),
                    customer_subject,
                    "customer",
                    customer_id,
                ),
            )
            connection.execute(
                """
                INSERT INTO eml_identity_aliases (alias_key, subject_id, alias_type, alias_value)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(alias_key) DO UPDATE SET subject_id = excluded.subject_id
                """,
                (
                    self.alias_key("anonymous", anonymous_id),
                    customer_subject,
                    "anonymous",
                    anonymous_id,
                ),
            )

        return customer_subject, "known"

    def _load_preferences(self, connection, subject_id: str) -> dict[str, Any]:
        rows = connection.execute(
            "SELECT pref_key, pref_value, weight FROM eml_preferences WHERE subject_id = ?",
            (subject_id,),
        ).fetchall()
        preferences: dict[str, Any] = {}
        for row in rows:
            preferences[row["pref_key"]] = {
                "value": Database.json_loads(row["pref_value"], row["pref_value"]),
                "weight": row["weight"],
            }
        return preferences

    def _load_history(self, connection, subject_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = connection.execute(
            """
            SELECT candidate_id, title, channel, shown_at, score, outcome_json
            FROM eml_recommendation_history
            WHERE subject_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (subject_id, limit),
        ).fetchall()
        history = []
        for row in reversed(rows):
            item = {
                "candidate_id": row["candidate_id"],
                "title": row["title"],
                "channel": row["channel"],
                "shown_at": row["shown_at"],
                "score": row["score"],
            }
            outcome = Database.json_loads(row["outcome_json"], None)
            if outcome:
                item["outcome"] = outcome
            history.append(item)
        return history

    def get_snapshot(self, context: CustomerContext) -> ExperienceMemorySnapshot:
        subject_id, subject_type = self.resolve_subject(context)
        with self.db.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM eml_subjects WHERE subject_id = ?",
                (subject_id,),
            ).fetchone()
            if not row:
                self._upsert_subject(connection, subject_id, subject_type)
                self._ensure_outcomes_row(connection, subject_id)
                row = connection.execute(
                    "SELECT * FROM eml_subjects WHERE subject_id = ?",
                    (subject_id,),
                ).fetchone()

            outcomes_row = connection.execute(
                "SELECT * FROM eml_outcomes WHERE subject_id = ?",
                (subject_id,),
            ).fetchone()
            outcomes = {
                "impressions": outcomes_row["impressions"] if outcomes_row else 0,
                "clicks": outcomes_row["clicks"] if outcomes_row else 0,
                "conversions": outcomes_row["conversions"] if outcomes_row else 0,
                "revenue": outcomes_row["revenue"] if outcomes_row else 0.0,
                "last_event_at": outcomes_row["last_event_at"] if outcomes_row else None,
            }

            return ExperienceMemorySnapshot(
                subject_id=subject_id,
                subject_type=row["subject_type"],
                trust_score=row["trust_score"],
                fatigue_score=row["fatigue_score"],
                preferences=self._load_preferences(connection, subject_id),
                recommendation_history=self._load_history(connection, subject_id),
                outcomes=outcomes,
            )

    def get_calibration(self, context: CustomerContext) -> dict[str, float]:
        snapshot = self.get_snapshot(context)
        impressions = max(int(snapshot.outcomes.get("impressions", 0)), 1)
        clicks = int(snapshot.outcomes.get("clicks", 0))
        conversions = int(snapshot.outcomes.get("conversions", 0))
        return {
            "historical_ctr": round(clicks / impressions, 4),
            "historical_cvr": round(conversions / impressions, 4),
            "avg_revenue_per_impression": round(
                float(snapshot.outcomes.get("revenue", 0.0)) / impressions,
                4,
            ),
        }

    def record_recommendations(self, context: CustomerContext, recommendations: list[Any]) -> ExperienceMemorySnapshot:
        subject_id, subject_type = self.resolve_subject(context)
        now = self._now()

        with self.db.transaction() as connection:
            self._upsert_subject(connection, subject_id, subject_type)
            self._ensure_outcomes_row(connection, subject_id)

            row = connection.execute(
                "SELECT trust_score, fatigue_score FROM eml_subjects WHERE subject_id = ?",
                (subject_id,),
            ).fetchone()
            fatigue_score = min(1.0, float(row["fatigue_score"]) + 0.04 * len(recommendations))
            connection.execute(
                "UPDATE eml_subjects SET fatigue_score = ?, updated_at = ? WHERE subject_id = ?",
                (round(fatigue_score, 4), now, subject_id),
            )

            for item in recommendations:
                candidate = getattr(item, "candidate", None)
                if candidate is None:
                    continue
                connection.execute(
                    """
                    INSERT INTO eml_recommendation_history
                    (subject_id, candidate_id, title, channel, shown_at, score)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        subject_id,
                        candidate.id,
                        candidate.title,
                        candidate.channel.value,
                        now,
                        getattr(getattr(item, "ai_score", None), "final_hybrid_score", None),
                    ),
                )

            connection.execute(
                """
                UPDATE eml_outcomes
                SET impressions = impressions + ?, last_event_at = ?
                WHERE subject_id = ?
                """,
                (len(recommendations), now, subject_id),
            )

        return self.get_snapshot(context)

    def _update_preference(self, connection, subject_id: str, pref_key: str, delta: float) -> None:
        row = connection.execute(
            "SELECT weight FROM eml_preferences WHERE subject_id = ? AND pref_key = ?",
            (subject_id, pref_key),
        ).fetchone()
        weight = round(min(5.0, (row["weight"] if row else 0.0) + delta), 4)
        connection.execute(
            """
            INSERT INTO eml_preferences (subject_id, pref_key, pref_value, weight, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(subject_id, pref_key) DO UPDATE SET
                weight = excluded.weight,
                updated_at = excluded.updated_at
            """,
            (subject_id, pref_key, Database.json_dumps(pref_key), weight, self._now()),
        )

    def record_feedback(self, event: FeedbackEvent) -> ExperienceMemorySnapshot:
        subject_id, subject_type = self.resolve_subject(event)
        now = self._now()
        event_type = event.event_type.lower()

        with self.db.transaction() as connection:
            self._upsert_subject(connection, subject_id, subject_type)
            self._ensure_outcomes_row(connection, subject_id)

            row = connection.execute(
                "SELECT trust_score, fatigue_score FROM eml_subjects WHERE subject_id = ?",
                (subject_id,),
            ).fetchone()
            trust_score = float(row["trust_score"])
            fatigue_score = float(row["fatigue_score"])

            if event_type == "click":
                trust_score = min(1.0, trust_score + 0.03)
                self._update_preference(connection, subject_id, f"candidate:{event.recommendation_id}", 0.25)
            elif event_type in {"dismiss", "unsubscribe", "complaint"}:
                trust_score = max(0.0, trust_score - 0.08)
                fatigue_score = min(1.0, fatigue_score + 0.12)
                self._update_preference(connection, subject_id, f"candidate:{event.recommendation_id}", -0.5)

            if event.converted:
                trust_score = min(1.0, trust_score + 0.05)
                self._update_preference(connection, subject_id, f"candidate:{event.recommendation_id}", 1.0)
                self._update_preference(connection, subject_id, f"channel:{event.channel.value}", 0.5)

            connection.execute(
                "UPDATE eml_subjects SET trust_score = ?, fatigue_score = ?, updated_at = ? WHERE subject_id = ?",
                (round(trust_score, 4), round(fatigue_score, 4), now, subject_id),
            )

            connection.execute(
                """
                UPDATE eml_outcomes
                SET clicks = clicks + ?,
                    conversions = conversions + ?,
                    revenue = revenue + ?,
                    last_event_at = ?
                WHERE subject_id = ?
                """,
                (
                    1 if event_type == "click" else 0,
                    1 if event.converted else 0,
                    float(event.revenue or 0.0),
                    now,
                    subject_id,
                ),
            )

            history_row = connection.execute(
                """
                SELECT id FROM eml_recommendation_history
                WHERE subject_id = ? AND candidate_id = ? AND outcome_json IS NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (subject_id, event.recommendation_id),
            ).fetchone()
            if history_row:
                outcome = {
                    "event_type": event.event_type,
                    "converted": event.converted,
                    "revenue": event.revenue,
                    "recorded_at": now,
                }
                connection.execute(
                    "UPDATE eml_recommendation_history SET outcome_json = ? WHERE id = ?",
                    (Database.json_dumps(outcome), history_row["id"]),
                )

        return self.get_snapshot(CustomerContext(
            customer_id=event.customer_id,
            anonymous_id=event.anonymous_id,
        ))

    def is_writable(self) -> bool:
        try:
            self.db.init_schema()
            with self.db.transaction() as connection:
                connection.execute("SELECT 1")
            return True
        except OSError:
            return False
