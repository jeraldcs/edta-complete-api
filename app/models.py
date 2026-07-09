from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class JourneyStage(str, Enum):
    awareness = "awareness"
    research = "research"
    consideration = "consideration"
    purchase = "purchase"
    service = "service"
    retention = "retention"


class IntentType(str, Enum):
    research = "research"
    purchase = "purchase"
    support = "support"
    retention = "retention"
    upgrade = "upgrade"
    unknown = "unknown"


class Channel(str, Enum):
    web = "web"
    mobile = "mobile"
    email = "email"
    sms = "sms"
    push = "push"
    in_app = "in_app"
    call_center = "call_center"
    chatbot = "chatbot"
    voice_assistant = "voice_assistant"
    iot = "iot"
    wearable = "wearable"
    connected_car = "connected_car"
    kiosk = "kiosk"
    smart_tv = "smart_tv"
    ar_vr = "ar_vr"
    social = "social"
    marketplace = "marketplace"
    partner_api = "partner_api"


class TAPLAction(str, Enum):
    show = "show"
    soften = "soften"
    delay = "delay"
    suppress = "suppress"
    generic_fallback = "generic_fallback"


class CustomerContext(BaseModel):
    anonymous_id: Optional[str] = None
    customer_id: Optional[str] = None
    channel: Channel = Channel.web
    journey_stage: Optional[JourneyStage] = None
    current_intent: Optional[IntentType] = None
    session_events: List[str] = Field(default_factory=list)
    search_terms: List[str] = Field(default_factory=list)
    past_transactions: List[Dict[str, Any]] = Field(default_factory=list)
    profile_attributes: Dict[str, Any] = Field(default_factory=dict)
    business_context: Dict[str, Any] = Field(default_factory=dict)
    channel_context: Dict[str, Any] = Field(default_factory=dict)
    device_context: Dict[str, Any] = Field(default_factory=dict)
    consent: Dict[str, bool] = Field(default_factory=lambda: {"personalization": True})


class RecommendationCandidate(BaseModel):
    id: str
    title: str
    type: str
    channel: Channel
    description: str = ""
    intent_tags: List[IntentType] = Field(default_factory=list)
    journey_tags: List[JourneyStage] = Field(default_factory=list)
    content_tags: List[str] = Field(default_factory=list)
    business_value: float = Field(ge=0, le=1, default=0.5)
    margin_weight: float = Field(ge=0, le=1, default=0.5)
    inventory_weight: float = Field(ge=0, le=1, default=0.5)
    compliance_sensitivity: float = Field(ge=0, le=1, default=0.0)


class EDSBreakdown(BaseModel):
    intent_score: float
    engagement_score: float
    business_value_score: float
    journey_momentum_score: float
    context_relevance_score: float
    risk_adjustment: float
    final_eds_score: float


class ModelPrediction(BaseModel):
    label: str
    confidence: float
    source: str


class OrchestrationDecision(BaseModel):
    tier: str
    reason: str
    estimated_latency_ms: int
    estimated_cost_units: float
    used_teacher_signal: bool = False


class ExperienceMemorySnapshot(BaseModel):
    subject_id: str
    subject_type: str
    trust_score: float
    fatigue_score: float
    preferences: Dict[str, Any] = Field(default_factory=dict)
    recommendation_history: List[Dict[str, Any]] = Field(default_factory=list)
    outcomes: Dict[str, Any] = Field(default_factory=dict)


class TemporalKnowledgeGraphSummary(BaseModel):
    node_count: int
    edge_count: int
    temporal_edge_count: int
    journey_sequence: List[str] = Field(default_factory=list)
    inferred_intent: str = "unknown"
    inferred_intent_confidence: float = 0.0
    next_best_journey_stage: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    timeline_event_count: int = 0
    recent_outcomes: List[Dict[str, Any]] = Field(default_factory=list)


class OutcomeSimulation(BaseModel):
    conversion_probability: float
    revenue_impact: float
    trust_impact: float
    journey_impact: float
    compliance_risk: float
    fatigue_risk: float
    expected_outcome_score: float


class TAPLDecision(BaseModel):
    action: TAPLAction
    trust_score: float
    fatigue_score: float
    sensitivity_score: float
    compliance_score: float
    reason: str


class AIModelBreakdown(BaseModel):
    intent: ModelPrediction
    journey_stage: ModelPrediction
    orchestration: OrchestrationDecision
    tapl: TAPLDecision
    semantic_similarity_score: float
    channel_fit_score: float
    outcome_simulation: OutcomeSimulation
    ai_rank_score: float
    final_hybrid_score: float


class RankedRecommendation(BaseModel):
    candidate: RecommendationCandidate
    eds_score: EDSBreakdown
    ai_score: AIModelBreakdown
    reason_codes: List[str]
    explanation: str
    explanation_source: str = "local"


class RecommendationRequest(BaseModel):
    context: CustomerContext
    candidates: Optional[List[RecommendationCandidate]] = None
    limit: int = Field(default=3, ge=1, le=20)
    use_ai_models: bool = True
    use_llm: bool = False
    use_llm_explanation: bool = False


class ScenarioRecommendationRequest(BaseModel):
    scenario_text: str = Field(min_length=10, max_length=4000)
    limit: int = Field(default=3, ge=1, le=20)
    use_ai_models: bool = True
    use_llm: bool = False
    use_llm_explanation: bool = False


class RecommendationResponse(BaseModel):
    request_summary: Dict[str, Any]
    recommendations: List[RankedRecommendation]


class SyntheticTrainingRequest(BaseModel):
    domain: str = "travel"
    count: int = Field(default=20, ge=1, le=100)


class SimulationRequest(BaseModel):
    context: CustomerContext
    candidates: Optional[List[RecommendationCandidate]] = None


class CompareOutcomesRequest(BaseModel):
    context: CustomerContext
    candidate_id_a: str
    candidate_id_b: str
    use_ai_models: bool = True


class CompareOutcomesResponse(BaseModel):
    request_summary: Dict[str, Any]
    candidate_a: RankedRecommendation
    candidate_b: RankedRecommendation
    winner_candidate_id: str


class FeedbackEvent(BaseModel):
    customer_id: Optional[str] = None
    anonymous_id: Optional[str] = None
    recommendation_id: str
    channel: Channel = Channel.web
    event_type: str = "click"
    converted: bool = False
    revenue: float = 0.0
    context_snapshot: Dict[str, Any] = Field(default_factory=dict)


class BatchRecommendationRequest(BaseModel):
    requests: List[RecommendationRequest] = Field(min_length=1, max_length=50)


class WebhookRegistrationRequest(BaseModel):
    target_url: str = Field(min_length=8, max_length=2000)
    event_types: List[str] = Field(
        default_factory=lambda: ["recommendation.created", "feedback.received"]
    )


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: str = "queued"
    status_url: str
