def test_recommend_returns_ranked_results(client, sample_recommend_payload):
    response = client.post("/recommend", json=sample_recommend_payload)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["recommendations"]) >= 1
    top = payload["recommendations"][0]
    assert top["candidate"]["id"]
    assert top["ai_score"]["final_hybrid_score"] > 0
    assert "context_graph" in payload["request_summary"]


def test_recommend_respects_channel_filter(client, sample_recommend_payload):
    response = client.post("/recommend", json=sample_recommend_payload)
    payload = response.json()
    for item in payload["recommendations"]:
        assert item["candidate"]["channel"] == sample_recommend_payload["context"]["channel"]


def test_simulate_returns_candidates(client, sample_recommend_payload):
    response = client.post(
        "/simulate",
        json={"context": sample_recommend_payload["context"]},
    )
    assert response.status_code == 200
    assert len(response.json()["recommendations"]) >= 1
