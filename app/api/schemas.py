from typing import Any, Optional, List, Dict

from pydantic import BaseModel, Field

from app.models import (
    Channel,
    IntentType,
    JourneyStage,
    ExperienceMemorySnapshot,
    TemporalKnowledgeGraphSummary,
    RankedRecommendation,
)


class ProfileLookupSummary(BaseModel):
    profile_lookup: str
    reason: str
    customer_id: Optional[str] = None
    fields_merged: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    adapter: Optional[str] = None


class MemoryDeltaSummary(BaseModel):
    before: ExperienceMemorySnapshot
    after: ExperienceMemorySnapshot


class TrainingAlignmentSummary(BaseModel):
    matched: bool
    expected_candidate_id: Optional[str] = None
    purpose: Optional[str] = None


class CandidatePreselectionSummary(BaseModel):
    enabled: bool
    candidate_count: int


class RequestSummary(BaseModel):
    request_id: str
    api_version: str = "v1"
    channel: Optional[Channel] = None
    journey_stage_input: Optional[JourneyStage] = None
    intent_input: Optional[IntentType] = None
    customer_id: Optional[str] = None
    profile: Optional[ProfileLookupSummary] = None
    experience_memory: Optional[Any] = None
    use_ai_models: Optional[bool] = None
    use_llm: Optional[bool] = None
    use_slm: Optional[bool] = None
    use_llm_explanation: Optional[bool] = None
    inference_mode: Optional[str] = None
    inference: Optional[Dict[str, Any]] = None
    ml_inference: Optional[Dict[str, Any]] = None
    provider_telemetry: Optional[Dict[str, Any]] = None
    explanation_routing: Optional[Dict[str, Any]] = None
    llm_enabled: Optional[bool] = None
    llm_status: Optional[Dict[str, Any]] = None
    self_distillation: Optional[Dict[str, Any]] = None
    haoe: Optional[Dict[str, Any]] = None
    ose_calibration: Optional[Dict[str, float]] = None
    context_graph: Optional[Dict[str, Any]] = None
    scenario_text: Optional[str] = None
    nlp: Optional[Dict[str, Any]] = None
    parsed_context: Optional[Dict[str, Any]] = None
    training_alignment: Optional[TrainingAlignmentSummary] = None
    candidate_preselection: Optional[CandidatePreselectionSummary] = None
    empathy: Optional[Dict[str, Any]] = None
    enrichment: Optional[Dict[str, Any]] = None
    tco: Optional[Dict[str, Any]] = None
    simulation: Optional[str] = None
    comparison: Optional[str] = None
    winner_candidate_id: Optional[str] = None


class RecommendationResponseV1(BaseModel):
    request_summary: RequestSummary
    recommendations: List[RankedRecommendation]


class CompareRequestSummary(BaseModel):
    request_id: str
    api_version: str = "v1"
    comparison: str
    channel: Channel
    customer_id: Optional[str] = None
    profile: Optional[ProfileLookupSummary] = None
    experience_memory: ExperienceMemorySnapshot
    ose_calibration: Dict[str, float]
    context_graph: Dict[str, Any]
    winner_candidate_id: str


class CompareOutcomesResponseV1(BaseModel):
    request_summary: CompareRequestSummary
    candidate_a: RankedRecommendation
    candidate_b: RankedRecommendation
    winner_candidate_id: str
