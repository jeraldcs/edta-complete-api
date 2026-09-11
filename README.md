# EDTA Full AI Models

**Architecture overview:** [ARCHITECTURE.md](ARCHITECTURE.md) · **Live demo:** https://edta-api.onrender.com/scenario-demo

This project extends the EDTA / EDS personalization framework with detailed AI models for all major decision categories:

1. Intent Classification Model
2. Journey Stage Classification Model
3. Trust-Aware Personalization Layer TAPL Model
4. Channel Fit Model
5. Outcome Simulation Model
6. Final Recommendation Ranker
7. Feedback Capture API
8. Web Demo with Loading Spinner
9. Optional OpenAI LLM intent enrichment and explanation generation
10. Known-user profile lookup enrichment
11. Temporal Knowledge Graph Engine TKGE
12. Experience Memory Layer EML
13. Hybrid AI Orchestration Engine HAOE
14. Self-distilling local SLM memory

## Why this version is stronger

Instead of using a single generic recommendation model, this implementation separates the decision into explainable AI modules:

```text
Customer Context
   -> Known Profile Lookup
   -> Experience Memory Layer
   -> Temporal Knowledge Graph Engine
   -> Hybrid AI Orchestration Engine
      -> Rules / ML / distilled SLM / optional LLM
   -> Intent + Journey Inference
   -> Trust / TAPL Model
   -> Channel Fit Model
   -> Outcome Simulation Engine
      -> conversion, revenue, trust, compliance, fatigue
   -> EDS Score
   -> Final Ranker
   -> Memory update + Feedback learning
   -> Recommendation
```

This is closer to the EDTA architecture because each model owns one decision responsibility. It also makes recommendations time-aware and memory-aware, so repeated exposure, trust changes, journey movement, and outcomes influence future decisions.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Train all models

Edit the single source-of-truth scenario file first:

```text
data/scenario_training_master.csv
```

Each row describes one natural-language scenario and its labels:

```text
scenario_text,domain,channel,intent,journey_stage,tapl_action,expected_candidate_id
```

When you run training, `scripts/train_all_models.py` automatically generates
100-row model-specific CSVs under `data/generated/` from that master file before
saving the model files:

- `data/generated/intent_training.csv`
- `data/generated/journey_training.csv`
- `data/generated/tapl_training.csv`
- `data/generated/outcome_training.csv`
- `data/generated/final_ranker_training.csv`

The generated files are the authoritative training inputs. The top-level
`data/*_training.csv` files are convenience copies when they are not locked by
Excel or another process.

```bash
python scripts/train_all_models.py
```

## Run API and web demo

```bash
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://localhost:8000/scenario-demo
```

(`/demo` redirects to the same page.)

Swagger:

```text
http://localhost:8000/docs
```

### Web demo (`/scenario-demo`)

Single browser demo for the full EDTA stack:

- **Recommend**, **Simulate** (`POST /simulate`), and **Experience memory** (`GET /experience-memory`) modes
- **100 training scenarios** plus free-text NLP parsing
- **Architecture panels** for TKGE, EML, HAOE, and OSE
- **Feedback capture** on the top recommendation (Click / Convert / Dismiss) — updates EML and TKGE timeline
- Training CSV rows contribute **alignment metadata only** (no forced candidate override)

## Observability and production hardening

- **`GET /live`** — liveness probe (always 200)
- **`GET /ready`** — readiness probe (503 when dependencies are degraded)
- **`GET /metrics`** — Prometheus metrics (disable with `EDTA_METRICS_ENABLED=false`)
- **Structured JSON logs** — `EDTA_LOG_FORMAT=json`, `EDTA_LOG_LEVEL=INFO`
- **Security headers** — applied on all responses; HSTS in production
- **Graceful shutdown** — uvicorn `--timeout-graceful-shutdown 30` in Docker entrypoint
- **Load test baseline** — `python scripts/load_test.py`
- **Four-tier benchmark** — `python scripts/load_test_tiers.py`

Optional OpenTelemetry tracing: install `requirements-observability.txt` and set `OTEL_ENABLED=true`.

## Deploy on Render (free)

Use the included [`render.yaml`](render.yaml) blueprint for one-click Docker deploy on Render's free tier.

Quick summary:

1. Push this repo to GitHub
2. Render → **New Blueprint** → connect repo
3. Set `EDTA_CORS_ORIGINS` to your Render URL (e.g. `https://edta-api.onrender.com`)
4. After deploy, open `https://<your-service>.onrender.com/scenario-demo`

The Docker entrypoint binds to Render's `PORT` automatically.

## Docker

Copy the environment template and start the stack:

```bash
cp .env.example .env
docker compose up --build
```

The image trains ML artifacts during build. On startup, the entrypoint retrains only if
`models/*.joblib` files are missing (for example when using a fresh volume mount).

Health check:

```text
http://localhost:8000/ready
```

Detailed status (always 200):

```text
http://localhost:8000/health
```

## Tests

```bash
pip install -r requirements-dev.txt
python scripts/train_all_models.py
pytest
```

## Security (optional)

By default, POST endpoints are open for local demo use. To require an API key:

```bash
export EDTA_API_KEY="your-secret-key"
```

Send the key on mutating requests:

```text
X-API-Key: your-secret-key
```

