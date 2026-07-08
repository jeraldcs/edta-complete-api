def test_health_reports_ready(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["checks"]["models"]["ready"] is True
    assert payload["checks"]["profile_lookup"]["exists"] is True
    assert payload["checks"]["sqlite"]["writable"] is True
    assert payload["checks"]["tapl_policy"]["exists"] is True


def test_health_alias(client):
    root = client.get("/").json()
    health = client.get("/health").json()
    assert root["ready"] == health["ready"]
    assert root["status"] == health["status"]
