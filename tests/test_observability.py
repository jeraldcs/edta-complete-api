import json
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient


def test_live_probe(client: TestClient):
    response = client.get("/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "alive"


def test_ready_probe_ok(client: TestClient):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_ready_probe_returns_503_when_not_ready(client, monkeypatch):
    import app.main

    original = app.main._health_response

    def degraded_health():
        payload = original()
        payload["ready"] = False
        payload["status"] = "degraded"
        return payload

    monkeypatch.setattr(app.main, "_health_response", degraded_health)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["ready"] is False


def test_metrics_endpoint_exposes_prometheus(client: TestClient):
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "edta_http_requests_total" in body


def test_security_headers_present(client: TestClient):
    response = client.get("/live")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "X-Request-ID" in response.headers


def test_access_log_and_metrics_increment(client: TestClient, sample_recommend_payload):
    client.get("/health")
    metrics = client.get("/metrics").text
    assert "edta_http_requests_total" in metrics

    recommend = client.post("/recommend", json=sample_recommend_payload)
    assert recommend.status_code == 200
    metrics = client.get("/metrics").text
    assert "edta_recommendations_total" in metrics


def test_feedback_records_metric(client: TestClient, sample_recommend_payload):
    recommend = client.post("/recommend", json=sample_recommend_payload)
    top_id = recommend.json()["recommendations"][0]["candidate"]["id"]
    response = client.post(
        "/feedback",
        json={
            "anonymous_id": sample_recommend_payload["context"]["anonymous_id"],
            "recommendation_id": top_id,
            "channel": sample_recommend_payload["context"]["channel"],
            "event_type": "click",
            "converted": True,
            "revenue": 42.0,
        },
    )
    assert response.status_code == 200
    metrics = client.get("/metrics").text
    assert 'edta_feedback_events_total{converted="true",event_type="click"}' in metrics


def test_production_hides_internal_error_details(monkeypatch):
    monkeypatch.setenv("EDTA_ENVIRONMENT", "production")
    monkeypatch.setenv("EDTA_EXPOSE_ERROR_DETAILS", "auto")
    import app.config

    app.config.settings = app.config.Settings()
    assert app.config.settings.expose_error_details is False


def test_concurrent_recommend_requests(client: TestClient, sample_recommend_payload):
    def call_recommend():
        response = client.post("/recommend", json=sample_recommend_payload)
        return response.status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(lambda _: call_recommend(), range(12)))

    assert all(status == 200 for status in statuses)


def test_recommend_burst(client: TestClient, sample_recommend_payload):
    payload = json.loads(json.dumps(sample_recommend_payload))
    statuses = [client.post("/recommend", json=payload).status_code for _ in range(5)]
    assert all(status == 200 for status in statuses)
