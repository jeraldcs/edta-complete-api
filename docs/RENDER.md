# Deploy EDTA on Render (free tier)

This guide deploys the Dockerized EDTA API to [Render](https://render.com) using the included `render.yaml` blueprint.

## What you get

- Public HTTPS URL for the API and web demos
- Docker build (models trained during image build)
- Health checks on `/ready`
- Auto-generated `EDTA_API_KEY` (via blueprint)

Demo URLs after deploy:

```text
https://<your-service>.onrender.com/scenario-demo
https://<your-service>.onrender.com/demo            # redirects to /scenario-demo
https://<your-service>.onrender.com/docs
```

## Prerequisites

1. GitHub account with this repository pushed
2. [Render account](https://dashboard.render.com/register)

## Option A — Blueprint (recommended)

1. Open [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
2. Connect your GitHub repo
3. Render detects `render.yaml` at the repo root
4. Before deploy, set **manual** env vars in the Render UI:
   - `EDTA_CORS_ORIGINS` → `https://<your-service>.onrender.com`  
     (update after first deploy when you know the URL, then redeploy)
   - `OPENAI_API_KEY` → optional, for LLM features
   - Optional public SLM (recommended for P0): `SLM_BASE_URL`, `SLM_API_KEY`, `SLM_MODEL`  
     See **`docs/SLM_PUBLIC_HOSTING.md`** (Groq / Together — do **not** run Ollama inside free Render)
5. Click **Apply** and wait for the Docker build (~5–10 minutes; includes model training)

## Option B — Manual web service

1. **New** → **Web Service** → connect repo
2. **Runtime:** Docker
3. **Dockerfile path:** `./Dockerfile`
4. **Health check path:** `/ready`
5. **Plan:** Free
6. Add environment variables:

| Variable | Value |
|----------|--------|
| `EDTA_ENVIRONMENT` | `production` |
| `EDTA_API_KEY` | strong random secret |
| `EDTA_CORS_ORIGINS` | `https://your-app.onrender.com` |
| `EDTA_LOG_FORMAT` | `json` |
| `OPENAI_API_KEY` | optional |
| `SLM_BASE_URL` | optional — e.g. `https://api.groq.com/openai/v1` |
| `SLM_API_KEY` | optional — provider secret (never commit) |
| `SLM_MODEL` | optional — e.g. `llama-3.1-8b-instant` |

Render sets `PORT` automatically — the entrypoint uses `${PORT:-8000}`.

### Public SLM (P0) without upgrading Render

Free Render **cannot** host Ollama/HF weights (512 MB). Keep EDTA on Render and point `SLM_*` at Groq, Together, or an HF Inference Endpoint. Full steps: [`docs/SLM_PUBLIC_HOSTING.md`](SLM_PUBLIC_HOSTING.md).

## Using the API key

Mutating endpoints require the key Render generated (or you set):

```text
X-API-Key: <EDTA_API_KEY>
```

When `EDTA_EXPOSE_DEMO_API_KEY=true` (local development default), the web demo loads the key from `GET /demo-config` and attaches it automatically.

In production (`EDTA_ENVIRONMENT=production`), the API key is **not** exposed to browsers. The demo uses same-origin `/demo-api/*` proxy routes that inject the key server-side. No client configuration is required.

## Free tier limits

| Topic | Behavior |
|-------|----------|
| **Sleep** | Service spins down after ~15 minutes idle; first request may take 30–60s |
| **Disk** | Ephemeral — SQLite (`data/edta.db`) and feedback JSON reset on redeploy |
| **Memory** | 512 MB on free tier — sufficient for this reference stack |
| **Build time** | Model training at Docker build adds several minutes |

For persistent EML/feedback data, upgrade to a paid plan with a **Render Disk** mounted at `/app/data`, or migrate to an external database.

## Troubleshooting

**Build fails during model training**

- Check build logs; ensure `scripts/train_all_models.py` completes locally with `docker build .`

**Health check fails**

- Confirm `GET /ready` returns 200 when dependencies are healthy
- Increase health check start period in Render if cold start is slow

**502 after idle period**

- Normal on free tier — wait for cold start or upgrade to a paid plan to avoid sleep

**CORS errors from browser**

- Set `EDTA_CORS_ORIGINS` to your exact Render URL (no trailing slash)

## Redeploy

Push to the connected branch — Render auto-deploys if enabled.

```bash
git push origin main
```

## Local Docker parity

```bash
docker build -t edta-api .
docker run -p 8000:8000 -e EDTA_API_KEY=test -e PORT=8000 edta-api
```

Open [http://localhost:8000/scenario-demo](http://localhost:8000/scenario-demo).
