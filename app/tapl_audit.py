from datetime import datetime, timezone

from app.db import Database
from app.models import TAPLDecision


class TAPLAuditLog:
    """Append-only governance audit trail for TAPL decisions."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.init_schema()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def record(
        self,
        *,
        subject_id: str | None,
        candidate_id: str,
        channel: str,
        decision: TAPLDecision,
        policy_source: str | None,
    ) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO tapl_audit
                (subject_id, candidate_id, channel, action, reason, trust_score, fatigue_score, policy_source, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subject_id,
                    candidate_id,
                    channel,
                    decision.action.value,
                    decision.reason,
                    decision.trust_score,
                    decision.fatigue_score,
                    policy_source,
                    self._now(),
                ),
            )

    def count(self) -> int:
        with self.db.transaction() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM tapl_audit").fetchone()
            return int(row["count"])
