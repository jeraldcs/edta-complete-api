from typing import Any

from pydantic import BaseModel, Field


class ImplicitConstraint(BaseModel):
    constraint_id: str
    weight: float = 0.1
    reason: str = ""
    source: str = "rules"


class HiddenNeedsProfile(BaseModel):
    persona_tags: list[str] = Field(default_factory=list)
    implicit_constraints: list[ImplicitConstraint] = Field(default_factory=list)
    confidence: float = 0.0
    evidence_phrases: list[str] = Field(default_factory=list)
    standard_filter_match: str = ""


class TripModel(BaseModel):
    destination: str | None = None
    origin: str | None = None
    distance_miles: float | None = None
    rental_days: int = 3
    route_hint: str | None = None
    route_label: str | None = None
    stops: list[str] = Field(default_factory=list)


class WeatherSnapshot(BaseModel):
    forecast: str = "clear"
    wind_mph: float = 0.0
    source: str = "stub"
    note: str = ""


class RouteProfile(BaseModel):
    max_elevation_ft: float = 0.0
    steep_grade: bool = False
    distance_miles: float | None = None
    source: str = "stub"


class EnrichmentBundle(BaseModel):
    weather: WeatherSnapshot | None = None
    route: RouteProfile | None = None
    derived_constraints: list[str] = Field(default_factory=list)
    gas_price_usd: float = 3.85
    source_mode: str = "stub"


class TCOBreakdown(BaseModel):
    candidate_id: str
    daily_rate_total: float
    estimated_fuel_cost: float
    total_trip_cost: float
    vs_baseline_candidate_id: str | None = None
    net_savings: float | None = None
    recommendation_pitch: str = ""


class ConstraintMatch(BaseModel):
    candidate_id: str
    match_score: float
    satisfied: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class EmpathyVehicleRecommendation(BaseModel):
    candidate_id: str
    title: str
    description: str = ""
    match_score: float = 0.0
    satisfied: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    pitch: str = ""
    tco: TCOBreakdown | None = None


class EmpathyBundle(BaseModel):
    hidden_needs: HiddenNeedsProfile
    trip: TripModel
    enrichment: EnrichmentBundle
    constraint_matches: dict[str, ConstraintMatch] = Field(default_factory=dict)
    tco_comparisons: list[TCOBreakdown] = Field(default_factory=list)
    empathy_pitch: str = ""
    vehicle_recommendation: EmpathyVehicleRecommendation | None = None
    active: bool = False
    insights_available: bool = False

    def model_dump_public(self) -> dict[str, Any]:
        payload = {
            "active": self.active,
            "insights_available": self.insights_available,
            "hidden_needs": self.hidden_needs.model_dump(),
            "trip": self.trip.model_dump(),
            "enrichment": self.enrichment.model_dump(),
            "constraint_matches": {
                key: value.model_dump() for key, value in self.constraint_matches.items()
            },
            "tco_comparisons": [item.model_dump() for item in self.tco_comparisons],
            "empathy_pitch": self.empathy_pitch,
        }
        if self.vehicle_recommendation:
            payload["vehicle_recommendation"] = self.vehicle_recommendation.model_dump()
        return payload
