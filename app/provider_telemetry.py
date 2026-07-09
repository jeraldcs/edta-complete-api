from datetime import datetime, timezone
from typing import Any

from app.db import Database
from app.llm.cost_estimator import CompletionUsage


class ProviderTelemetryStore:
    """Telemetry for LLM/SLM provider calls including token and cost estimates."""

    def __init__(self, db: Database | None = None):
        self.db = db or Database()
        self.db.init_schema()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def record(self, usage: CompletionUsage) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                """
                INSERT INTO provider_telemetry
                (provider, operation, model, input_tokens, output_tokens,
                 estimated_cost_units, latency_ms, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    usage.provider,
                    usage.operation,
                    usage.model,
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.estimated_cost_units,
                    usage.latency_ms,
                    self._now(),
                ),
            )

    def count(self) -> int:
        with self.db.transaction() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM provider_telemetry").fetchone()
            return int(row["count"])

    def summary(self) -> dict[str, Any]:
        with self.db.transaction() as connection:
            totals = connection.execute(
                """
                SELECT
                    COUNT(*) AS call_count,
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(estimated_cost_units), 0) AS total_cost_units
                FROM provider_telemetry
                """
            ).fetchone()
            provider_rows = connection.execute(
                """
                SELECT provider, COUNT(*) AS count, COALESCE(SUM(estimated_cost_units), 0) AS cost_units
                FROM provider_telemetry
                GROUP BY provider
                ORDER BY count DESC
                """
            ).fetchall()
            operation_rows = connection.execute(
                """
                SELECT operation, COUNT(*) AS count
                FROM provider_telemetry
                GROUP BY operation
                ORDER BY count DESC
                """
            ).fetchall()
        return {
            "call_count": int(totals["call_count"]),
            "input_tokens": int(totals["input_tokens"]),
            "output_tokens": int(totals["output_tokens"]),
            "total_cost_units": round(float(totals["total_cost_units"]), 6),
            "providers": {
                row["provider"]: {
                    "count": int(row["count"]),
                    "cost_units": round(float(row["cost_units"]), 6),
                }
                for row in provider_rows
            },
            "operations": {row["operation"]: int(row["count"]) for row in operation_rows},
        }
