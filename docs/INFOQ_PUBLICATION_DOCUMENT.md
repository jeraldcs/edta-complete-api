# EDTA — InfoQ Publication Document

## Governed Personalization: A Four-Tier Architecture for Explainable, Trust-Aware Recommendations

**Author:** Jerald Selvaraj  
**Contact:** jerald.cs@gmail.com  
**Version:** Publication package v2 — July 2026  
**Status:** Ready for InfoQ Architecture / AI, ML & Data Engineering submission  

| Resource | URL |
|----------|-----|
| **Live demo** | https://edta-api.onrender.com/scenario-demo |
| **GitHub** | https://github.com/jeraldcs/edta-complete-api |
| **OpenAPI** | https://edta-api.onrender.com/docs |
| **Architecture PDF** | `docs/edta_architecture_diagram.pdf` (3 pages — regenerate: `python docs/generate_architecture_pdf.py`) |
| **Word export** | `docs/INFOQ_PUBLICATION_DOCUMENT.docx` |

---

## Editor summary (50 words)

Enterprise teams adopt LLMs for personalization faster than governance. **EDTA (Experience-Driven Targeting Architecture)** is an open reference for a governed decision pipeline: explicit **Rules / SLM / ML / LLM** tiers, **trust-aware ranking (TAPL)**, outcome simulation, and API-native explainability. A live travel demo runs **eleven trained road-trip scenarios** with auditable scores. LLMs enrich and explain; they do not own consent or compliance.

---

## Table of contents

