from datetime import datetime, timezone
from typing import Any

from app.db import Database


class HAOETelemetryStore:
    """Route telemetry for Hybrid AI Orchestration Engine."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.init_schema()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def record(
        self,
        *,
        tier: str,
        reason: str,
        estimated_latency_ms: int,
        estimated_cost_units: float,
        llm_circuit_open: bool,
    ) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO haoe_telemetry
                (tier, reason, estimated_latency_ms, estimated_cost_units, llm_circuit_open, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tier,
                    reason,
                    estimated_latency_ms,
                    estimated_cost_units,
                    int(llm_circuit_open),
                    self._now(),
                ),
            )

    def summary(self) -> dict[str, Any]:
        with self.db.transaction() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS route_count,
                    COALESCE(SUM(estimated_cost_units), 0) AS total_cost_units
                FROM haoe_telemetry
                """
            ).fetchone()
            tier_rows = connection.execute(
                """
                SELECT tier, COUNT(*) AS count
                FROM haoe_telemetry
                GROUP BY tier
                ORDER BY count DESC
                """
            ).fetchall()
            return {
                "route_count": int(row["route_count"]),
                "total_cost_units": round(float(row["total_cost_units"]), 4),
                "tiers": {item["tier"]: int(item["count"]) for item in tier_rows},
            }
