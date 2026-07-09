import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.catalog import DEFAULT_CANDIDATES
from app.db import Database
from app.eml_policy import EMLPolicyEngine
from app.models import CustomerContext, ExperienceMemorySnapshot, FeedbackEvent

CANDIDATE_BY_ID = {candidate.id: candidate for candidate in DEFAULT_CANDIDATES}


class EMLStore:
    """SQLite-backed Experience Memory Layer with identity resolution."""

    def __init__(
        self,
        db: Database | None = None,
        legacy_json_path: str | Path | None = None,
        policy: EMLPolicyEngine | None = None,
    ):
        self.db = db or Database()
        self.legacy_json_path = Path(legacy_json_path) if legacy_json_path else None
        self.policy = policy or EMLPolicyEngine()
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

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    def _decay_toward_baseline(self, score: float, baseline: float, age_hours: float, half_life_hours: float) -> float:
        if half_life_hours <= 0 or age_hours <= 0:
            return score
        decay_factor = math.exp(-age_hours / half_life_hours)
        return baseline + (score - baseline) * decay_factor

    def _apply_score_decay(self, trust_score: float, fatigue_score: float, updated_at: str | None) -> tuple[float, float]:
        defaults = self.policy.section("defaults")
        decay = self.policy.section("decay")
        trust_baseline = float(defaults.get("trust_baseline", 0.65))
        fatigue_baseline = float(defaults.get("fatigue_baseline", 0.0))
        timestamp = self._parse_iso(updated_at)
        if timestamp is None:
            return trust_score, fatigue_score

        age_hours = max(0.0, (datetime.now(timezone.utc) - timestamp).total_seconds() / 3600.0)
        decayed_trust = self._decay_toward_baseline(
            trust_score,
            trust_baseline,
            age_hours,
            float(decay.get("trust_half_life_hours", 168.0)),
        )
        decayed_fatigue = self._decay_toward_baseline(
            fatigue_score,
            fatigue_baseline,
            age_hours,
            float(decay.get("fatigue_half_life_hours", 48.0)),
        )
        return round(max(0.0, min(1.0, decayed_trust)), 4), round(max(0.0, min(1.0, decayed_fatigue)), 4)

    def _persist_decayed_scores(
        self,
        connection,
        subject_id: str,
        trust_score: float,
        fatigue_score: float,
        previous_trust: float,
        previous_fatigue: float,
    ) -> None:
        if round(trust_score, 4) == round(previous_trust, 4) and round(fatigue_score, 4) == round(previous_fatigue, 4):
            return
        connection.execute(
            "UPDATE eml_subjects SET trust_score = ?, fatigue_score = ?, updated_at = ? WHERE subject_id = ?",
            (trust_score, fatigue_score, self._now(), subject_id),
        )

    def _lookup_candidate(self, recommendation_id: str):
        return CANDIDATE_BY_ID.get(recommendation_id)

    def _apply_feedback_preferences(
        self,
        connection,
        subject_id: str,
        recommendation_id: str,
        event: FeedbackEvent,
        feedback_policy: dict[str, Any],
    ) -> None:
        event_type = event.event_type.lower()
        candidate = self._lookup_candidate(recommendation_id)

        if event_type == "click":
            self._update_preference(
                connection,
                subject_id,
                f"candidate:{recommendation_id}",
                float(feedback_policy.get("click_preference_delta", 0.25)),
            )
        elif event_type in {"dismiss", "unsubscribe", "complaint"}:
            self._update_preference(
                connection,
                subject_id,
                f"candidate:{recommendation_id}",
                float(feedback_policy.get("dismiss_preference_delta", -0.5)),
            )

        if not event.converted:
            return

        self._update_preference(
            connection,
            subject_id,
            f"candidate:{recommendation_id}",
            float(feedback_policy.get("convert_candidate_preference_delta", 1.0)),
        )
        self._update_preference(
            connection,
            subject_id,
            f"channel:{event.channel.value}",
            float(feedback_policy.get("convert_channel_preference_delta", 0.5)),
        )
        if candidate:
            self._update_preference(
                connection,
                subject_id,
                f"type:{candidate.type}",
                float(feedback_policy.get("convert_type_preference_delta", 0.35)),
            )
            category_delta = float(feedback_policy.get("convert_category_preference_delta", 0.2))
            for tag in candidate.content_tags[:2]:
                self._update_preference(connection, subject_id, f"category:{tag.lower()}", category_delta)

    def _exposure_fatigue_delta(self, recommendation: Any) -> float:
        exposure = self.policy.section("exposure")
        ai_score = getattr(recommendation, "ai_score", None)
        tapl = getattr(ai_score, "tapl", None) if ai_score else None
        action = getattr(getattr(tapl, "action", None), "value", None)
        if action in {"suppress", "generic_fallback"}:
            return 0.0
        if action == "delay":
            return float(exposure.get("delay_fatigue_delta", 0.01))
        if action == "soften":
            return float(exposure.get("soften_fatigue_delta", 0.03))
        return float(exposure.get("deliver_fatigue_delta", 0.04))

    def _counts_as_impression(self, recommendation: Any) -> bool:
        ai_score = getattr(recommendation, "ai_score", None)
        tapl = getattr(ai_score, "tapl", None) if ai_score else None
        action = getattr(getattr(tapl, "action", None), "value", None)
        return action not in {"suppress", "generic_fallback", "delay"}

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

            trust_score, fatigue_score = self._apply_score_decay(
                float(row["trust_score"]),
                float(row["fatigue_score"]),
                row["updated_at"],
            )
            self._persist_decayed_scores(
                connection,
                subject_id,
                trust_score,
                fatigue_score,
                float(row["trust_score"]),
                float(row["fatigue_score"]),
            )

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
                trust_score=trust_score,
                fatigue_score=fatigue_score,
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
            fatigue_score = float(row["fatigue_score"])
            impression_count = 0
            for item in recommendations:
                fatigue_score = min(1.0, fatigue_score + self._exposure_fatigue_delta(item))
                if self._counts_as_impression(item):
                    impression_count += 1

            connection.execute(
                "UPDATE eml_subjects SET fatigue_score = ?, updated_at = ? WHERE subject_id = ?",
                (round(fatigue_score, 4), now, subject_id),
            )

            for item in recommendations:
                candidate = getattr(item, "candidate", None)
                if candidate is None:
                    continue
                if not self._counts_as_impression(item):
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
                (impression_count, now, subject_id),
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
        feedback_policy = self.policy.section("feedback")

        with self.db.transaction() as connection:
            self._upsert_subject(connection, subject_id, subject_type)
            self._ensure_outcomes_row(connection, subject_id)

            row = connection.execute(
                "SELECT trust_score, fatigue_score, updated_at FROM eml_subjects WHERE subject_id = ?",
                (subject_id,),
            ).fetchone()
            trust_score, fatigue_score = self._apply_score_decay(
                float(row["trust_score"]),
                float(row["fatigue_score"]),
                row["updated_at"],
            )

            if event_type == "click":
                trust_score = min(1.0, trust_score + float(feedback_policy.get("click_trust_delta", 0.03)))
            elif event_type in {"dismiss", "unsubscribe", "complaint"}:
                trust_score = max(0.0, trust_score + float(feedback_policy.get("dismiss_trust_delta", -0.08)))
                fatigue_score = min(1.0, fatigue_score + float(feedback_policy.get("dismiss_fatigue_delta", 0.12)))

            if event.converted:
                trust_score = min(1.0, trust_score + float(feedback_policy.get("convert_trust_delta", 0.05)))

            self._apply_feedback_preferences(connection, subject_id, event.recommendation_id, event, feedback_policy)

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
