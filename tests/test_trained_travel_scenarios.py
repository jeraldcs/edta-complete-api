import pytest

from app.empathy.scenario_profiles import ScenarioProfileMatcher
from app.empathy.service import EmpathyEngine
from app.empathy.trained_scenarios import TRAINED_SCENARIOS
from app.models import CustomerContext, Channel


@pytest.mark.parametrize("scenario_key", list(TRAINED_SCENARIOS.keys()))
def test_scenario_profile_matcher(scenario_key):
    scenario = TRAINED_SCENARIOS[scenario_key]
    matcher = ScenarioProfileMatcher()
    matched = matcher.match(scenario["text"])
    assert matched is not None, f"No profile matched for {scenario_key}"
    profile_id, _config = matched
    assert profile_id == scenario_key
    assert matcher.preferred_vehicle(scenario["text"]) == scenario["expected_vehicle"]


@pytest.mark.parametrize("scenario_key", list(TRAINED_SCENARIOS.keys()))
def test_empathy_vehicle_recommendation(scenario_key):
    scenario = TRAINED_SCENARIOS[scenario_key]
    matcher = ScenarioProfileMatcher()
    matched = matcher.match(scenario["text"])
    assert matched is not None
    _profile_id, config = matched
    expected_miles = scenario.get("expected_miles") or config.get("default_miles")

    engine = EmpathyEngine()
    context = CustomerContext(channel=Channel.web)
    updated_context, bundle = engine.process(
        scenario["text"],
        context,
        include_empathy=True,
    )
    assert bundle.vehicle_recommendation.candidate_id == scenario["expected_vehicle"]
    if expected_miles:
        assert bundle.trip.distance_miles == pytest.approx(expected_miles, rel=0.05)
    profile_meta = updated_context.business_context.get("scenario_profile") or {}
    assert profile_meta.get("profile_id") == scenario_key


def test_travel_scenario_isolates_architecture_subjects(client):
    denver = TRAINED_SCENARIOS["winter_mountain_denver"]["text"]
    family = TRAINED_SCENARIOS["long_family_vacation"]["text"]

    denver_response = client.post(
        "/recommend-from-scenario",
        json={"scenario_text": denver, "limit": 1, "use_ai_models": True, "use_llm": False},
    )
    family_response = client.post(
        "/recommend-from-scenario",
        json={"scenario_text": family, "limit": 1, "use_ai_models": True, "use_llm": False},
    )
    assert denver_response.status_code == 200
    assert family_response.status_code == 200

    denver_summary = denver_response.json()["request_summary"]
    family_summary = family_response.json()["request_summary"]

    assert denver_summary["nlp"]["scenario_subject_id"] == "anonymous:travel-winter_mountain_denver"
    assert family_summary["nlp"]["scenario_subject_id"] == "anonymous:travel-long_family_vacation"
    assert denver_summary["scenario_profile"]["profile_id"] == "winter_mountain_denver"
    assert family_summary["scenario_profile"]["profile_id"] == "long_family_vacation"

    denver_graph = denver_summary["context_graph"]
    family_graph = family_summary["context_graph"]
    assert denver_graph["scenario_profile_id"] == "winter_mountain_denver"
    assert family_graph["scenario_profile_id"] == "long_family_vacation"
    assert denver_graph["live_journey_sequence"]
    assert family_graph["live_journey_sequence"]
    assert "denver" in " ".join(denver_graph["live_journey_sequence"]).lower()
    assert "recommendation:" in denver_graph["live_journey_sequence"][-1]

    assert denver_summary["inference"]["domain"] == "travel"
    assert denver_summary["experience_memory"]["before"]["subject_id"] == "anonymous:travel-winter_mountain_denver"


def test_travel_scenario_benchmark_endpoint(client):
    response = client.get("/travel-scenario-benchmark")
    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_count"] == len(TRAINED_SCENARIOS)
    assert payload["vehicle_match_count"] == len(TRAINED_SCENARIOS)
    assert len(payload["scenarios"]) == len(TRAINED_SCENARIOS)
    for row in payload["scenarios"]:
        assert row["vehicle_match"] is True
        assert row["eds_score"] is not None
        assert row["expected_outcome"] is not None
