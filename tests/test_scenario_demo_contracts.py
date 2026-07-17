import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_CSV = ROOT / "data" / "scenario_training_master.csv"


@pytest.fixture
def scenario_rows():
    with SCENARIO_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_all_training_scenarios_return_recommendations(client: TestClient, scenario_rows):
    failures = []
    for index, row in enumerate(scenario_rows):
        response = client.post(
            "/recommend-from-scenario",
            json={
                "scenario_text": row["scenario_text"],
                "limit": 3,
                "use_ai_models": True,
            },
        )
        if response.status_code != 200:
            failures.append((index, row["domain"], response.status_code))
            continue
        data = response.json()
        if not data.get("recommendations"):
            failures.append((index, row["domain"], "empty"))
            continue
        empathy = data.get("request_summary", {}).get("empathy") or {}
        if not empathy.get("vehicle_recommendation"):
            failures.append((index, row["domain"], "missing_empathy_vehicle"))

    assert not failures, f"Scenario recommend failures: {failures[:10]}"


def test_car_rental_chatbot_stays_on_channel_catalog(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": "chatbot user asks if SUV rental is available at SFO",
            "limit": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"], "chatbot car rental should rank chatbot candidates"
    assert data["request_summary"]["empathy"]["active"] is False
    assert data["recommendations"][0]["candidate"]["id"] == "chatbot_booking_assist"
    vehicle = data["request_summary"]["empathy"]["vehicle_recommendation"]
    assert vehicle["candidate_id"] in {
        "economy_compact",
        "standard_sedan",
        "family_friendly_suv",
        "premium_suv",
        "cargo_suv",
        "awd_suv",
        "hybrid_midsize",
        "convertible_premium",
    }
    assert vehicle.get("pitch")


def test_email_scenario_uses_demo_channel_fallback(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": "customer receives loyalty dining offer by email",
            "limit": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"], "email scenarios should fall back to web demo catalog"
    assert data["request_summary"]["nlp"]["demo_channel_fallback"]["from"] == "email"


def test_unified_recommendation_auto_applies_empathy_for_family_scenario(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": "Traveling with my 80-year-old grandmother and toddler.",
            "rental_days": 7,
            "limit": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_summary"]["empathy"]["active"] is True
    assert data["recommendations"][0]["candidate"]["id"] == "family_friendly_suv"
    explanation = data["recommendations"][0]["explanation"].lower()
    assert "grandmother" in explanation or "toddler" in explanation or "isofix" in explanation or "step-in" in explanation


def test_hotel_scenario_includes_empathy_vehicle_recommendation(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": "guest looking for hotel room availability this weekend",
            "limit": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["recommendations"][0]["candidate"]["id"] in {
        "hotel_reservation_assist",
        "hotel_room_offer",
    }
    vehicle = data["request_summary"]["empathy"]["vehicle_recommendation"]
    assert vehicle["candidate_id"] == "economy_compact"
    assert data["request_summary"]["empathy"]["insights_available"] is True


def test_scenario_demo_page_has_unified_empathy_controls(client: TestClient):
    response = client.get("/scenario-demo")
    assert response.status_code == 200
    assert "scenario_app.js" in response.text
    assert 'data-mode="empathy"' not in response.text
    assert "Trained travel scenarios" not in response.text
    assert "empathy-preset" not in response.text
    assert 'id="empathyDestination"' not in response.text
    assert "scenario-mode-tab" not in response.text
    assert 'id="scenarioRunBtn"' in response.text
    assert 'id="scenarioForm"' in response.text
    assert "__EDTA_DEMO_CONFIG__" in response.text
    assert "scenario_app.js?v=" in response.text
    assert 'id="scenarioRunError"' in response.text
    assert 'id="scenarioStatus"' not in response.text
    assert "Experience memory" not in response.text
