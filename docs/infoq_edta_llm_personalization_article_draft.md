# Architecting Explainable, Trust-Aware Personalization with Local AI Models and Optional LLM Enrichment

## Draft For InfoQ Submission

**Working title:** Governed Personalization: A Four-Tier Architecture for Explainable, Trust-Aware Recommendations  
**Alternative title:** Beyond LLM-First Recommendations: Cost-Aware, Auditable Personalization with Rules, SLM, ML, and Optional LLM  
**Previous title:** Architecting Explainable, Trust-Aware Personalization with Local AI Models and Optional LLM Enrichment  
**Author:** Jerald Selvaraj  
**Target publication:** InfoQ Architecture / AI, ML & Data Engineering  
**Status:** Draft v2 (positioning refresh)  
**Live demo:** https://edta-api.onrender.com/scenario-demo  
**Reference repo:** https://github.com/jeraldcs/edta-complete-api

---

## Abstract

Enterprise teams are adopting LLMs for personalization faster than they are adopting **governance** for personalization. The result is relevant but risky recommendations: opaque scores, uncontrolled token cost, and weak answers to "why did we show this?"

Enterprise personalization systems are often implemented as opaque ranking services: a customer context enters the model, a recommendation comes out, and the surrounding teams are left to infer why the system made the decision. That approach becomes fragile when personalization must operate across web, mobile, chatbot, IoT, wearable, connected vehicle, and partner API channels, especially when trust, consent, fatigue, compliance, and explainability matter.

This article presents **EDTA (Experience-Driven Targeting Architecture)** — an implementation-oriented reference for a **governed decision pipeline**, not a single model. The design combines a runtime context graph, Experience DNA Score (EDS), a **four-tier inference stack** (Rules → SLM → ML → optional LLM) under a Hybrid AI Orchestration Engine (HAOE), a Trust-Aware Personalization Layer (TAPL), outcome simulation, known-user profile lookup, and a FastAPI recommendation API. The goal is not to replace deterministic governance or local models with a large language model, but to use the LLM selectively where it adds value: intent enrichment, explanation generation, and synthetic training data support — while **SLM-first explanation routing** keeps token cost bounded.

The result is a modular architecture where each decision responsibility is explicit: context interpretation, tier selection, intent prediction, journey-stage prediction, candidate matching, channel suitability, trust governance, outcome estimation, final ranking, and explanation generation. This separation makes the system easier to reason about, test, govern, and adapt across channels and industries (travel, hospitality, healthcare education).

---

## Key Takeaways

- **Personalization is a governance problem**, not only a ranking problem.
- **Four explicit inference tiers** (Rules, SLM, ML, LLM) beat a hidden routing layer for testability, cost control, and benchmarks.
- Personalization architectures should separate recommendation scoring, trust governance, outcome prediction, and explanation rather than hiding all decisions inside one black-box model.
- LLMs are useful for enrichment and explanation, but critical recommendation governance should remain auditable and deterministic.
- **TAPL must affect ranking**, not only logs — consent, fatigue, compliance sensitivity, and channel constraints are first-class inputs.
- **Distilled SLM memory** reduces LLM cost on repeat journeys; explanation routing prefers SLM before LLM escalation.
- A runtime context graph can convert live behavioral, profile, device, and business signals into reusable features for both local models and LLM prompts.
- Known-user personalization requires a profile lookup/enrichment layer before scoring, but live session behavior should still influence the final decision.
- **Explainability belongs in the API contract** — rules fired, inference tier, TAPL decision, outcome simulation, and explanation source.

---

## 1. The Problem With Opaque Personalization

Personalization has moved far beyond "customers who bought this also bought that." Modern digital experiences need to decide what to show, when to show it, how strongly to recommend it, and whether it should be suppressed entirely. A travel customer browsing SUV rentals on the web, a patient support user in a chatbot, and a connected device emitting a service signal all require different recommendation behavior.

Many recommendation systems treat this as a ranking problem only. The architecture is often reduced to:

```text
context -> model -> ranked recommendation
```

That pattern is not enough for enterprise-grade personalization. It does not clearly answer:

- Why was this recommendation selected?
- Was customer consent respected?
- Was the channel appropriate?
- Did the system consider fatigue?
- Was the content sensitive?
- Did the decision optimize only conversion, or also trust and journey momentum?
- Can the system work if the LLM provider is unavailable?

The architecture described here addresses those questions by decomposing personalization into explicit decision modules.

---

## 2. Reference Architecture

At a high level, the system has four runtime layers:

