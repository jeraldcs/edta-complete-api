# Public SLM Hosting for EDTA (P0)

Keep the **EDTA demo on Render free**. Host the small language model on a **separate public OpenAI-compatible API**, then point EDTA at it with `SLM_BASE_URL`.

```text
Browser → https://edta-api.onrender.com  (EDTA: TAPL, EDS, ML, demo UI)
                │
                │  SLM_BASE_URL (HTTPS)
                ▼
         Groq / Together / HF Endpoint  (small instruct model)
```

EDTA already supports this via `SLMClient` (`api_mode: chat`, OpenAI-compatible).

---

## Recommended path: Groq (fastest for a public demo)

### Step 1 — Create a Groq account and API key

1. Go to [https://console.groq.com](https://console.groq.com) and sign up.
2. Open **API Keys** → create a key.
3. Copy the key somewhere safe (Render secrets only — never commit it).

### Step 2 — Pick a model

Use a **small, fast** chat model, for example:

| Model ID (example) | Role in EDTA |
|--------------------|--------------|
| `llama-3.1-8b-instant` | Good default for SLM parse/explain |
| `llama-3.3-70b-versatile` | Stronger, slower/costlier — optional later |

Confirm current model IDs in the Groq console (names change over time).

### Step 3 — Smoke-test Groq from your machine

```bash
curl https://api.groq.com/openai/v1/chat/completions ^
  -H "Authorization: Bearer YOUR_GROQ_API_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"llama-3.1-8b-instant\",\"messages\":[{\"role\":\"user\",\"content\":\"Say ok\"}],\"max_tokens\":16}"
```

You should get a JSON completion. If this fails, fix the key/model before touching Render.

### Step 4 — Test EDTA locally against Groq

In `.env` (local only):

```bash
SLM_ENABLED=true
SLM_BASE_URL=https://api.groq.com/openai/v1
SLM_API_KEY=YOUR_GROQ_API_KEY
SLM_MODEL=llama-3.1-8b-instant
SLM_REQUEST_TIMEOUT=20
```

Start the API:

```bash
uvicorn app.main:app --reload --port 8000
```

Force the SLM tier:

```bash
curl -X POST http://127.0.0.1:8000/v1/recommend-from-scenario ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: YOUR_LOCAL_KEY_IF_SET" ^
  -d "{\"scenario_text\":\"cust-789 booking family SUV at SFO, personalization consent true\",\"limit\":3,\"use_ai_models\":true,\"use_slm\":true,\"inference_mode\":\"slm\",\"use_llm\":false}"
```

**Pass criteria**

- HTTP 200 and recommendations returned  
- `request_summary.inference.tier` is `slm` (or shows SLM involvement in status)  
- `GET /orchestration-status` or SLM status shows remote success (not only pattern-only)  
- Consent/fatigue scenarios still change TAPL (`generic_fallback` / `delay`)

### Step 5 — Configure Render (public demo)

In [Render Dashboard](https://dashboard.render.com) → service **edta-api** → **Environment**:

| Key | Value | Notes |
|-----|--------|--------|
| `SLM_ENABLED` | `true` | Already in blueprint |
| `SLM_BASE_URL` | `https://api.groq.com/openai/v1` | No trailing path beyond `/v1` |
| `SLM_API_KEY` | *(your Groq key)* | Mark as secret |
| `SLM_MODEL` | `llama-3.1-8b-instant` | Must match Groq model id |
| `SLM_REQUEST_TIMEOUT` | `20` | Optional; cold paths need headroom |

Do **not** put the API key in `render.yaml` or git.

Redeploy the service (manual deploy or push a no-op if auto-deploy is on).

### Step 6 — Public smoke test after deploy

1. Open https://edta-api.onrender.com/scenario-demo (allow cold start).  
2. Run **Family loyalty** → Recommend.  
3. Open **Technical details** / architecture panels — confirm recommendations still work.  
4. Run **No consent** and **High fatigue** — TAPL must still govern.  
5. Optional API check:

```bash
curl -X POST https://edta-api.onrender.com/v1/recommend-from-scenario ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: YOUR_RENDER_EDTA_API_KEY" ^
  -d "{\"scenario_text\":\"family SUV airport rental consent true\",\"limit\":2,\"inference_mode\":\"slm\",\"use_llm\":false}"
```

### Step 7 — Demo script for talks

1. Show default loyalty scenario (full stack).  
2. Say: “SLM tier can call a hosted small model; TAPL still owns consent.”  
3. Toggle **No consent** → fallback.  
4. Mention Render hosts EDTA; Groq hosts the small model only.

---

## Alternate path: Together AI

Same steps; different env values:

| Key | Example |
|-----|---------|
| `SLM_BASE_URL` | `https://api.together.xyz/v1` |
| `SLM_API_KEY` | Together API key |
| `SLM_MODEL` | e.g. `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` |

Confirm exact model IDs in the Together model list.

Smoke-test:

```bash
curl https://api.together.xyz/v1/chat/completions ^
  -H "Authorization: Bearer YOUR_TOGETHER_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo\",\"messages\":[{\"role\":\"user\",\"content\":\"Say ok\"}],\"max_tokens\":16}"
```

---

## Alternate path: Hugging Face Inference Endpoint

Use when you want an explicit HF-deployed model:

1. Create an **Inference Endpoint** for a small instruct model (CPU or small GPU).  
2. Enable OpenAI-compatible API if offered, or use a gateway that exposes `/v1/chat/completions`.  
3. Set:

```bash
SLM_BASE_URL=https://YOUR_ENDPOINT_HOST/v1
SLM_API_KEY=YOUR_HF_TOKEN
SLM_MODEL=YOUR_DEPLOYED_MODEL_NAME
```

HF free serverless Inference can be flaky for a conference demo — prefer Endpoint or Groq/Together for reliability.

---

## What stays on Render (do not move)

- TAPL policies and audit  
- EDS / OSE / final ranker  
- EML / TKGE  
- Scenario demo UI and `/demo-api` proxy  
- API key auth  

The remote host only supplies **SLM chat completions**.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Demo works but never uses remote SLM | Confirm `SLM_BASE_URL` set; restart/redeploy; try `inference_mode: slm` |
| 401 from SLM provider | Wrong `SLM_API_KEY` or missing `Authorization` |
| 404 model | `SLM_MODEL` id does not match provider catalog |
| Timeouts on Render | Raise `SLM_REQUEST_TIMEOUT` to 20–30; pick a faster model |
| TAPL broken after SLM enable | Regression: re-run No consent / High fatigue chips — SLM must not bypass TAPL |
| Rate limits | Groq/Together free tiers have limits; cache/distill later (P3) |

---

## Security checklist

- [ ] API keys only in Render env / local `.env` (gitignored)  
- [ ] Do not log full prompts with PII in production  
- [ ] Keep `EDTA_API_KEY` set on Render  
- [ ] Prefer small models; do not send unnecessary profile fields to the SLM host  

---

## Success definition (P0 done)

- Public demo URL still works without local laptop.  
- With `SLM_BASE_URL` set, SLM tier can call the hosted model.  
- Without `SLM_BASE_URL`, EDTA still works (pattern-only SLM fallback).  
- Governance demos (consent / fatigue) still behave correctly.
