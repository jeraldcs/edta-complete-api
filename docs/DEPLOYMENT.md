# EDTA Deployment Guide

This guide covers production deployment, health probes, observability, and baseline load testing for the EDTA reference API.

## Runtime requirements

- Python 3.12+
- Trained model artifacts in `models/*.joblib` (built at Docker image build or via `python scripts/train_all_models.py`)
- Writable SQLite database at `EDTA_DB_PATH` (default `data/edta.db`)

## Health probes

| Endpoint | Purpose | Success |
|----------|---------|---------|
| `GET /live` | Liveness — process is running | Always `200` |
| `GET /ready` | Readiness — dependencies OK | `200` when ready, `503` when degraded |
| `GET /health` | Detailed status (backward compatible) | Always `200` with `ready` flag |

Configure orchestrators to:

- Use **`/live`** for liveness probes
- Use **`/ready`** for readiness and load-balancer membership
- Remove pods/instances from rotation when `/ready` returns `503`

## Observability

### Structured logs

Set:

```bash
EDTA_LOG_LEVEL=INFO
EDTA_LOG_FORMAT=json
EDTA_ENVIRONMENT=production
```

Logs include `request_id`, HTTP access events (`event=http_request`), and recommendation audit events (`event=recommendation.audit`).

### Prometheus metrics

Enable metrics (default on):

```bash
EDTA_METRICS_ENABLED=true
```

Scrape `GET /metrics`:

- `edta_http_requests_total{method,route,status}`
- `edta_http_request_duration_seconds{method,route}`
- `edta_recommendations_total{channel,tapl_action}`
- `edta_feedback_events_total{event_type,converted}`

### OpenTelemetry (optional)

Install optional packages:

```bash
pip install -r requirements-observability.txt
```

Enable:

```bash
OTEL_ENABLED=true
OTEL_SERVICE_NAME=edta-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Compose uses `/ready` for health checks and sets CPU/memory limits. Uvicorn graceful shutdown timeout is 30 seconds.

## Production checklist

1. Set `EDTA_ENVIRONMENT=production`
2. Set `EDTA_API_KEY` and restrict `EDTA_CORS_ORIGINS`
3. Set `EDTA_EXPOSE_ERROR_DETAILS=auto` (default) or `false`
4. Mount persistent volumes for `data/` and `models/`
5. Scrape `/metrics` with Prometheus
6. Ship JSON logs to your log aggregator
7. Point readiness probes at `/ready`
8. Back up `data/edta.db` on a schedule

## Load testing baseline

Run against a live server:

```bash
uvicorn app.main:app --port 8000
python scripts/load_test.py --workers 4 --requests-per-worker 10 --p95-budget-ms 3000
```

The script alternates `GET /health` and `POST /recommend`, reports p50/p95 latency, and exits non-zero if errors occur or p95 exceeds the budget.

## Scaling notes

- Rate limiting is **in-memory per instance** — use an edge proxy or Redis-backed limiter for multi-replica deployments
- SSE/webhook event bus is **in-process** — treat as demo/integration pattern, not durable messaging
- For horizontal scale, run stateless API replicas with shared SQLite replaced by a managed database in production deployments

## Render

See [RENDER.md](RENDER.md) for free-tier deployment with the root `render.yaml` blueprint.
