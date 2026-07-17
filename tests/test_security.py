import pytest


def test_protected_read_endpoints_require_api_key(client, sample_recommend_payload, monkeypatch):
    monkeypatch.setenv("EDTA_API_KEY", "read-secret")
    monkeypatch.setenv("EDTA_ENVIRONMENT", "development")

    import app.config

    app.config.settings = app.config.Settings()

    context = sample_recommend_payload["context"]
    protected_paths = [
        ("/v1/context-graph", {"customer_id": context["customer_id"]}),
        ("/v1/experience-memory", {"anonymous_id": context["anonymous_id"]}),
        ("/v1/orchestration-status", None),
        ("/v1/self-distillation", None),
    ]
    for path, params in protected_paths:
        response = client.get(path, params=params or {})
        assert response.status_code == 401, path

    authed = client.get(
        "/v1/context-graph",
        params={"customer_id": context["customer_id"]},
        headers={"X-API-Key": "read-secret"},
    )
    assert authed.status_code == 200


def test_webhook_rejects_private_target(client, monkeypatch):
    monkeypatch.setenv("EDTA_API_KEY", "hook-secret")
    import app.config

    app.config.settings = app.config.Settings()

    response = client.post(
        "/v1/webhooks",
        json={
            "target_url": "https://127.0.0.1/hook",
            "event_types": ["recommendation.created"],
        },
        headers={"X-API-Key": "hook-secret"},
    )
    assert response.status_code == 400
    assert "private" in response.json()["detail"].lower()


def test_webhook_rejects_http_scheme(client, monkeypatch):
    monkeypatch.setenv("EDTA_API_KEY", "hook-secret")
    import app.config

    app.config.settings = app.config.Settings()

    response = client.post(
        "/v1/webhooks",
        json={
            "target_url": "http://example.com/hook",
            "event_types": ["recommendation.created"],
        },
        headers={"X-API-Key": "hook-secret"},
    )
    assert response.status_code == 400


def test_rate_limit_returns_429(monkeypatch):
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.testclient import TestClient

    from app.middleware.http import RateLimitMiddleware

    app = Starlette()

    async def homepage(_request):
        return PlainTextResponse("ok")

    app.add_route("/", homepage, methods=["GET"])
    app.add_middleware(RateLimitMiddleware, limit_per_minute=2)
    client = TestClient(app)

    statuses = [client.get("/").status_code for _ in range(4)]
    assert statuses.count(429) >= 1


def test_idempotency_key_replays_recommend_response(client, sample_recommend_payload, monkeypatch):
    monkeypatch.setenv("EDTA_API_KEY", "idem-secret")
    import app.config

    app.config.settings = app.config.Settings()
    headers = {"X-API-Key": "idem-secret", "Idempotency-Key": "recommend-abc"}

    first = client.post("/v1/recommend", json=sample_recommend_payload, headers=headers)
    second = client.post("/v1/recommend", json=sample_recommend_payload, headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["request_summary"]["request_id"] == second.json()["request_summary"]["request_id"]


def test_demo_proxy_available_when_key_hidden(client, monkeypatch):
    monkeypatch.setenv("EDTA_API_KEY", "demo-secret")
    monkeypatch.setenv("EDTA_EXPOSE_DEMO_API_KEY", "false")
    monkeypatch.setenv("EDTA_ENVIRONMENT", "development")

    import app.config

    app.config.settings = app.config.Settings()
    config = client.get("/demo-config").json()
    assert config["demo_proxy_enabled"] is True
    assert config["api_key"] is None

    response = client.post(
        "/demo-api/recommend-from-scenario",
        json={
            "scenario_text": "Family of four needs an SUV for Orlando theme park vacation with luggage.",
            "limit": 1,
        },
    )
    assert response.status_code == 200
    assert response.json()["recommendations"]


def test_production_startup_requires_api_key(monkeypatch):
    monkeypatch.setenv("EDTA_ENVIRONMENT", "production")
    monkeypatch.delenv("EDTA_API_KEY", raising=False)

    import app.config

    settings = app.config.Settings()
    with pytest.raises(RuntimeError, match="EDTA_API_KEY"):
        settings.validate_for_startup()
