# Empathy Engine — Changes Roadmap

This document lists **what must change in EDTA** to support:

1. **Hidden Needs Persona Mapping** — infer implicit constraints from scenario text  
2. **API Enrichment** — weather, terrain/route elevation  
3. **Cost-to-Drive (TCO) Calculator** — fuel/EV total trip cost  
4. **Empathy Engine Simulator** — interactive demo UI  

Aligned with existing EDTA pillars: accuracy, memory/impact, trust/compliance, architecture-native context, outcome/revenue simulation.

---

## Current state (what you already have)

| Area | Today |
|------|--------|
| Scenario parsing | `ScenarioNLPParser` — keywords + optional LLM |
| Context | `CustomerContext.profile_attributes`, `business_context`, `channel_context` |
| Ranking | EDS + semantic + ML ranker + TAPL + outcome simulation |
| Catalog | Generic travel/hotel candidates; **no vehicle specs** (MPG, AWD, ISOFIX, etc.) |
| External APIs | None (LLM/SLM optional only) |
| Demo | `/scenario-demo` — recommend / simulate / memory |

**Gap:** Empathy features need a **constraint extraction layer**, **enriched trip model**, **vehicle attribute catalog**, **external data adapters**, and **TCO economics** wired into ranking and explanation.

---

## Target pipeline (after changes)

```text
Scenario text
  -> Hidden Needs Parser (persona + implicit constraints)
  -> Trip Model Extractor (route, dates, passengers, destination)
  -> External Enrichment (weather, elevation, gas prices)  [optional APIs]
  -> Constraint Feasibility + Candidate Scoring (catalog specs)
  -> TCO Engine (fuel/EV vs daily rate)
  -> Existing EDTA stack (TKGE, EML, HAOE, TAPL, OSE, rank)
  -> Empathy explanation (why this matches hidden needs + weather + TCO)
  -> Empathy Simulator UI
```

---

## 1. Hidden Needs Persona Mapping

### What it does

Reads between the lines of free text and produces **implicit constraints** that standard filters miss.

| User says | Standard filter | Empathy output |
|-----------|-----------------|----------------|
| 80-year-old grandmother + toddler | Sedan / SUV | Low step-in, ISOFIX, rear legroom |
| PCH road trip, two partners | Economy | Panoramic/convertible, sound, handling |
| College dorm move, 3 hours | Midsize SUV | Fold-flat seats, wide tailgate, cargo volume |

### Changes required

#### A. New module: `app/empathy/hidden_needs.py`

- **`HiddenNeedsProfile`** (Pydantic model):
  - `persona_tags`: e.g. `elderly_passenger`, `toddler`, `couple_leisure`, `college_move`
  - `implicit_constraints`: list of `{constraint_id, weight, reason, source}`
  - `confidence`: float
  - `evidence_phrases`: list[str]

- **`HiddenNeedsExtractor`**:
  - **Tier 1:** Rule/keyword patterns (YAML) — fast, auditable  
  - **Tier 2:** SLM/LLM structured prompt — `parse_hidden_needs_prompt()`  
  - Output merged into `CustomerContext.business_context["empathy_constraints"]`

#### B. Config: `config/empathy/hidden_needs.yaml`

```yaml
patterns:
  elderly_mobility:
    triggers: [grandmother, grandmother's, 80-year-old, wheelchair, mobility]
    constraints: [low_step_in, wide_door_opening, easy_entry]
  toddler_family:
    triggers: [toddler, infant, car seat, isofix]
    constraints: [isofix_anchors, rear_legroom, suv_preference]
  scenic_couple:
    triggers: [pacific coast, road trip, partner, scenic]
    constraints: [panoramic_roof, convertible_option, premium_audio, handling]
  dorm_move:
    triggers: [college, dorm, moving, haul]
    constraints: [fold_flat_seats, wide_tailgate, cargo_volume]
```

#### C. Catalog enrichment: vehicle **attributes** (not just tags)

Extend `RecommendationCandidate` or add **`VehicleSpec`** sidecar in `data/catalog/vehicles.json`:

| Field | Used for |
|-------|----------|
| `step_in_height_cm` | Elderly mobility |
| `isofix_count` | Toddler |
| `rear_legroom_score` | Family |
| `has_panoramic_roof` / `convertible` | Scenic couple |
| `cargo_volume_cu_ft` | Dorm move |
| `mpg_highway`, `fuel_type`, `awd` | TCO + weather (later) |

Add candidates or variants: `compact_suv`, `awd_suv`, `hybrid_midsize`, `convertible_premium`, etc.