```text
Web or channel experience
  -> FastAPI recommendation API
    -> Recommendation engine
      -> Context graph, profile lookup, EDS, AI models, TAPL, LLM enrichment
```

The implemented flow is:

```text
Browser or channel client
  -> POST /recommend
  -> Validate request contract
  -> Enrich known-user profile
  -> Build runtime context graph
  -> Resolve intent and journey stage
  -> Score candidates with EDS
  -> Compute semantic similarity
  -> Apply TAPL trust governance
  -> Simulate outcome
  -> Rank recommendations
  -> Generate explanation
  -> Return personalized response
```

The key architectural decision is that the recommendation engine is not a single model. It is an orchestrator. Each module owns a specific decision responsibility.

### 2.1 Four-tier inference and why it matters

Most 2024–2026 personalization stacks converge on some mix of rules, ML, and LLM. EDTA makes tiers **first-class and benchmarkable**:

```text
Rules  -> deterministic, auditable (YAML packs + EDS + TKGE-boosted confidence)
SLM    -> distilled pattern memory + optional small-model endpoint + rules fallback
ML     -> sklearn intent / journey / TAPL / outcome / ranker
LLM    -> optional teacher (intent enrichment, explanation, synthetic labels)
```

The **Hybrid AI Orchestration Engine (HAOE)** selects tier by confidence, cost budget, and policy YAML — not by ad hoc branching in application code. **Explanation routing** (SLM first, LLM escalation when enabled) treats explanation cost the same way teams treat API rate limits or connection pools.

Each tier returns a unified **InferenceResult**: tier, confidence, rules fired, signals, fallback metadata. This contract is what makes four-tier personalization **testable** in CI and **comparable** in load benchmarks (`docs/BENCHMARKS.md`).

### 2.2 Industry scenarios (travel lead, healthcare scope)

**Travel / car rental (primary demo narrative):** A family traveler searching for an airport SUV rental moves from research to booking in one session. EDTA routes structured booking context through the **Rules** or **ML** tier, applies **TAPL** for fatigue, and explains via **SLM-first** routing. Example scenario: *"customer checked SUV availability and started booking airport rental"* → `vehicle_upgrade_suv` with full EDS/TAPL/outcome breakdown. Live demo: https://edta-api.onrender.com/scenario-demo

**Healthcare HCP education (governance narrative):** An HCP browsing obesity product education needs **approved content routing**, not aggressive cross-sell. **TAPL** suppresses or softens on sensitive channels (SMS, push, wearable); **rules_fired** and audit logs support inspection. **Scope boundary:** this reference implementation supports **HCP education and approved commercial content routing**. It is **not** a clinical decision support system and does not recommend diagnosis, treatment, or off-label use.

The engine is **vertical-agnostic at the core** and **vertical-specific at the policy layer** — YAML rule packs, TAPL policies, and catalog candidates swap per industry without rewriting the orchestrator.

---

## 3. The Data Contract

The API contract starts with a `CustomerContext`. The context contains both anonymous and known-user signals:

```python
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
```

This structure allows the same recommendation API to serve several channels:

- Web personalization
- Chatbot next-best action
- IoT service alert
- Wearable micro-prompt
- Connected vehicle prompt
- Partner API decisioning

The request also includes runtime switches:

```python
class RecommendationRequest(BaseModel):
    context: CustomerContext
    candidates: Optional[List[RecommendationCandidate]] = None
    limit: int = Field(default=3, ge=1, le=20)
    use_ai_models: bool = True
    use_llm: bool = False
    use_llm_explanation: bool = False
```

These switches are important operationally. The API can run with local models only, attempt LLM enrichment, or request LLM-generated explanations. If the LLM is unavailable, the system falls back to local prediction.

---

## 4. Known-User Profile Lookup

Anonymous personalization can rely on live session behavior. Known-user personalization adds historical and profile context. In this implementation, the profile lookup layer is represented by a `ProfileLookupService`:

```text
customer_id
  -> profile lookup
  -> merge profile attributes, transactions, consent, business context
  -> enriched CustomerContext
```

The demo uses a local JSON file as a mock external CRM/CDP/loyalty source:

```json
{
  "cust-789": {
    "profile_attributes": {
      "loyalty_tier": "preferred",
      "preferred_vehicle_class": "SUV",
      "home_airport": "SFO",
      "family_traveler": true,
      "lifetime_rentals": 9,
      "fatigue_count": 1
    },
    "business_context": {
      "customer_value_segment": "high",
      "eligible_upgrade_credit": true,
      "loyalty_offer_eligible": true
    },
    "consent": {
      "personalization": true,
      "profile_lookup": true
    }
  }
}
```

