import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_orchestration_status_endpoint(client):
    response = client.get("/v1/orchestration-status")
    assert response.status_code == 200
    payload = response.json()
    assert "cost_budget" in payload
    assert payload["distilled_tier_name"] == "distilled_pattern"


def test_context_graph_v1_endpoint(client, sample_recommend_payload):
    recommend = client.post("/v1/recommend", json=sample_recommend_payload)
    assert recommend.status_code == 200

    context = sample_recommend_payload["context"]
    response = client.get(
        "/v1/context-graph",
        params={
            "customer_id": context["customer_id"],
            "anonymous_id": context["anonymous_id"],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["subject_id"] == f"customer:{context['customer_id']}"
    assert payload["stored_snapshot"] is not None


def test_compare_outcomes_v1(client, sample_recommend_payload):
    response = client.post(
        "/v1/compare-outcomes",
        json={
            "context": sample_recommend_payload["context"],
            "candidate_id_a": "vehicle_upgrade_suv",
            "candidate_id_b": "early_booking_discount",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["request_summary"]["api_version"] == "v1"
    assert payload["winner_candidate_id"] in {"vehicle_upgrade_suv", "early_booking_discount"}


def test_v1_recommend_returns_typed_summary(client, sample_recommend_payload):
    response = client.post("/v1/recommend", json=sample_recommend_payload)
    assert response.status_code == 200
    payload = response.json()
    assert payload["request_summary"]["api_version"] == "v1"
    assert payload["request_summary"]["request_id"]
    assert payload["request_summary"]["profile"]["adapter"] == "json_file"
    assert "X-Request-ID" in response.headers


def test_v1_batch_recommend_job(client, sample_recommend_payload):
    accepted = client.post(
        "/v1/recommend/batch",
        json={"requests": [sample_recommend_payload, sample_recommend_payload]},
    )
    assert accepted.status_code == 202
    job_id = accepted.json()["job_id"]

    job = client.get(f"/v1/jobs/{job_id}")
    assert job.status_code == 200
    assert job.json()["status"] in {"queued", "running", "completed"}


def test_problem_json_on_invalid_compare(client, sample_recommend_payload):
    response = client.post(
        "/v1/compare-outcomes",
        json={
            "context": sample_recommend_payload["context"],
            "candidate_id_a": "missing_a",
            "candidate_id_b": "missing_b",
        },
    )
    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["status"] == 400
    assert body["request_id"]


def test_webhook_registration(client):
    response = client.post(
        "/v1/webhooks",
        json={
            "target_url": "https://example.com/edta-webhook",
            "event_types": ["recommendation.created"],
        },
    )
    assert response.status_code == 200
    webhook_id = response.json()["id"]

    listed = client.get("/v1/webhooks")
    assert listed.status_code == 200
    assert any(item["id"] == webhook_id for item in listed.json()["webhooks"])


def test_openapi_export_script():
    openapi_path = ROOT / "openapi.json"
    if not openapi_path.exists():
        import subprocess
        import sys

        subprocess.run([sys.executable, "scripts/export_openapi.py"], cwd=ROOT, check=True)

    schema = json.loads(openapi_path.read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.")
    assert "/v1/recommend" in schema["paths"]
    assert "/health" in schema["paths"] or "/" in schema["paths"]
