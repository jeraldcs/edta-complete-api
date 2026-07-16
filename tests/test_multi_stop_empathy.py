from app.empathy.hidden_needs import HiddenNeedsExtractor, TripExtractor
from app.empathy.route_planner import RoutePlanner
from app.empathy.service import EmpathyEngine
from app.models import CustomerContext, Channel

SIERRA_FAMILY_SCENARIO = (
    "I am planning for a road trip from San Francisco to yosemite, then from there I will be "
    "traveling to lake tahoe, then from there 1 day in Napa Valley, and then i will be traveling "
    "back to SfO airport. i will be traveling with my wife and year-old daughter "
)


def test_route_planner_sf_yosemite_tahoe_napa():
    planner = RoutePlanner()
    profile = planner.route_profile(SIERRA_FAMILY_SCENARIO)
    assert profile is not None
    assert profile["distance_miles"] == 525
    assert "Yosemite" in profile["stops"][1]
    assert profile["steep_grade"] is True


def test_trip_extractor_multi_stop_miles():
    trip = TripExtractor().extract(SIERRA_FAMILY_SCENARIO, rental_days=5)
    assert trip.distance_miles == 525
    assert len(trip.stops) == 5
    assert trip.route_label
    assert trip.rental_days >= 5


def test_hidden_needs_year_old_daughter():
    profile = HiddenNeedsExtractor().extract(SIERRA_FAMILY_SCENARIO)
    assert "toddler_family" in profile.persona_tags
    assert "mountain_travel" in profile.persona_tags
    constraint_ids = {item.constraint_id for item in profile.implicit_constraints}
    assert "isofix_anchors" in constraint_ids
    assert "awd_preferred" in constraint_ids


def test_sierra_family_scenario_recommendation(client):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": SIERRA_FAMILY_SCENARIO,
            "limit": 3,
            "rental_days": 5,
        },
    )
    assert response.status_code == 200
    data = response.json()
    empathy = data["request_summary"]["empathy"]
    assert empathy["trip"]["distance_miles"] == 525
    assert len(empathy["trip"]["stops"]) == 5
    assert "toddler_family" in empathy["hidden_needs"]["persona_tags"]
    vehicle = empathy["vehicle_recommendation"]
    assert vehicle["candidate_id"] == "family_friendly_suv"
    assert vehicle.get("tco") is not None
    assert vehicle["tco"]["total_trip_cost"] > 0
    assert len(empathy.get("tco_comparisons") or []) >= 1
    explanation = data["recommendations"][0]["explanation"].lower()
    assert any(token in explanation for token in ("isofix", "rear legroom", "child", "toddler", "daughter"))