In production, this boundary can be replaced with an HTTP client or database adapter. The key design principle is to keep profile lookup outside the core recommendation engine. The engine should receive an enriched context, but not own identity resolution or customer master-data logic.

---

## 5. Runtime Context Graph

The `ContextGraph` turns structured input into two useful representations:

1. A graph-like summary of nodes and edges.
2. A text representation for local text models and optional LLM prompts.

For example, this web context:

```json
{
  "channel": "web",
  "session_events": [
    "viewed_vehicle_page",
    "searched_suv",
    "checked_location_availability",
    "started_booking"
  ],
  "search_terms": ["family SUV airport rental"],
  "profile_attributes": {
    "loyalty_tier": "preferred",
    "trip_type": "family"
  }
}
```

becomes a reusable context representation containing signals such as:

```text
web, viewed, vehicle, searched, suv, airport, rental, family, preferred
```

This representation is used by:

- Intent prediction
- Journey-stage prediction
- Semantic similarity scoring
- EDS context overlap
- LLM intent enrichment
- Explanation generation

The context graph is deliberately simple in this implementation. In a production environment, it could be extended into a real-time feature graph or event graph backed by a feature store.

---

## 6. Experience DNA Score

The Experience DNA Score, or EDS, provides an explainable scoring layer before the final AI ranker. It combines several factors:

```text
intent_score
engagement_score
business_value_score
journey_momentum_score
context_relevance_score
risk_adjustment
```

The score is calculated as:

```python
final = (
    intent_score * 0.25
    + engagement_score * 0.15
    + business_score * 0.20
    + journey_score * 0.20
    + context_score * 0.20
    - risk_adjustment
)
```

EDS is intentionally transparent. It gives architects and business stakeholders a clear reason model:

- Did the predicted intent match the candidate?
- Is the user engaged?
- Is there business value?
- Does the recommendation fit the journey stage?
- Does the content overlap with the live context?
- Should risk reduce the score?

This is useful because final rank scores are often difficult to interpret. EDS provides a human-readable scoring foundation that can be logged, audited, and explained.

---

## 7. Local AI Models

The system includes local AI modules for specialized decisions:

```text
IntentModel
JourneyStageModel
TAPLModel
ChannelFitModel
SemanticSimilarityModel
OutcomeSimulationModel
FinalRankerModel
```

This modular design avoids overloading one model with every decision. For example:

- `IntentModel` predicts whether the user is researching, purchasing, seeking support, upgrading, or retaining.
- `JourneyStageModel` predicts awareness, research, consideration, purchase, service, or retention.
- `SemanticSimilarityModel` compares the context text with candidate content.
- `OutcomeSimulationModel` estimates conversion probability, revenue impact, trust impact, fatigue risk, and expected outcome.
- `FinalRankerModel` produces the final AI ranking score.

Some modules load trained `.joblib` models. Others use deterministic scoring when a model is unavailable. This matters operationally because the API should remain useful in degraded mode.

---

## 8. Trust-Aware Personalization Layer

The Trust-Aware Personalization Layer, or TAPL, is the governance layer. It evaluates:

- Personalization consent
- Fatigue count
- Candidate compliance sensitivity
- Channel constraints
- Trust score
- Compliance score

TAPL returns one of five actions:

```text
show
soften
delay
suppress
generic_fallback
```

The important design choice is that TAPL directly affects ranking:

```python
if tapl.action.value in {"suppress", "generic_fallback"}:
    final_hybrid = min(ai_rank_score, 0.15)
elif tapl.action.value == "delay":
    final_hybrid = ai_rank_score * 0.55
elif tapl.action.value == "soften":
    final_hybrid = ai_rank_score * 0.85
else:
    final_hybrid = ai_rank_score
```

This prevents governance from becoming a passive label. If the system detects missing consent, high fatigue, or sensitive content in a constrained channel, the recommendation is penalized or capped.

---

## 9. Optional LLM Enrichment

The LLM layer is deliberately optional. It is used for three purposes:

1. Intent and journey enrichment.
2. Recommendation explanation.
3. Synthetic training data generation.

The LLM client enables itself only when an API key is present:

```python
self.enabled = bool(os.getenv("OPENAI_API_KEY"))
```

When `use_llm=true`, the recommendation engine tries:

```python
enriched = self.llm.enrich_intent(context_text)
```