#### D. Scoring: `app/empathy/constraint_matcher.py`

- Score each candidate: **constraint satisfaction** (0–1)  
- Blend into rank:  
  `final_hybrid_score += empathy_weight * constraint_match_score`  
- Expose in API: `request_summary.empathy = { profile, matches, constraint_gaps }`

#### E. Prompts: `app/llm/prompt_templates.py`

- Add `hidden_needs_prompt(scenario_text) -> JSON schema`  
- Same schema for LLM and SLM tiers (Phase 3 pattern)

#### F. Training data

- Add columns to `data/scenario_training_master.csv` or new `data/empathy_scenarios.csv`:
  - `implicit_constraints` (JSON)
  - `expected_vehicle_id`
- Examples: the three rows in your spec + 20–30 more

#### G. Tests

- `tests/test_hidden_needs.py` — three canonical scenarios → expected constraints  
- Accuracy metric: **constraint recall** on held-out empathy scenarios  

---

## 2. API Enrichment (Weather, Terrain, Route)

### What it does

Before ranking, enrich trip context with **real-time or forecast** data:

- **Route/elevation:** Denver trip → steep climb → boost AWD / engine power  
- **Weather:** Snow/rain forecast → boost safety-rated AWD + explanation note  

### Changes required

#### A. New module: `app/enrichment/` (adapter pattern)

| File | Role |
|------|------|
| `contracts.py` | `TripModel`, `EnrichmentBundle`, `WeatherSnapshot`, `RouteProfile` |
| `trip_extractor.py` | Parse origin/destination/dates/distance from scenario or explicit fields |
| `weather_provider.py` | OpenWeather / NOAA adapter (env-gated) |
| `route_provider.py` | OpenRouteService / Google Elevation / Mapbox adapter |
| `enrichment_service.py` | Orchestrate calls, cache, fallback when API keys missing |

#### B. Config: `config/enrichment_providers.yaml`

```yaml
weather:
  driver: openweather
  enabled_env: WEATHER_API_KEY
  cache_ttl_seconds: 3600
route:
  driver: openrouteservice
  enabled_env: ROUTE_API_KEY
  elevation_threshold_ft: 5000
fallback:
  mode: rules_only  # demo works without keys
```

#### C. Context wiring

Store enrichment in:

```python
context.business_context["trip"] = {
  "destination": "Denver, CO",
  "distance_miles": 500,
  "rental_start": "2026-08-01",
  "rental_end": "2026-08-05",
}
context.business_context["enrichment"] = {
  "weather": {"forecast": "snow", "wind_mph": 25, "source": "openweather"},
  "route": {"max_elevation_ft": 7200, "steep_grade": true, "source": "ors"},
  "derived_constraints": ["awd_preferred", "winter_tires_recommended"],
}
```

#### D. Ranking rules

- `config/rules/packs/travel_empathy.yaml`:
  - IF `steep_grade` AND NOT candidate.awd → penalty  
  - IF `forecast in [snow, heavy_rain]` → boost AWD candidates  
- Explanation template: *"We prioritized AWD because snow is forecast along your route."*

#### E. Infrastructure

- **Caching:** SQLite or Redis-lite in `data/enrichment_cache.db` (Render-friendly)  
- **Rate limits:** respect API quotas; HAOE cost units for external calls  
- **Secrets:** `WEATHER_API_KEY`, `ROUTE_API_KEY` in Render env (optional)  
- **Graceful degrade:** demo works without keys using **stub enrichment** from keywords ("Denver", "snow")

#### F. API surface

- Optional request fields on `ScenarioRecommendationRequest`:
  - `destination`, `route_miles`, `rental_dates` (override parser)
- Response: `request_summary.enrichment` + `recommendation.enrichment_notes[]`

#### G. Tests

- Mock providers in `tests/test_enrichment.py`  
- Contract tests: Denver scenario → `awd_preferred` without live API  

---

## 3. Cost-to-Drive (TCO) Calculator

### What it does

Compare **daily rate + estimated fuel** vs hybrid/EV uplift:

> *"Hybrid costs $10/day more but saves $45 fuel on 500 miles → $35 net savings."*

### Changes required

#### A. New module: `app/empathy/tco_calculator.py`

**Inputs:**

- `route_miles` (from trip model)  
- `rental_days`  
- `daily_rate` per candidate (catalog)  
- `mpg_city` / `mpg_highway` or `kwh_per_mile`  
- Live **gas price** (API or config default by region)  

**Outputs:** `TCOBreakdown`:

