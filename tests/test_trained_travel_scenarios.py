import pytest

from app.empathy.scenario_profiles import ScenarioProfileMatcher
from app.empathy.service import EmpathyEngine
from app.models import CustomerContext, Channel


TRAINED_SCENARIOS = {
    "winter_mountain_denver": {
        "text": (
            "I am planning a 500-mile one-way road trip to Denver, Colorado during the winter season. "
            "The journey may include interstate highways, mountain roads, steep inclines and declines, "
            "snow-covered roads, icy pavement, and rapidly changing weather conditions. "
            "I will be traveling with my spouse and luggage. My highest priorities are passenger safety, "
            "winter traction, braking performance, driver confidence, and reliability. "
            "Please recommend the most suitable vehicle for this trip and explain why."
        ),
        "vehicle": "awd_suv",
        "miles": 500,
        "profile_id": "winter_mountain_denver",
    },
    "long_family_vacation": {
        "text": (
            "I am planning a 1,200-mile family vacation from New Jersey to Orlando, Florida during the summer. "
            "We are a family of five with three children, multiple suitcases, a stroller, and sports equipment. "
            "Most driving will be on interstate highways with occasional city traffic. "
            "Comfort, cargo capacity, fuel efficiency, reliability, and advanced driver assistance features "
            "are my highest priorities. Please recommend the best vehicle for this trip."
        ),
        "vehicle": "large_family_suv",
        "miles": 1200,
        "profile_id": "long_family_vacation",
    },
    "business_executive": {
        "text": (
            "I travel frequently for business, averaging 35,000 highway miles annually. "
            "Most trips involve airport transfers, interstate driving, and meetings with clients. "
            "I want a premium vehicle that provides excellent comfort, advanced technology, outstanding safety, "
            "a quiet cabin, and strong fuel efficiency while maintaining a professional appearance. "
            "Recommend the most suitable vehicle."
        ),
        "vehicle": "luxury_sedan",
        "miles": 35000,
        "profile_id": "business_executive",
    },
    "national_park_adventure": {
        "text": (
            "I am planning a 10-day road trip covering Yellowstone, Grand Teton, Glacier National Park, "
            "and Rocky Mountain National Park. The trip includes paved highways, gravel roads, mountain passes, "
            "wildlife areas, and occasional rough terrain. I need a vehicle that offers good ground clearance, "
            "AWD capability, cargo space for camping equipment, reliability, and excellent safety. "
            "Recommend the best vehicle for this adventure."
        ),
        "vehicle": "awd_suv",
        "miles": 1800,
        "profile_id": "national_park_adventure",
    },
    "urban_commuter": {
        "text": (
            "I drive approximately 18,000 miles per year, primarily commuting through heavy urban traffic "
            "with occasional weekend highway trips. Fuel economy, reliability, parking convenience, "
            "low maintenance costs, and advanced safety features are my highest priorities. "
            "I also prefer modern infotainment and driver assistance technologies. "
            "Recommend the most suitable vehicle."
        ),
        "vehicle": "hybrid_midsize",
        "miles": 18000,
        "profile_id": "urban_commuter",
    },
    "electric_vehicle": {
        "text": (
            "I am considering purchasing my first electric vehicle. I drive approximately 50 miles per day, "
            "have access to home charging, and occasionally take 300-mile weekend trips. "
            "My priorities include long driving range, fast charging capability, battery reliability, safety, "
            "low maintenance, advanced technology, and overall ownership cost. "
            "Recommend the most suitable electric vehicle."
        ),
        "vehicle": "electric_midsize",
        "miles": 300,
        "profile_id": "electric_vehicle",
    },
    "luxury_winter_suv": {
        "text": (
            "I live in Colorado and frequently drive through mountainous regions during winter. "
            "My budget allows me to purchase a luxury SUV. I value exceptional safety, AWD performance, "
            "premium comfort, advanced driver assistance systems, heated features, and long-distance driving comfort. "
            "Winter capability is more important than fuel economy. Recommend the ideal luxury SUV."
        ),
        "vehicle": "premium_suv",
        "miles": 400,
        "profile_id": "luxury_winter_suv",
    },
    "first_time_driver": {
        "text": (
            "I recently received my driver's license and will primarily drive within suburban neighborhoods "
            "and nearby highways. I have limited driving experience and want a vehicle that is easy to drive, "
            "highly reliable, affordable to maintain, fuel-efficient, and equipped with comprehensive safety "
            "technologies. Please recommend the best vehicle for a new driver."
        ),
        "vehicle": "economy_compact",
        "miles": 120,
        "profile_id": "first_time_driver",
    },
    "rental_seattle_vacation": {
        "text": (
            "I am flying to Seattle and renting a vehicle for a 7-day vacation. My itinerary includes city driving, "
            "scenic coastal highways, Mount Rainier, Olympic National Park, and occasional mountain roads. "
            "Rental cost is important, but safety, reliability, fuel efficiency, cargo space, and driving comfort "
            "are more important. Recommend the best rental vehicle category and specific models if available."
        ),
        "vehicle": "awd_suv",
        "miles": 650,
        "profile_id": "rental_seattle_vacation",
    },
    "wet_weather_hurricane": {
        "text": (
            "I am planning a 700-mile road trip across the southeastern United States during hurricane season. "
            "The journey may involve heavy rain, flooded roads, strong crosswinds, poor visibility, and long highway drives. "
            "I prioritize hydroplaning resistance, braking performance, stability control, driver assistance technologies, "
            "visibility, and overall safety. Recommend the most suitable vehicle for these conditions."
        ),
        "vehicle": "awd_suv",
        "miles": 700,
        "profile_id": "wet_weather_hurricane",
    },
}


@pytest.mark.parametrize("scenario_key", list(TRAINED_SCENARIOS.keys()))
def test_scenario_profile_matcher(scenario_key):
    scenario = TRAINED_SCENARIOS[scenario_key]
    matcher = ScenarioProfileMatcher()
    matched = matcher.match(scenario["text"])
    assert matched is not None, f"No profile matched for {scenario_key}"
    profile_id, _config = matched
    assert profile_id == scenario["profile_id"]
    assert matcher.preferred_vehicle(scenario["text"]) == scenario["vehicle"]


@pytest.mark.parametrize("scenario_key", list(TRAINED_SCENARIOS.keys()))
def test_empathy_vehicle_recommendation(scenario_key):
    scenario = TRAINED_SCENARIOS[scenario_key]
    engine = EmpathyEngine()
    context = CustomerContext(channel=Channel.web)
    updated_context, bundle = engine.process(
        scenario["text"],
        context,
        include_empathy=True,
    )
    assert bundle.vehicle_recommendation.candidate_id == scenario["vehicle"]
    assert bundle.trip.distance_miles == pytest.approx(scenario["miles"], rel=0.05)
    profile_meta = updated_context.business_context.get("scenario_profile") or {}
    assert profile_meta.get("profile_id") == scenario["profile_id"]