The LLM is asked to return a constrained JSON object:

```json
{
  "intent": "research|purchase|support|retention|upgrade|unknown",
  "confidence": 0.0,
  "journey_stage": "awareness|research|consideration|purchase|service|retention",
  "reason": "short reason"
}
```

If the LLM response is unavailable or invalid, the engine falls back to local models. This fallback is not a minor implementation detail; it is a core architectural principle. Personalization should not become unavailable because an external generative provider is unavailable.

---

## 10. Example: Known Web User Looking for an SUV

Consider a known customer:

```json
{
  "customer_id": "cust-789",
  "channel": "web",
  "session_events": [
    "viewed_vehicle_page",
    "searched_suv",
    "started_booking"
  ],
  "search_terms": ["airport SUV rental"],
  "consent": {
    "personalization": true,
    "profile_lookup": true
  }
}
```

The system performs the following steps:

1. `ProfileLookupService` enriches the context with loyalty tier, prior rentals, preferred vehicle class, and business eligibility.
2. `ContextGraph` extracts keywords such as `suv`, `airport`, `rental`, `preferred`, and `family`.
3. Intent and journey models classify the user as likely purchase or upgrade intent in the consideration/purchase stage.
4. The catalog candidate `Premium SUV upgrade` matches:
   - Channel: web
   - Intent tags: purchase, upgrade
   - Journey tags: consideration, purchase
   - Content tags: family, car rental, upgrade, SUV, airport
5. EDS assigns high scores for intent, engagement, business value, journey match, and context relevance.
6. TAPL permits the action because personalization consent is true, fatigue is low, and compliance sensitivity is low.
7. Outcome simulation predicts high conversion and revenue impact.
8. The final ranker returns the top recommendation.
9. The frontend updates the page hero, CTA, recommendation card, signal panel, and ranked recommendation list.

The visible result is:

```text
Hero: Premium SUV upgrade
CTA: Continue with this recommendation
Reason: selected with intent=purchase, journey=consideration, TAPL action=show
```

---

## 11. Why This Architecture Is Different

The architectural contribution is the separation of decision responsibilities. Instead of relying on a monolithic model, the system makes each layer explicit:

```text
Profile lookup: enrich known-user context
Context graph: normalize live signals
Intent model: classify what the user is trying to do
Journey model: classify lifecycle stage
EDS: provide explainable relevance and business score
TAPL: enforce trust and governance
Outcome model: estimate downstream impact
Ranker: select final order
LLM: enrich and explain when available
```

This separation creates several benefits:

- Easier debugging: each score can be inspected.
- Better governance: trust controls are explicit.
- Better resilience: LLM failure does not break the system.
- Better portability: the same API can serve multiple channels.
- Better extensibility: new candidate types and channels can be added without rewriting the whole engine.

---

## 12. Operational Considerations

An enterprise implementation of this architecture should consider:

### Observability

Every recommendation should log:

- Request ID
- Customer or anonymous ID
- Channel
- Predicted intent and source
- Journey stage and source
- EDS breakdown
- TAPL action
- Outcome score
- Final rank score
- Reason codes
- LLM availability and fallback status

### Governance

Trust-aware controls should be testable. Teams should create tests for:

- Missing personalization consent
- High fatigue
- Sensitive content
- Constrained channels such as SMS, wearable, voice assistant, or IoT
- LLM failure
- Unknown customer profile

### Model Lifecycle

The system should support:

- Offline training from feedback data
- Model versioning
- A/B testing
- Shadow scoring
- Drift detection
- Human review for high-risk recommendation categories

### Profile Lookup

The profile lookup layer should remain a facade. The recommendation engine should not know whether profile data came from:

- CRM
- CDP
- Loyalty platform
- Data warehouse
- Feature store
- Partner API

That separation keeps the engine portable.

---

## 13. Lessons Learned

The main lesson is that LLMs should not be inserted into personalization systems as an uncontrolled ranking layer. They are better used as an optional intelligence layer around a governed recommendation pipeline.

In this architecture, the LLM can help interpret context and generate explanations, but it does not own consent enforcement, channel safety, compliance sensitivity, fatigue management, or final ranking. Those decisions remain visible and testable.

The second lesson is that explainability must be designed into the data contract. If the API only returns a candidate ID and score, the frontend and business teams cannot understand the decision. Returning EDS breakdowns, model predictions, TAPL decisions, outcome simulation, and reason codes makes the system usable by engineering, product, compliance, and architecture teams.

