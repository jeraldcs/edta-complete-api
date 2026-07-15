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
        if not response.json().get("recommendations"):
            failures.append((index, row["domain"], "empty"))

    assert not failures, f"Scenario recommend failures: {failures[:10]}"


def test_car_rental_without_empathy_uses_channel_catalog(client: TestClient):
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
    assert data["request_summary"].get("empathy") is None
    assert data["recommendations"][0]["candidate"]["id"] == "chatbot_booking_assist"


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


def test_empathy_mode_returns_vehicle_for_family_preset(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": "Traveling with my 80-year-old grandmother and toddler.",
            "include_empathy": True,
            "rental_days": 7,
            "limit": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_summary"]["empathy"]["active"] is True
    assert data["recommendations"][0]["candidate"]["id"] == "family_friendly_suv"


def test_scenario_demo_page_has_empathy_tab(client: TestClient):
    response = client.get("/scenario-demo")
    assert response.status_code == 200
    assert "Empathy Engine" in response.text
    assert "scenario_app.js" in response.text
