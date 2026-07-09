"""Pure helpers for four-tier benchmark probe metrics."""

from __future__ import annotations

from datetime import datetime, timezone
import statistics
from typing import Any


def utc_run_id() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_probe_metrics(
    body: dict[str, Any],
    *,
    expected_tier: str,
    expected_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Extract quality metrics from a /recommend response body."""
    summary = body.get("request_summary") or {}
    inference = summary.get("inference") or {}
    recommendations = body.get("recommendations") or []
    top = recommendations[0] if recommendations else {}
    candidate = top.get("candidate") or {}
    ai_score = top.get("ai_score") or {}
    orchestration = ai_score.get("orchestration") or {}

    observed_tier = inference.get("tier") or orchestration.get("tier")
    tier_match = observed_tier == expected_tier if observed_tier else False

    confidence = inference.get("confidence")
    if confidence is None:
        intent = ai_score.get("intent") or {}
        confidence = intent.get("confidence")

    sub_source = inference.get("sub_source") or ""
    fallback_from = inference.get("fallback_from")
    fallback = bool(
        fallback_from
        or sub_source.endswith("_fallback")
        or sub_source == "rules_fallback"
    )

    rules_fired = inference.get("rules_fired") or []
    candidate_id = candidate.get("id")
    alignment_match: bool | None = None
    if expected_candidate_id and candidate_id:
        alignment_match = candidate_id == expected_candidate_id

    haoe = summary.get("haoe") or {}
    provider_telemetry = summary.get("provider_telemetry") or {}

    return {
        "observed_tier": observed_tier,
        "tier_match": tier_match,
        "confidence": float(confidence) if confidence is not None else None,
        "fallback": fallback,
        "fallback_from": fallback_from,
        "sub_source": sub_source or None,
        "rules_fired_count": len(rules_fired),
        "top_candidate_id": candidate_id,
        "alignment_match": alignment_match,
        "session_cost_units": float(haoe.get("session_cost_units") or 0.0),
        "provider_cost_units": float(provider_telemetry.get("total_cost_units") or 0.0),
    }


def aggregate_probe_metrics(probes: list[dict[str, Any]]) -> dict[str, Any]:
    if not probes:
        return {
            "observed_tier_match_rate": 0.0,
            "fallback_rate": 0.0,
            "avg_confidence": None,
            "cost_units_total": 0.0,
            "accuracy_proxy": None,
            "explainability": {"rules_fired_avg": 0.0},
            "observed_tiers": [],
        }

    tier_matches = [probe["tier_match"] for probe in probes if probe.get("tier_match") is not None]
    fallbacks = [probe["fallback"] for probe in probes]
    confidences = [probe["confidence"] for probe in probes if probe.get("confidence") is not None]
    alignments = [probe["alignment_match"] for probe in probes if probe.get("alignment_match") is not None]
    rules_counts = [probe.get("rules_fired_count", 0) for probe in probes]
    cost_units = max(
        (probe.get("session_cost_units") or 0.0) + (probe.get("provider_cost_units") or 0.0)
        for probe in probes
    )

    accuracy_proxy = None
    if alignments:
        accuracy_proxy = {
            "training_alignment_top1": round(sum(1 for item in alignments if item) / len(alignments), 4),
            "probes_with_expected": len(alignments),
        }

    return {
        "observed_tier_match_rate": round(sum(tier_matches) / len(tier_matches), 4) if tier_matches else 0.0,
        "fallback_rate": round(sum(1 for item in fallbacks if item) / len(fallbacks), 4),
        "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "cost_units_total": round(cost_units, 6),
        "accuracy_proxy": accuracy_proxy,
        "explainability": {
            "rules_fired_avg": round(sum(rules_counts) / len(rules_counts), 2),
        },
        "observed_tiers": sorted({probe.get("observed_tier") for probe in probes if probe.get("observed_tier")}),
    }


def build_tier_result(
    *,
    tier_name: str,
    latencies_ms: list[float],
    errors: int,
    probes: list[dict[str, Any]],
    p95_budget_ms: float,
    expected_tier: str,
    duration_seconds: float,
    llm_enabled: bool,
    slm_enabled: bool,
) -> dict[str, Any]:
    latencies = sorted(latencies_ms)
    total_requests = len(latencies)
    p95_index = max(0, int(total_requests * 0.95) - 1) if total_requests else 0
    p95_ms = latencies[p95_index] if latencies else 0.0
    quality = aggregate_probe_metrics(probes)

    return {
        "tier": tier_name,
        "requests": total_requests,
        "errors": errors,
        "error_rate": round(errors / total_requests, 4) if total_requests else 0.0,
        "throughput_rps": round(total_requests / duration_seconds, 2) if duration_seconds > 0 else 0.0,
        "latency_ms": {
            "p50": round(statistics.median(latencies), 2) if latencies else 0.0,
            "p95": round(p95_ms, 2),
            "max": round(max(latencies), 2) if latencies else 0.0,
        },
        "p95_budget_ms": p95_budget_ms,
        "expected_tier": expected_tier,
        **quality,
        "passed": errors == 0 and p95_ms <= p95_budget_ms,
        "llm_enabled": llm_enabled,
        "slm_enabled": slm_enabled,
    }