The third lesson is that known-user personalization should merge historical profile context with live session context. A static customer profile is not enough. A live session without history is also incomplete. The best recommendation usually comes from the intersection of both.

---

## 14. Conclusion

Enterprise personalization is no longer just a ranking problem. It is an architecture problem involving identity, context, consent, trust, channel constraints, model resilience, and explanation.

The architecture presented here demonstrates one way to build a modular personalization engine that combines local AI models, explainable scoring, trust-aware governance, known-user profile enrichment, and optional LLM assistance. The central design principle is separation of responsibility: each module owns a specific decision, and the final recommendation is assembled from transparent, inspectable signals.

This makes the system practical for multi-channel personalization while also preserving the ability to explain why a recommendation was selected, why it was delayed or suppressed, and how the decision would behave if the LLM were unavailable.

---

## Suggested Diagrams For Article

### Diagram 1: Runtime Architecture

```text
Browser / Channel Client
  -> POST /recommend
  -> FastAPI
  -> Profile Lookup
  -> Context Graph
  -> LLM or Local Intent/Journey
  -> EDS
  -> TAPL
  -> Outcome Simulation
  -> Final Ranker
  -> Personalized Response
```

### Diagram 2: Decision Responsibility Model

```text
Identity/Profile        -> Who is this user?
Live Context            -> What is happening now?
HAOE Tier Selection     -> Rules, SLM, ML, or LLM?
Intent/Journey          -> What is the user trying to do?
EDS                     -> How relevant and valuable is the candidate?
TAPL                    -> Should we show, soften, delay, or suppress?
Outcome Simulation      -> What impact do we expect?
Ranker                  -> What should be ordered first?
Explanation Router      -> SLM first, LLM escalation if needed
```

### Table 1: Four-tier benchmark (structured travel scenario)

*Caption: Forced `inference_mode` per tier on SUV rental payload. Latency targets from local Docker; quality probes from tier match and training-alignment top-1. Hosted demo adds platform/network overhead — report separately.*

| Tier | p95 latency (Docker)* | Tier match | Alignment top-1 | Explainability |
|------|------------------------:|-----------:|----------------:|----------------|
| Rules | ~20–50 ms | 100% | 100% | rules_fired (avg ~2) |
| SLM | ~50–150 ms | 100% | 100% | pattern + rules fallback |
| ML | ~200–400 ms | 100% | 100% | feature-level scores |
| LLM | ~3–8 s | varies | n/a (sparse payload) | natural language |

*Reproduce with `scripts/load_test_tiers.py` and `docs/BENCHMARKS.md`.*

---

## Suggested Author Bio

Jerald Selvaraj is an enterprise architecture and digital experience technology leader focused on AI-enabled personalization, omnichannel platforms, customer experience architecture, and responsible recommendation systems. His work spans experience decisioning, marketing technology, platform modernization, and applied AI architectures for scalable digital ecosystems.

---

## Evidence Notes For EB-1A Positioning

This section is not intended for publication in InfoQ. It is included to help prepare a stronger evidence package around the article. See also **`docs/EB1A_ORIGINAL_CONTRIBUTION.md`** and **`docs/INFOQ_POSITIONING.md`** in the repository.

To make this article more useful for an EB-1A record, collect supporting evidence around:

1. **Original contribution**
   - Explain what is novel about combining EDS, TAPL, local AI, LLM enrichment, profile lookup, and multi-channel API decisioning.
   - Preserve architecture diagrams, code repository history, demo screenshots, and design rationale.

2. **Major significance**
   - Add measurable results if available: conversion lift, recommendation accuracy, response latency, profile enrichment impact, governance reduction, channel reuse, or cost savings.
   - If deployed in an organization, obtain letters explaining why the architecture mattered.

3. **Authorship**
   - Keep publication acceptance, article URL, editorial correspondence, and author page.
   - Maintain a PDF copy of the published article.

4. **Published material about the work**
   - Track third-party mentions, citations, newsletters, reposts, conference references, or expert commentary.

5. **Critical role**
   - If this architecture was created as part of a distinguished employer/client initiative, collect letters confirming your leading or critical contribution.

6. **Judging**
   - Use this expertise to judge architecture submissions, AI hackathons, technical papers, or industry awards where appropriate.

7. **Expert letters**
   - Ask independent experts to comment specifically on technical originality, industry relevance, and significance beyond routine implementation.

Avoid unsupported claims. The article should be technically strong and credible on its own; EB-1A value comes from independent recognition, adoption, and documented impact.