```python
{
  "daily_rate_total": 120.0,
  "estimated_fuel_cost": 85.0,
  "estimated_ev_charge_cost": 22.0,
  "total_trip_cost": 205.0,
  "vs_baseline_candidate_id": "economy_compact",
  "net_savings": 35.0,
  "recommendation_pitch": "While this hybrid costs $10/day more..."
}
```

#### B. Catalog fields (per vehicle candidate)

- `daily_rate_usd`  
- `mpg_highway`, `mpg_city`  
- `fuel_type`: gas | hybrid | ev  
- `tank_gallons` or `battery_kwh`  

#### C. Gas price provider

- `app/enrichment/gas_price_provider.py` — e.g. collectAPI / AAA stub / static YAML by state  
- Env: `GAS_PRICE_API_KEY` (optional)

#### D. Ranking integration

- OSE already has `revenue_impact` — extend with **`tco_adjusted_value`**  
- Rank boost when TCO favors higher-tier vehicle despite higher daily rate  
- TAPL: ensure upsell doesn’t violate trust/fatigue on price-sensitive personas  

#### E. Explanation

- Extend `ExplanationRouter` payload with TCO pitch  
- SLM/rules template for side-by-side comparison  

#### F. Demo / API

- `request_summary.tco` on scenario responses  
- Per-recommendation: `tco_comparison` vs baseline  

#### G. Tests

- Fixed MPG + gas price → deterministic $45 fuel savings example  
- Unit tests for edge cases (EV, 0 miles, missing MPG)  

---

## 4. Empathy Engine Simulator (UI)

### What it does

Interactive page: user edits trip details → sees hidden constraints, enrichment, TCO, and tailored pitch update live.

### Changes required

#### A. New route + static assets

| Asset | Purpose |
|-------|---------|
| `GET /empathy-demo` | Simulator page |
| `static/empathy_app.js` | Form + live API calls |
| `static/empathy.css` | Layout |
| Link from `/scenario-demo` | "Try Empathy Engine" |

#### B. API endpoint (optional dedicated)

- `POST /empathy/simulate` — returns full bundle without full recommend, OR  
- Reuse `POST /recommend-from-scenario` with `include_empathy: true`  

Response sections:

1. **Hidden needs** — persona + constraints  
2. **Enrichment** — weather + elevation cards  
3. **TCO** — side-by-side table  
4. **Recommendation** — vehicle + empathy pitch  
5. **Architecture panels** — reuse `demo-shared.js` for TKGE/EML/TAPL  

#### C. Example scenarios (prefill buttons)

- Grandmother + toddler  
- PCH couple road trip  
- College dorm move  
- Denver winter drive (enrichment + AWD story)  

#### D. `demo-config` / CORS

- Already on Render; no change if same origin  

---

## Cross-cutting changes

### Models (`app/models.py`)

- `HiddenNeedsProfile`, `EnrichmentBundle`, `TCOBreakdown`  
- Extend `RankedRecommendation` with optional `empathy_match`, `tco`, `enrichment_notes`  

### API schemas (`app/api/schemas.py`)

- `request_summary.empathy`, `.enrichment`, `.tco`  
- `ScenarioRecommendationRequest`: optional trip overrides  

### Recommender (`app/recommender.py`)

Insert **before** candidate loop:

```text
hidden_needs = HiddenNeedsExtractor.parse(context_text)
trip = TripExtractor.parse(context_text, context)
enrichment = EnrichmentService.enrich(trip)  # no-op if no keys
context = merge_into_context(context, hidden_needs, trip, enrichment)
# ... existing rank loop ...
tco = TCOCalculator.compare(top_candidates, trip, enrichment)
```

### Rules / ML

- Rules: empathy constraint boosts/penalties  
- ML (later): train ranker with empathy + enrichment features  

### Observability

- Log enrichment provider latency, cache hits, API failures  
- `provider_telemetry` pattern for weather/route/gas APIs  

### Documentation

- `docs/EMPATHY_ENGINE.md` — user-facing  
- Article section: **"Empathy constraints beyond segmentation"**
- **Implicit need inference + enriched context ranking**  

---

## Phased implementation roadmap

### Phase 6A — Hidden Needs (4 weeks) — **P0**

| Task | Output |
|------|--------|
| 6A.1 | `HiddenNeedsProfile` + YAML patterns |
| 6A.2 | LLM/SLM prompt + fallback parser |
| 6A.3 | `data/catalog/vehicles.json` with specs |
| 6A.4 | `constraint_matcher.py` + rank blend |
| 6A.5 | 30 empathy scenarios + tests |
| 6A.6 | API fields in `request_summary.empathy` |

