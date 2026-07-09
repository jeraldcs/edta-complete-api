from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def load_test_payloads():
    payloads = {}
    for tier in ("rules", "ml", "slm", "llm"):
        path = ROOT / "sample_requests" / "load_test" / f"{tier}.json"
        payloads[tier] = json.loads(path.read_text(encoding="utf-8"))
    return payloads


def test_load_test_payload_files_exist():
    for tier in ("rules", "ml", "slm", "llm"):
        payload_path = ROOT / "sample_requests" / "load_test" / f"{tier}.json"
        assert payload_path.exists(), payload_path


def test_load_test_payloads_force_inference_mode(load_test_payloads):
    assert load_test_payloads["rules"]["inference_mode"] == "rules"
    assert load_test_payloads["ml"]["inference_mode"] == "ml"
    assert load_test_payloads["slm"]["inference_mode"] == "slm"
    assert load_test_payloads["llm"]["inference_mode"] == "llm"


def test_extract_probe_metrics_from_recommend_response(client, load_test_payloads):
    from scripts.benchmark_metrics import aggregate_probe_metrics, extract_probe_metrics

    response = client.post("/recommend", json=load_test_payloads["rules"])
    assert response.status_code == 200
    body = response.json()
    metrics = extract_probe_metrics(
        body,
        expected_tier="rules",
        expected_candidate_id="vehicle_upgrade_suv",
    )
    assert metrics["tier_match"] is True
    assert metrics["confidence"] is not None
    assert metrics["rules_fired_count"] >= 0

    aggregate = aggregate_probe_metrics([metrics])
    assert aggregate["observed_tier_match_rate"] == 1.0
    assert aggregate["accuracy_proxy"]["training_alignment_top1"] in {0.0, 1.0}


def test_forced_ml_tier_probe(client, load_test_payloads):
    from scripts.benchmark_metrics import extract_probe_metrics

    response = client.post("/recommend", json=load_test_payloads["ml"])
    assert response.status_code == 200
    metrics = extract_probe_metrics(
        response.json(),
        expected_tier="ml",
        expected_candidate_id="vehicle_upgrade_suv",
    )
    assert metrics["observed_tier"] == "ml"
    assert metrics["tier_match"] is True


def test_forced_slm_tier_probe(client, load_test_payloads):
    from scripts.benchmark_metrics import extract_probe_metrics

    response = client.post("/recommend", json=load_test_payloads["slm"])
    assert response.status_code == 200
    metrics = extract_probe_metrics(
        response.json(),
        expected_tier="slm",
        expected_candidate_id="vehicle_upgrade_suv",
    )
    assert metrics["observed_tier"] == "slm"
    assert metrics["tier_match"] is True


def test_build_tier_result_shape():
    from scripts.benchmark_metrics import build_tier_result

    result = build_tier_result(
        tier_name="rules",
        latencies_ms=[10.0, 12.0, 15.0, 20.0],
        errors=0,
        probes=[
            {
                "tier_match": True,
                "fallback": False,
                "confidence": 0.9,
                "alignment_match": True,
                "rules_fired_count": 2,
                "session_cost_units": 0.0,
                "provider_cost_units": 0.0,
            }
        ],
        p95_budget_ms=250.0,
        expected_tier="rules",
        duration_seconds=1.0,
        llm_enabled=False,
        slm_enabled=True,
    )
    assert result["tier"] == "rules"
    assert result["latency_ms"]["p95"] == 15.0
    assert result["throughput_rps"] == 4.0
    assert result["observed_tier_match_rate"] == 1.0
    assert result["accuracy_proxy"]["training_alignment_top1"] == 1.0
    assert result["passed"] is True


def test_load_test_report_renders_markdown():
    from scripts.load_test_report import render_markdown

    markdown = render_markdown(
        [
            {
                "run_id": "2026-07-08T22:00:00Z",
                "environment": "local",
                "base_url": "http://127.0.0.1:8000",
                "workers": 2,
                "requests_per_worker": 2,
                "passed": True,
                "tiers": [
                    {
                        "tier": "rules",
                        "requests": 4,
                        "latency_ms": {"p50": 10.0, "p95": 20.0, "max": 25.0},
                        "p95_budget_ms": 250.0,
                        "throughput_rps": 4.0,
                        "error_rate": 0.0,
                        "fallback_rate": 0.0,
                        "observed_tier_match_rate": 1.0,
                        "avg_confidence": 0.86,
                        "accuracy_proxy": {"training_alignment_top1": 1.0},
                        "explainability": {"rules_fired_avg": 2.0},
                        "passed": True,
                    }
                ],
            }
        ]
    )
    assert "# EDTA Four-Tier Benchmark Report" in markdown
    assert "| rules |" in markdown
    assert "1.00" in markdown