1. [Abstract](#1-abstract)
2. [Key takeaways](#2-key-takeaways)
3. [Problem statement](#3-problem-statement)
4. [Reference architecture](#4-reference-architecture)
5. [Implementation overview (latest code)](#5-implementation-overview-latest-code)
6. [Data contract](#6-data-contract)
7. [Layer-by-layer design](#7-layer-by-layer-design)
8. [Empathy engine and travel vertical](#8-empathy-engine-and-travel-vertical)
9. [Four-tier inference (HAOE)](#9-four-tier-inference-haoe)
10. [Trust-aware personalization (TAPL)](#10-trust-aware-personalization-tapl)
11. [Live demo walkthrough](#11-live-demo-walkthrough)
12. [Benchmarks and evidence](#12-benchmarks-and-evidence)
13. [Why EDTA is different](#13-why-edta-is-different)
14. [Operational considerations](#14-operational-considerations)
15. [Lessons learned](#15-lessons-learned)
16. [Scope and honest limits](#16-scope-and-honest-limits)
17. [GitHub repository guide](#17-github-repository-guide)
18. [Suggested InfoQ submission package](#18-suggested-infoq-submission-package)
19. [Architecture diagrams](#19-architecture-diagrams)

---

## 1. Abstract

Enterprise personalization systems are often implemented as opaque ranking services: a customer context enters the model, a recommendation comes out, and surrounding teams infer *why* the system made the decision. That approach breaks when personalization must operate across web, mobile, chatbot, IoT, wearable, connected vehicle, and partner API channels — especially when trust, consent, fatigue, compliance, and explainability matter.

This document presents **EDTA (Experience-Driven Targeting Architecture)** — an implementation-oriented reference for a **governed decision pipeline**, not a single model. The design combines:

- A **Temporal Knowledge Graph Engine (TKGE)** for live journey context
- An **Experience Memory Layer (EML)** for trust, fatigue, and preference state
- A **Hybrid AI Orchestration Engine (HAOE)** with explicit **Rules → SLM → ML → optional LLM** tiers
- **Experience DNA Score (EDS)** for explainable relevance
- **Trust-Aware Personalization Layer (TAPL)** that affects ranking, not only logs
- **Outcome Simulation Engine (OSE)** for expected conversion and revenue impact
- An **Empathy Engine** for travel scenarios — hidden needs, route enrichment, TCO, and constraint-based vehicle fit
- A **FastAPI** surface with auditable API contracts and a browser scenario demo

The LLM is optional: it enriches and explains; it does **not** own consent, compliance, fatigue, or final trust governance.

---

## 2. Key takeaways

- **Personalization is a governance problem**, not only a ranking problem.
- **Four explicit inference tiers** (Rules, SLM, ML, LLM) beat a hidden routing layer for testability, cost control, and benchmarks.
- **TAPL must affect ranking** — consent, fatigue, compliance sensitivity, and channel constraints are first-class inputs.
- **Distilled SLM memory** reduces LLM cost on repeat journeys; explanation routing prefers SLM before LLM escalation.
- A **runtime context graph (TKGE)** converts live behavioral, profile, device, and business signals into reusable features.
- **Known-user personalization** requires profile lookup before scoring; live session behavior still influences the final decision.
- **Explainability belongs in the API contract** — rules fired, inference tier, TAPL decision, outcome simulation, and explanation source.
- **Travel demo** proves vertical extension without rewriting the core — empathy profiles, constraints, and 11-scenario benchmark matrix.

---

## 3. Problem statement

Many recommendation systems reduce personalization to:

```text
context → model → ranked recommendation
```

That pattern fails enterprise requirements:

| Gap | Consequence |
|-----|-------------|
| Opaque ranking | Product and compliance cannot answer *why* |
| LLM-first design | Unbounded cost, latency, and provider dependency |
| Trust as metadata | Consent/fatigue logged but not enforced in ranking |
| Single-channel thinking | Web, chatbot, IoT, wearable need unified policy |
| No outcome view | Optimizes click-through, not expected business outcome |
| Weak explainability | No rules fired, tier, TAPL action, or score breakdown in API |
| Vertical monolith | Each industry rewrites the engine instead of policy layers |

EDTA decomposes personalization into **testable modules** with explicit responsibilities and API-visible decisions.

---

## 4. Reference architecture

### 4.1 System context

```text
Channel clients (web, chatbot, IoT, partner API)
  → FastAPI (POST /recommend, POST /recommend-from-scenario)
    → RecommendationHandlers
      → Profile lookup + EML enrich + TKGE graph + HAOE tier
      → EmpathyEngine (travel scenario path)
      → RecommendationEngine (EDS → TAPL → OSE → ranker)
      → Explanation router (SLM first, LLM optional)
    → Auditable JSON + demo architecture panels
```

**Deployment:** Public demo on Render (`render.yaml`); local/Docker for latency benchmarks.

### 4.2 Logical layer stack

| Acronym | Name | Role |
|---------|------|------|
| **TKGE** | Temporal Knowledge Graph Engine | Journey timeline, inferred intent, per-scenario subjects |
| **EML** | Experience Memory Layer | Trust, fatigue, preferences, recommendation history |
| **HAOE** | Hybrid AI Orchestration Engine | Rules / SLM / ML / LLM tier selection |
| **EDS** | Experience DNA Score | Explainable relevance before ranker fusion |
| **TAPL** | Trust-Aware Personalization Layer | show / soften / delay / suppress / generic_fallback |
| **OSE** | Outcome Simulation Engine | Conversion, revenue, expected outcome score |
| **Empathy** | Travel vertical extension | Hidden needs, constraints, TCO, trained profiles |

See **Section 19** and `docs/edta_architecture_diagram.pdf` for visual diagrams aligned with the current codebase.

---

## 5. Implementation overview (latest code)

### 5.1 Two primary request paths

**Structured API — `POST /recommend`**

```text
CustomerContext
  → ProfileLookupService.enrich_context()
  → ExperienceMemory.enrich_context()  (EML)
  → ContextGraph + graph_store timeline  (TKGE)
  → HAOE.select_tier()
  → RecommendationEngine.recommend()
      loop candidates: EDS → semantic → channel fit → TAPL → OSE → ranker
  → record EML + save graph snapshot
  → ExplanationRouter → RecommendationResponse
```

**Free-text demo — `POST /recommend-from-scenario`**

Used by https://edta-api.onrender.com/scenario-demo and the travel benchmark:

```text
scenario_text
  → ScenarioNLPParser.parse()                    [app/scenario_nlp.py]
  → scenario_anonymous_id()                      [app/empathy/scenario_profiles.py]
  → ProfileLookupService + EML enrich
  → EmpathyEngine.process()                      [app/empathy/service.py]
  → merge vehicle_candidates() catalog
  → RecommendationEngine.recommend()
  → attach empathy vehicle + TKGE/EML/HAOE/OSE/TAPL panels
  → RecommendationResponse
```

**Entry point:** `app/services/recommendation_handlers.py` → `recommend_from_scenario()`.

### 5.2 Demo UI stack

| Component | File | Purpose |
|-----------|------|---------|
| Scenario page | `static/scenario.html` | Textarea, Recommend form, result panels |
| Client logic | `static/scenario_app.js` | Form submit, fetch, panel rendering |
| Shared UI | `static/demo-shared.js` | TAPL, architecture cards, benchmark table |
| Server inject | `app/demo_html.py` | Inline `window.__EDTA_DEMO_CONFIG__`, cache-bust |
| Benchmark API | `GET /travel-scenario-benchmark` | 11-scenario score matrix |

### 5.3 Service wiring

`app/container.py` wires:

- `RecommendationEngine` (`app/recommender.py`)
- `EmpathyEngine` (`app/empathy/service.py`)
- `ScenarioNLPParser` (`app/scenario_nlp.py`)
- `ExperienceMemory` + `EMLStore` + `GraphStore`
- `HAOEOrchestrator` (`app/orchestration.py`)
- ML models under `app/ai/`
- Optional LLM clients under `app/llm/`

---

## 6. Data contract

The API contract starts with `CustomerContext` (`app/models.py`):

```python
class CustomerContext(BaseModel):
    anonymous_id: Optional[str] = None
    customer_id: Optional[str] = None
    channel: Channel = Channel.web
    journey_stage: Optional[JourneyStage] = None
    current_intent: Optional[IntentType] = None
    session_events: List[str] = Field(default_factory=list)
    search_terms: List[str] = Field(default_factory=list)
    profile_attributes: Dict[str, Any] = Field(default_factory=dict)
    business_context: Dict[str, Any] = Field(default_factory=dict)
    consent: Dict[str, bool] = Field(default_factory=lambda: {"personalization": True})
```

Runtime switches on `RecommendationRequest`:

```python
use_ai_models: bool = True
use_llm: bool = False
use_llm_explanation: bool = False
```

These switches allow local-only operation, LLM enrichment when budget allows, and graceful fallback when providers are unavailable.

---

## 7. Layer-by-layer design

### 7.1 Scenario NLP

**Files:** `app/scenario_nlp.py`

Parses free text into channel, intent, journey stage, consent flags, fatigue/trust hints, session events, and search terms. Parser confidence is exposed for HAOE tier routing.

### 7.2 Profile lookup

**Files:** `app/profile_service.py`, `app/profile/adapters/json_file.py`

Identity resolution stays **outside** the recommender. Demo profile `cust-789` provides loyalty tier, SFO home airport, family traveler flags, and business eligibility.

### 7.3 TKGE — Temporal Knowledge Graph

**Files:** `app/context_graph.py`, `app/graph_store.py`

Builds nodes and temporal edges from context; maintains `live_journey_sequence`; persists per-subject timeline. Scenario runs use isolated subjects like `anonymous:travel-winter_mountain_denver` so demo scenarios do not overwrite each other.

### 7.4 EML — Experience Memory

**Files:** `app/experience_memory.py`, `app/eml_store.py`

SQLite persistence for trust, fatigue, preferences, and outcome history. Influences TAPL inputs and OSE calibration (`historical_cvr`). Demo panels show trust/fatigue before → after each run.

### 7.5 EDS — Experience DNA Score

**Files:** `app/eds.py`

Transparent scoring: intent match, engagement, business value, journey momentum, context overlap (TKGE keywords), minus risk adjustment. Returns human-readable reason codes (`intent_match`, `context_overlap:suv`, etc.).

### 7.6 OSE — Outcome Simulation

**Files:** `app/ai/outcome_model.py`

Estimates conversion probability, revenue impact, trust/journey impact, compliance and fatigue risk. Blends ML with heuristics when models saturate; applies EML historical calibration.

### 7.7 Final ranker

**Files:** `app/recommender.py`, `app/ai/ranker_model.py`

Hybrid score from EDS, semantic similarity, channel fit, TAPL trust, OSE expected outcome, business value, and penalties. Returns:

- `ai_rank_score` — base rank before TAPL cap
- `final_hybrid_score` — after TAPL and empathy adjustments

### 7.8 Explanation router

**Files:** `app/inference/explanation_router.py`, `app/llm/slm_client.py`, `app/llm/llm_client.py`

Order: SLM / local template first → LLM escalation if enabled and budget allows. API field: `explanation_source` — `local`, `slm`, `llm`, `local_fallback`.

---

## 8. Empathy engine and travel vertical

Travel is the **primary demo vertical** with **11 trained scenarios** (cust-789 loyalty rental + 10 road-trip archetypes).

### 8.1 Pipeline

```text
Scenario text
  → Hidden needs extractor     (hidden_needs.yaml — word-boundary rules)
  → Scenario profile matcher   (scenario_profiles.yaml — 11 profiles)
  → Trip extractor + route planner
  → Weather / route enrichment
  → Constraint matcher         (AWD, ISOFIX, EV range, cargo)
  → TCO calculator
  → Empathy vehicle + pitch → merged into ranking via empathy boost
```

### 8.2 Key modules

| Module | File | Function |
|--------|------|----------|
| Orchestration | `app/empathy/service.py` | Wires empathy into `business_context` |
| Hidden needs | `app/empathy/hidden_needs.py` | Pattern rules with word-boundary matching |
| Profiles | `app/empathy/scenario_profiles.py` | Keywords, persona, preferred vehicle, scoring hints |
| Corpus | `config/empathy/trained_scenarios.yaml` | Canonical texts for tests and benchmark |
| Constraints | `app/empathy/constraint_matcher.py` | Maps needs → vehicle specs |
| TCO | `app/empathy/tco_calculator.py` | Rental + fuel trip cost comparisons |
| Benchmark | `app/services/travel_benchmark.py` | Score extraction for 11 scenarios |

### 8.3 Trained scenario matrix

| # | Profile | Expected vehicle | Objective |
|---|---------|------------------|-----------|
| 0 | loyalty_family_rental | family_friendly_suv | cust-789 SFO family SUV rental |
| 1 | winter_mountain_denver | awd_suv | Winter Denver 500-mile trip |
| 2 | long_family_vacation | large_family_suv | NJ → Orlando, family of five |
| 3 | business_executive | luxury_sedan | 35k annual business miles |
| 4 | national_park_adventure | awd_suv | Multi-park adventure |
| 5 | urban_commuter | hybrid_midsize | 18k urban commute |
| 6 | electric_vehicle | electric_midsize | First EV purchase |
| 7 | luxury_winter_suv | premium_suv | Colorado luxury winter |
| 8 | first_time_driver | economy_compact | New driver |
| 9 | rental_seattle_vacation | awd_suv | Seattle 7-day rental |
| 10 | wet_weather_hurricane | awd_suv | Hurricane season Southeast |

Regenerate scored matrix: `python scripts/benchmark_travel_scenarios.py` → `docs/TRAVEL_SCENARIO_SCORES.md`.

---

## 9. Four-tier inference (HAOE)

**Files:** `app/orchestration.py`, `app/haoe_policy.py`, `config/haoe_policies.yaml`

```text
Rules  → deterministic YAML packs + EDS + TKGE-boosted confidence
SLM    → distilled pattern memory + optional endpoint + rules fallback
ML     → sklearn intent / journey / TAPL / outcome / ranker
LLM    → optional teacher (intent enrichment, explanation, synthetic labels)
```

HAOE selects tier by confidence, session cost budget, and policy YAML. Each tier returns a unified **InferenceResult**: tier, confidence, rules fired, cost units, fallback metadata.

**Benchmark:** `scripts/load_test_tiers.py`, `docs/BENCHMARKS.md`.

| Tier | Typical p95 (Docker) | Tier match | Explainability |
|------|---------------------:|-----------:|----------------|
| Rules | ~20–50 ms | 100% | rules_fired |
| SLM | ~50–150 ms | 100% | pattern + rules fallback |
| ML | ~200–400 ms | 100% | feature-level scores |
| LLM | ~3–8 s | varies | natural language |

*Hosted Render demo adds platform cold-start overhead — report separately from engine benchmarks.*

---

## 10. Trust-aware personalization (TAPL)

**Files:** `app/ai/tapl_model.py`, `app/tapl_policy.py`, `config/tapl_policies.yaml`, `app/tapl_audit.py`

TAPL evaluates consent, fatigue, compliance sensitivity, channel constraints, and trust score. Actions:

| Action | Effect on ranking |
|--------|-------------------|
| `show` | Full hybrid score |
| `soften` | Score × 0.85 |
| `delay` | Score × 0.55 |
| `suppress` / `generic_fallback` | Cap score at 0.15 |

Policy examples:

- No personalization consent → `generic_fallback`
- Fatigue ≥ threshold → `delay`
- Sensitive channel + high compliance content → `suppress`

TAPL decisions are SQLite-audited and returned in every recommendation response.

---

## 11. Live demo walkthrough

**URL:** https://edta-api.onrender.com/scenario-demo

### Demo UI sections

| Section | What it shows |
|---------|----------------|
| Scenario input + Recommend | Free-text → `POST /recommend-from-scenario` |
| Recommendation result | Top candidate, hybrid score, TAPL action, empathy badge |
| Parsed NLP context | Channel, intent, journey, parser confidence |
| Empathy panels | Hidden needs, weather/terrain, TCO, empathy pitch |
| Architecture panels | TKGE, EML, HAOE, OSE, TAPL per run |
| API request/response | Raw JSON for integrators |
| Travel benchmark table | 11 scenarios with EDS, outcome, trust, rank scores |

### 5-minute demo script

1. **Default cust-789** — loyalty family SUV, high trust, `loyalty_family_rental` profile
2. **Winter Denver** — paste scenario 1 → `awd_suv`, mountain constraints
3. **Consent false** — add “personalization consent false” → TAPL `generic_fallback`
4. **High fatigue** — “fatigue count 8” → TAPL `delay`
5. **Benchmark table** — scroll to 11 scenarios with distinct scores

---

## 12. Benchmarks and evidence

### Travel scenario matrix

- **11/11 vehicle match (100%)** — see `docs/TRAVEL_SCENARIO_SCORES.md`
- API: `GET /travel-scenario-benchmark`
- Tests: `tests/test_trained_travel_scenarios.py`

### Test suite

```bash
pytest   # 149+ passed — API, TAPL, empathy, trained scenarios, demo UI
```

### Four-tier benchmarks

See `docs/BENCHMARKS.md` — tier routing fidelity, latency, cost units, fallback rates.

**Not claimed without partner data:** Production A/B conversion lift or Netflix-scale generalization.

---

## 13. Why EDTA is different

| Pattern | Typical approach | EDTA difference |
|---------|------------------|-----------------|
| LLM-first personalization | One prompt → recommendation | LLM optional; TAPL + rules own governance |
| Monolithic ranker | Single model score | EDS + TAPL + OSE + ranker — each auditable |
| Trust as logging | Trust score in analytics only | TAPL modifies rank and action |
| Hidden routing | Ad hoc if/else | HAOE with YAML policy + InferenceResult |
| Stateless API | Each request independent | EML + TKGE timeline across sessions |
| Vertical rewrite | New engine per industry | Same core; swap YAML, catalog, empathy profiles |
| Travel recommender | Filter by category | Hidden needs + constraints + TCO + trained profiles |

**Original contribution:** A governed, multi-tier, memory-aware personalization pipeline with API-native explainability — implemented as open reference code with live demo and reproducible benchmarks.

---

## 14. Operational considerations

### Observability

Log request ID, channel, predicted intent source, EDS breakdown, TAPL action, outcome score, final rank, reason codes, LLM availability, and empathy profile match.

### Governance testing

Test missing consent, high fatigue, sensitive channels (SMS, wearable, IoT), LLM failure, and unknown profiles.

### Profile lookup boundary

Keep profile lookup as a facade — CRM, CDP, loyalty platform, or feature store adapters swap without changing the ranker.

### Healthcare scope (secondary vertical)

HCP education content routing with TAPL suppress on sensitive channels — **not** clinical decision support.

---

## 15. Lessons learned

1. **LLMs should not own governance.** Use them for enrichment and explanation; keep consent, fatigue, and compliance in TAPL and rules.

2. **Explainability must be in the API contract.** Return EDS breakdowns, TAPL decisions, tier, rules fired, and explanation source — not only candidate ID and score.

3. **Merge profile history with live session context.** Static profiles and live sessions alone are both incomplete.

4. **Per-scenario memory isolation matters for demos.** `scenario_anonymous_id()` prevents cross-contamination in TKGE/EML during benchmark runs.

5. **Word-boundary rule matching prevents false empathy triggers.** Substring matches (e.g. “son” in “personalization”) caused incorrect toddler-family constraints until fixed.

6. **ML saturation requires heuristic blend.** When sklearn models saturate, blend with profile-aware heuristics so benchmark scores vary meaningfully across scenarios.

---

## 16. Scope and honest limits

1. Reference implementation on demonstration training data — not production traffic at scale.
2. ML models use synthetic/generated training data; heuristic blend when predictions saturate.
3. Healthcare: approved HCP **education routing** only; not clinical decision support.
4. Empathy: rule + profile based for travel demo; not full LLM extraction at scale.
5. Hosted demo latency includes Render cold-start overhead.

---

## 17. GitHub repository guide

**Repository:** https://github.com/jeraldcs/edta-complete-api

```text
edta-complete-api/
├── app/                    # FastAPI core — recommender, empathy, orchestration
├── config/                 # YAML — rules, TAPL, HAOE, empathy profiles
├── docs/                   # InfoQ publication, architecture PDF, benchmarks
├── static/                 # scenario-demo UI
├── tests/                  # pytest (149+)
├── scripts/                # train, benchmark, load test
└── render.yaml             # hosted demo
```

### Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# Demo: http://localhost:8000/scenario-demo
python scripts/benchmark_travel_scenarios.py
pytest
```

### Regenerate publication assets

```bash
python docs/generate_architecture_pdf.py      # 3-page PDF diagrams
python docs/generate_infoq_publication_docx.py # Word document with embedded figures
```

---

## 18. Suggested InfoQ submission package

| Artifact | Path |
|----------|------|
| **This publication document** | `docs/INFOQ_PUBLICATION_DOCUMENT.md` |
| **Word export (with diagrams)** | `docs/INFOQ_PUBLICATION_DOCUMENT.docx` |
| Narrative article draft | `docs/infoq_edta_llm_personalization_article_draft.md` |
| Architecture reference | `docs/INFOQ_ARCHITECTURE_DOCUMENT.md` |
| Positioning / cover note | `docs/INFOQ_POSITIONING.md` |
| Architecture PDF (3 pages) | `docs/edta_architecture_diagram.pdf` |
| Travel benchmark | `docs/TRAVEL_SCENARIO_SCORES.md` |
| Four-tier benchmarks | `docs/BENCHMARKS.md` |
| Live demo | https://edta-api.onrender.com/scenario-demo |
| Source code | https://github.com/jeraldcs/edta-complete-api |

---

## 19. Architecture diagrams

Three PDF pages (July 2026 codebase) — embed in article or attach to submission:

| Figure | Title | Content |
|--------|-------|---------|
| **Figure 1** | Scenario demo runtime | `scenario-demo` → `/recommend-from-scenario` → NLP → EML/TKGE → Empathy → ranker → panels |
| **Figure 2** | Codebase layer map | `app/`, `config/`, `static/`, empathy and AI module layout |
| **Figure 3** | HAOE + empathy pipeline | Four-tier routing + travel empathy constraint flow |

**Generate:** `python docs/generate_architecture_pdf.py`  
**File:** `docs/edta_architecture_diagram.pdf`

---

## Suggested author bio

Jerald Selvaraj is an enterprise architecture and digital experience technology leader focused on AI-enabled personalization, omnichannel platforms, customer experience architecture, and responsible recommendation systems. His work spans experience decisioning, marketing technology, platform modernization, and applied AI architectures for scalable digital ecosystems.

---

*Document prepared for InfoQ submission — EDTA reference implementation, Jerald Selvaraj, July 2026.*
