def test_feedback_persists_to_store(client, sample_recommend_payload, temp_data_dir):
    from app.services import recommendation_handlers

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
            "revenue": 99.0,
        },
    )
    assert response.status_code == 200
    assert response.json()["feedback_count"] == 1

    store = recommendation_handlers.handlers.services.feedback_store
    assert store.count() == 1
    assert temp_data_dir["db_path"].exists()


def test_api_key_required_when_configured(client, sample_recommend_payload, monkeypatch):
    monkeypatch.setenv("EDTA_API_KEY", "secret-test-key")

    import app.config
    import app.main

    app.config.settings = app.config.Settings()

    unauthenticated = client.post("/recommend", json=sample_recommend_payload)
    assert unauthenticated.status_code == 401

    authenticated = client.post(
        "/recommend",
        json=sample_recommend_payload,
        headers={"X-API-Key": "secret-test-key"},
    )
    assert authenticated.status_code == 200
