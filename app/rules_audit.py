import json
from datetime import datetime, timezone

from app.db import Database
from app.inference.contracts import RuleTrace


class RulesAuditLog:
    """Append-only audit trail for rules-tier inference decisions."""

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
        domain: str | None,
        provider: str,
        intent_label: str,
        journey_label: str,
        confidence: float,
        parser_confidence: float | None = None,
        tkge_confidence: float | None = None,
        rules_fired: list[RuleTrace] | None = None,
    ) -> None:
        payload = [item.model_dump() for item in (rules_fired or [])]
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO rules_audit
                (subject_id, domain, provider, intent_label, journey_label, confidence,
                 parser_confidence, tkge_confidence, rules_fired_json, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    subject_id,
                    domain,
                    provider,
                    intent_label,
                    journey_label,
                    confidence,
                    parser_confidence,
                    tkge_confidence,
                    json.dumps(payload),
                    self._now(),
                ),
            )

    def count(self) -> int:
        with self.db.transaction() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM rules_audit").fetchone()
            return int(row["count"])

    def recent(self, limit: int = 10) -> list[dict]:
        with self.db.transaction() as connection:
            rows = connection.execute(
                """
                SELECT subject_id, domain, provider, intent_label, journey_label, confidence,
                       parser_confidence, tkge_confidence, rules_fired_json, recorded_at
                FROM rules_audit
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            try:
                item["rules_fired"] = json.loads(item.pop("rules_fired_json") or "[]")
            except json.JSONDecodeError:
                item["rules_fired"] = []
            results.append(item)
        return results