Configure allowed browser origins with `EDTA_CORS_ORIGINS` (comma-separated).

See `.env.example` for all runtime settings.

## Versioned API (`/v1`)

Canonical integration endpoints live under `/v1`:

```text
POST /v1/recommend
POST /v1/recommend/batch
GET  /v1/jobs/{job_id}
POST /v1/compare-outcomes
GET  /v1/context-graph
GET  /v1/events/stream
POST /v1/webhooks
```

Legacy root-level routes remain for the web demo (`POST /recommend`, etc.) but new integrations should use `/v1`.

Responses include typed `request_summary` objects with `request_id` and `api_version`. Errors return `application/problem+json` with the same `request_id` echoed in `X-Request-ID`.

Export the OpenAPI contract:

```bash
python scripts/export_openapi.py
```

## APIs

- `GET /` — health check with dependency readiness
- `GET /health` — detailed readiness probe
- `GET /demo` — redirects to `/scenario-demo`
- `GET /scenario-demo` — web demo
- `GET /scenario-examples`
- `GET /experience-memory?customer_id=...`
- `GET /experience-memory?anonymous_id=...`
- `GET /self-distillation`
- `GET /context-graph`
- `GET /orchestration-status`
- `POST /compare-outcomes`
- `POST /recommend`
- `POST /recommend-from-scenario`
- `POST /feedback`
- `POST /simulate`
- `POST /synthetic-training-data`

## Architectural enhancements

### Experience Memory Layer EML

`app/experience_memory.py` persists trust, fatigue, preferences, recommendation history, and outcomes for both `customer_id` and `anonymous_id`. Recommendation responses include before/after memory snapshots, and `/feedback` updates trust, fatigue, conversions, and revenue.

Set `EXPERIENCE_MEMORY_FILE` to change the legacy JSON migration source. Runtime memory is stored in SQLite at `EDTA_DB_PATH` (default `data/edta.db`), with identity resolution when both `customer_id` and `anonymous_id` are present.

### Temporal Knowledge Graph Engine TKGE

`app/context_graph.py` builds a **subject timeline** with timestamped temporal edges across session events, searches, transactions, recommendations, and feedback. Snapshots persist per EML subject in SQLite, merge prior outcome nodes/timeline on subsequent requests, and apply recency-weighted intent/journey inference when inputs are missing.

Each recommend call writes recommendation nodes to the graph; `/feedback` appends feedback nodes and returns an updated `context_graph` summary.

Graph export:

```text
GET /context-graph?customer_id=...&anonymous_id=...
```

### Trust-Aware Personalization Layer TAPL

Governance rules are externalized in `config/tapl_policies.yaml`. Each TAPL decision is appended to an audit log in SQLite.

### Outcome Simulation Engine OSE

The existing outcome simulation now runs before final ranking and factors in memory-backed trust, fatigue, compliance risk, channel fit, conversion probability, and revenue impact. OSE applies calibration multipliers from EML historical CTR/CVR via `ose_calibration` in API responses.

Counterfactual comparison:

```text
POST /compare-outcomes
```

### Hybrid AI Orchestration Engine HAOE

`app/orchestration.py` chooses the inference route per request:

- `rules` for explicit scenario/parser inputs or AI-disabled mode
- `ml` for local trained classifiers
- `distilled_pattern` for local distilled pattern memory (formerly labeled `slm`)
- `llm` for ambiguous rich contexts when OpenAI is enabled and the cost budget allows

HAOE tracks route telemetry in SQLite, supports an LLM circuit breaker (`HAOE_LLM_FAILURE_THRESHOLD`), and enforces a session cost budget (`HAOE_LLM_COST_BUDGET`).

Status endpoint:

```text
GET /orchestration-status
```

### Self-distilling pattern memory

`app/self_distillation.py` stores high-confidence LLM or local-ML labels into `data/distilled_slm_memory.json`. Similar future requests can use the `distilled_pattern` HAOE route to reduce API cost and latency over time.

## Optional OpenAI LLM mode

The API runs without an LLM by default. To enable OpenAI intent enrichment and
LLM-generated explanations, set `OPENAI_API_KEY` before starting the API:

```bash
export OPENAI_API_KEY="your_key"
export OPENAI_MODEL="gpt-4o-mini"
uvicorn app.main:app --reload --port 8000
```

Windows PowerShell:

```powershell
$env:OPENAI_API_KEY="your_key"
$env:OPENAI_MODEL="gpt-4o-mini"
uvicorn app.main:app --reload --port 8000
```

Then send a request with:

```json
{
  "use_ai_models": true,
  "use_llm": true,
  "use_llm_explanation": true
}
```

Example payload: `sample_requests/web_family_suv_llm.json`.

If the API key is not set or the LLM call fails, the engine automatically falls
back to the local trained AI models.

## Known-user profile lookup

When `context.customer_id` is present, the API enriches the request context from
`data/customer_profiles.json` before scoring recommendations. This file acts as
a local mock for an external CRM, CDP, loyalty, or profile service.

Example payload:

```text
sample_requests/known_user_profile_lookup.json
```

The enrichment merges profile attributes, past transactions, business context,
and consent into the live request context. The response includes lookup status in
`request_summary.profile`.

Set `PROFILE_LOOKUP_FILE` to point the lookup service at a different JSON file.