**Exit:** Three canonical examples match your table in API response.

---

### Phase 6B — TCO Calculator (3 weeks) — **P0**

| Task | Output |
|------|--------|
| 6B.1 | `tco_calculator.py` |
| 6B.2 | Catalog daily_rate + MPG fields |
| 6B.3 | Static gas price YAML (API optional) |
| 6B.4 | TCO in response + explanation pitch |
| 6B.5 | Unit tests (500-mile hybrid savings) |

**Exit:** Hybrid vs compact shows $35 net savings narrative.

---

### Phase 6C — API Enrichment (4 weeks) — **P1**

| Task | Output |
|------|--------|
| 6C.1 | `enrichment_service.py` + provider interfaces |
| 6C.2 | Weather + route mock providers |
| 6C.3 | Live adapters (OpenWeather, ORS) behind env flags |
| 6C.4 | Rules: AWD boost + explanation |
| 6C.5 | SQLite enrichment cache |
| 6C.6 | Denver + snow demo scenario |

**Exit:** Enrichment block in API; demo works offline with stubs.

---

### Phase 6D — Empathy Simulator UI (3 weeks) — **P1**

| Task | Output |
|------|--------|
| 6D.1 | `/empathy-demo` page |
| 6D.2 | Prefill scenarios + editable trip fields |
| 6D.3 | Live panels: hidden needs / weather / TCO / pitch |
| 6D.4 | Link from scenario-demo hero |

**Exit:** Public URL for live demos.

---

### Phase 7 — Accuracy & evidence (parallel) — **P1**

| Task | Output |
|------|--------|
| 7.1 | `evaluate_empathy_accuracy.py` — constraint recall + top-1 vehicle |
| 7.2 | Compare vs standard filter baseline |
| 7.3 | Benchmark exhibit JSON |

---

## Uniqueness / differentiation angle

| Generic recommender | Empathy Engine + EDTA |
|---------------------|------------------------|
| Filter on explicit search params | **Implicit constraint inference** |
| Static catalog match | **Live weather/route enrichment** |
| Lowest daily rate | **TCO-aware upsell** (hybrid/EV) |
| Segment-based offers | **Architecture-native** context pipeline |
| Black-box rank | **Auditable** rules + empathy evidence in API |

**Suggested contribution name:** **Empathy Engine** — governed implicit-need extraction with enrichment-aware, TCO-adjusted ranking inside EDTA.

---

## Dependencies & risks

| Risk | Mitigation |
|------|------------|
| External API cost / keys | Stubs + cache; optional env flags |
| LLM hallucinated constraints | Rules YAML validate + confidence threshold |
| Render latency | Cache enrichment; async optional |
| Healthcare scope creep | Keep empathy Phase 6 **travel-first**; healthcare uses TAPL only |
| Catalog too small | Start with 8–12 vehicle SKUs with full specs |

---

## File checklist (new / modified)

**New**

- `app/empathy/hidden_needs.py`  
- `app/empathy/constraint_matcher.py`  
- `app/empathy/tco_calculator.py`  
- `app/enrichment/enrichment_service.py`  
- `app/enrichment/weather_provider.py`  
- `app/enrichment/route_provider.py`  
- `app/enrichment/gas_price_provider.py`  
- `config/empathy/hidden_needs.yaml`  
- `config/enrichment_providers.yaml`  
- `data/catalog/vehicles.json`  
- `data/empathy_scenarios.csv`  
- `static/empathy_app.js`  
- `tests/test_hidden_needs.py`  
- `tests/test_tco_calculator.py`  
- `tests/test_enrichment.py`  

**Modified**

- `app/scenario_nlp.py` — call hidden needs extractor  
- `app/recommender.py` — empathy + TCO in rank loop  
- `app/catalog.py` — load vehicle specs  
- `app/models.py`, `app/api/schemas.py`  
- `app/llm/prompt_templates.py`  
- `app/services/recommendation_handlers.py`  
- `static/scenario_demo.html` — link to empathy demo  
- `docs/edta_llm_personalization_article_draft.md` — new section  
- `render.yaml` — optional API key env vars  

---

## Suggested implementation order

```text
1. Vehicle catalog + hidden needs YAML + constraint matcher     (demo value fast)
2. TCO calculator + explanation pitch                           (your hybrid $35 story)
3. Empathy simulator UI (mock enrichment)                       (live demo)
4. Live weather/route/gas APIs + cache                          (production polish)
5. Accuracy eval vs standard filters                            (evidence)
```

---

*Version 1.0 — aligns with EDTA Phases 0–5 and Phase 6+ roadmap.*
