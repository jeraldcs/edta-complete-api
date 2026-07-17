from fastapi.testclient import TestClient


def test_travel_scenarios_produce_distinct_scoring_signals(client: TestClient):
    scenarios = {
        "winter": (
            "Winter trip to Denver mountains with ski gear, need AWD SUV for snow and icy grades."
        ),
        "family": (
            "Family vacation with three children, need large SUV with isofix and cargo for road trip."
        ),
        "ev": (
            "Eco-conscious buyer wants electric midsize for city commute and charging network access."
        ),
        "first_time": (
            "First-time nervous driver needs beginner-friendly economy compact with easy parking."
        ),
    }

    signatures = {}
    for name, text in scenarios.items():
        response = client.post(
            "/recommend-from-scenario",
            json={"scenario_text": text, "limit": 1, "use_ai_models": True},
        )
        assert response.status_code == 200, response.text
        rec = response.json()["recommendations"][0]
        ai = rec["ai_score"]
        tapl = ai["tapl"]
        outcome = ai["outcome_simulation"]
        signatures[name] = (
            round(ai["semantic_similarity_score"], 3),
            round(outcome["expected_outcome_score"], 3),
            round(tapl["trust_score"], 3),
            round(tapl["fatigue_score"], 3),
            tapl["action"],
            round(ai["ai_rank_score"], 3),
        )

    assert len(set(signatures.values())) >= 3, signatures


def test_consent_false_triggers_tapl_fallback(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": (
                "Customer on web vehicle page comparing SUV rentals at SFO. "
                "Personalization consent false and profile lookup disabled."
            ),
            "limit": 1,
            "use_ai_models": True,
        },
    )
    assert response.status_code == 200
    tapl = response.json()["recommendations"][0]["ai_score"]["tapl"]
    assert tapl["action"] == "generic_fallback"
    assert "consent" in tapl["reason"].lower()


def test_high_fatigue_triggers_tapl_delay(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": (
                "Web visitor fatigued by many ads and repeated exposure to SUV offers. "
                "High fatigue count is 8. Still browsing family SUV rentals."
            ),
            "limit": 1,
            "use_ai_models": True,
        },
    )
    assert response.status_code == 200
    tapl = response.json()["recommendations"][0]["ai_score"]["tapl"]
    assert tapl["action"] == "delay"
    assert tapl["fatigue_score"] >= 0.7
