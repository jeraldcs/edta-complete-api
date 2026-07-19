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


def test_desert_summer_scenario_activates_empathy_and_prefers_efficient_vehicle(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": (
                "I am planning a 900-mile road trip through Arizona and Nevada during summer "
                "where temperatures may exceed 110°F. Reliability, cooling performance, fuel "
                "efficiency, and cabin comfort are important."
            ),
            "limit": 3,
            "use_ai_models": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    summary = data["request_summary"]
    empathy = summary["empathy"]
    assert empathy["active"] is True
    assert empathy["enrichment"]["weather"]["forecast"] == "extreme_heat"
    assert empathy["trip"]["distance_miles"] == 900
    constraint_ids = {
        item["constraint_id"]
        for item in (empathy.get("hidden_needs") or {}).get("implicit_constraints") or []
    }
    derived = set((empathy.get("enrichment") or {}).get("derived_constraints") or [])
    assert "fuel_efficiency" in constraint_ids.union(derived)
    assert "cabin_comfort" in constraint_ids.union(derived)
    top_id = data["recommendations"][0]["candidate"]["id"]
    assert top_id in {"hybrid_midsize", "electric_midsize"}
    vehicle = empathy.get("vehicle_recommendation") or {}
    assert vehicle.get("candidate_id") in {"hybrid_midsize", "electric_midsize"}
    assert float(vehicle.get("match_score") or 0) > 0


def test_trip_extractor_parses_plural_miles():
    from app.empathy.hidden_needs import TripExtractor

    trip = TripExtractor().extract(
        "I need to drive 300 miles during an active snowstorm with icy roads."
    )
    assert trip.distance_miles == 300


def test_snowstorm_drive_scenario_recommends_vehicle_not_hotel(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": (
                "I need to drive 300 miles during an active snowstorm with heavy snowfall, "
                "poor visibility, icy roads, and strong winds. Safety, traction, and stability "
                "are my highest priorities."
            ),
            "limit": 3,
            "use_ai_models": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    summary = data["request_summary"]
    assert summary["nlp"]["detected_domain"] == "travel"
    top_id = data["recommendations"][0]["candidate"]["id"]
    assert not top_id.startswith("hotel_"), top_id
    assert top_id in {
        "awd_suv",
        "premium_suv",
        "family_friendly_suv",
        "cargo_suv",
        "large_family_suv",
        "standard_sedan",
        "hybrid_midsize",
    }
    vehicle = (summary.get("empathy") or {}).get("vehicle_recommendation") or {}
    assert vehicle.get("candidate_id") in {"awd_suv", "premium_suv"}


def test_recommend_from_scenario_exposes_slm_status(client: TestClient):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": (
                "Hosted SLM demo — I need something comfortable for a trip next week, "
                "not sure which car. Maybe family-friendly? Budget is flexible but I care about safety."
            ),
            "limit": 3,
            "inference_mode": "rules",
            "use_llm_explanation": False,
        },
    )
    assert response.status_code == 200
    summary = response.json()["request_summary"]
    assert summary["inference_mode"] == "rules"
    assert "llm_status" in summary
    assert "slm_engine" in summary["llm_status"]
    assert "provider_telemetry" in summary
    assert summary["inference"]["tier"] == "rules"


def test_scenario_app_has_hosted_slm_demo_flow():
    app_js = (ROOT / "static" / "scenario_app.js").read_text(encoding="utf-8")
    assert 'hosted_slm:' in app_js
    assert 'rules_vs_slm:' in app_js
    assert "compare_rules_vs_slm" in app_js
    assert "Hosted SLM telemetry" in app_js
    assert 'inference_mode: "slm"' in app_js
    assert "use_llm_explanation: true" in app_js


def test_scenario_demo_page_has_unified_empathy_controls(client: TestClient):
    response = client.get("/scenario-demo")
    assert response.status_code == 200
    assert "scenario_app.js" in response.text
    assert 'id="scenarioChipRowTravel"' in response.text
    assert 'id="scenarioChipRowGovernance"' in response.text
    assert 'id="scenarioChipRowSlm"' in response.text
    assert 'id="scenarioChipRowCompare"' in response.text
    assert "scenario-sampler" in response.text
    assert "Try scenario" in response.text
    assert "Try governance" in response.text
    assert "Try hosted SLM" in response.text
    assert "Compare vs traditional" in response.text
    assert 'data-scenario-key="hosted_slm"' in response.text
    assert 'data-scenario-key="rules_vs_slm"' in response.text
    assert 'data-scenario-key="compare_rules"' in response.text
    assert 'data-scenario-key="compare_edta"' in response.text
    assert "scenario-start-here" in response.text
    assert 'id="demoWakeBanner"' in response.text
    assert 'id="tryNextSuggestions"' in response.text
    assert 'id="copyDemoLinkBtn"' in response.text
    assert "demo-details-section" in response.text
    assert "scenario-chip-btn" in response.text
    assert 'data-mode="empathy"' not in response.text
    assert 'id="travelBenchmarkTable"' in response.text
    assert "empathy-preset" not in response.text
    assert 'id="empathyDestination"' not in response.text
    assert "scenario-mode-tab" not in response.text
    assert 'id="scenarioForm"' in response.text
    assert 'id="scenarioRunBtn"' in response.text
    assert "__EDTA_DEMO_CONFIG__" in response.text
    assert "scenario_app.js?v=" in response.text
    assert 'id="scenarioRunError"' in response.text
    assert 'id="scenarioColdStart"' in response.text
    assert "demo-accordion" in response.text
    assert 'id="benchmarkToggleMetrics"' in response.text
    assert "scenario-demo-footer" in response.text
    assert 'id="scenarioOfferCard"' in response.text
    assert "EDTA_PUBLICATION_DOCUMENT" in response.text
    assert 'id="scenarioStatus"' not in response.text
    assert "Experience memory" not in response.text
    assert "Describe a trip" in response.text
