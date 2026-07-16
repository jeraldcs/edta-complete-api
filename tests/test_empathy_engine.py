from app.empathy.constraint_matcher import ConstraintMatcher
from app.empathy.hidden_needs import HiddenNeedsExtractor, TripExtractor
from app.empathy.service import EmpathyEngine
from app.empathy.tco_calculator import TCOCalculator
from app.enrichment.enrichment_service import EnrichmentService
from app.models import CustomerContext, Channel


FAMILY_SCENARIO = (
    "Traveling with my 80-year-old grandmother and toddler. "
    "Need a rental car for a week-long family trip."
)
PCH_SCENARIO = (
    "Road trip along the Pacific Coast Highway, just me and my partner. "
    "We want something special for the scenic drive."
)
DORM_SCENARIO = (
    "Moving my kid into their college dorm 3 hours away. "
    "Need space for boxes and furniture."
)
DENVER_SCENARIO = (
    "500-mile road trip driving to Denver in winter. Need a safe vehicle for mountain driving."
)


def test_hidden_needs_grandmother_toddler():
    profile = HiddenNeedsExtractor().extract(FAMILY_SCENARIO)
    constraint_ids = {item.constraint_id for item in profile.implicit_constraints}
    assert "elderly_passenger" in profile.persona_tags or "toddler_family" in profile.persona_tags
    assert "low_step_in" in constraint_ids or "isofix_anchors" in constraint_ids
    assert profile.standard_filter_match


def test_empathy_ranking_only_when_signals_present():
    engine = EmpathyEngine()
    profile = engine.hidden_needs.extract(FAMILY_SCENARIO)
    assert engine.should_rank_with_empathy(profile, include_empathy=False) is True
    assert engine.should_rank_with_empathy(profile, include_empathy=True) is True
    generic = engine.hidden_needs.extract("chatbot user asks if SUV rental is available at SFO")
    assert engine.should_rank_with_empathy(generic, include_empathy=False) is False


def test_unified_process_always_exposes_insights():
    engine = EmpathyEngine()
    context = CustomerContext(channel=Channel.web)
    _, bundle = engine.process(
        "chatbot user asks if SUV rental is available at SFO",
        context,
        include_empathy=False,
    )
    assert bundle.insights_available is True
    assert bundle.active is False
    assert bundle.vehicle_recommendation is not None
    assert bundle.vehicle_recommendation.candidate_id == "standard_sedan"


def test_build_vehicle_recommendation_for_family():
    engine = EmpathyEngine()
    context = CustomerContext(channel=Channel.web)
    _, bundle = engine.process(FAMILY_SCENARIO, context, include_empathy=False)
    assert bundle.vehicle_recommendation.candidate_id == "family_friendly_suv"
    assert bundle.vehicle_recommendation.match_score > 0


def test_hidden_needs_pch_couple():
    profile = HiddenNeedsExtractor().extract(PCH_SCENARIO)
    constraint_ids = {item.constraint_id for item in profile.implicit_constraints}
    assert "couple_leisure" in profile.persona_tags
    assert "convertible_option" in constraint_ids or "panoramic_roof" in constraint_ids


def test_hidden_needs_dorm_move():
    profile = HiddenNeedsExtractor().extract(DORM_SCENARIO)
    constraint_ids = {item.constraint_id for item in profile.implicit_constraints}
    assert "college_move" in profile.persona_tags
    assert "cargo_volume" in constraint_ids


def test_enrichment_denver_snow():
    trip = TripExtractor().extract(DENVER_SCENARIO, destination="Denver, CO", route_miles=500)
    enrichment = EnrichmentService().enrich(trip, DENVER_SCENARIO)
    assert enrichment.weather.forecast == "snow"
    assert enrichment.route.steep_grade is True
    assert "awd_preferred" in enrichment.derived_constraints


def test_constraint_matcher_family_suv_wins():
    engine = EmpathyEngine()
    context = CustomerContext(channel=Channel.web)
    updated, bundle = engine.process(FAMILY_SCENARIO, context, include_empathy=True)
    matches = bundle.constraint_matches
    assert matches["family_friendly_suv"].match_score > matches["premium_suv"].match_score


def test_tco_hybrid_saves_on_long_route():
    calculator = TCOCalculator()
    from app.catalog import vehicle_specs_by_id

    specs = vehicle_specs_by_id()
    trip = TripExtractor().extract("", route_miles=500, rental_days=1)
    enrichment = EnrichmentService().enrich(trip, "")
    hybrid = calculator.breakdown(
        "hybrid_midsize",
        specs["hybrid_midsize"],
        trip,
        enrichment.gas_price_usd,
        baseline_spec=specs["economy_compact"],
        baseline_id="economy_compact",
    )
    assert hybrid.net_savings is not None
    assert hybrid.net_savings > 0
    assert "save" in hybrid.recommendation_pitch.lower()


def test_empathy_simulate_endpoint(client):
    response = client.post(
        "/empathy/simulate",
        json={
            "scenario_text": DENVER_SCENARIO,
            "destination": "Denver, CO",
            "route_miles": 500,
            "rental_days": 4,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["empathy"]["active"] is True
    assert data["top_vehicle_id"] in {
        "awd_suv",
        "family_friendly_suv",
        "hybrid_midsize",
        "cargo_suv",
        "premium_suv",
    }


def test_recommend_from_scenario_with_empathy(client):
    response = client.post(
        "/recommend-from-scenario",
        json={
            "scenario_text": FAMILY_SCENARIO,
            "limit": 3,
            "include_empathy": True,
            "use_ai_models": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    summary = data["request_summary"]
    assert summary.get("empathy") is not None
    assert summary["empathy"].get("vehicle_recommendation") is not None
    assert len(data["recommendations"]) >= 1
    top = data["recommendations"][0]
    assert top.get("empathy_match") is not None or top["candidate"]["id"]


def test_empathy_demo_page(client):
    response = client.get("/empathy-demo", follow_redirects=False)
    assert response.status_code == 307
    assert "mode=empathy" in response.headers.get("location", "")

    scenario = client.get("/scenario-demo")
    assert scenario.status_code == 200
    assert "Empathy" in scenario.text
