# EDTA Security Guide

Security controls in this reference implementation and recommended production hardening.

## Authentication

When `EDTA_API_KEY` is set, mutating endpoints require:

```text
X-API-Key: <your-key>
```

When unset, POST endpoints are open for local demo use. **Always set `EDTA_API_KEY` in production.**

## CORS

Default `EDTA_CORS_ORIGINS=*` is suitable for local demos only. In production, set an explicit allowlist:

```bash
EDTA_CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

## Error disclosure

Internal exception details are hidden when:

- `EDTA_ENVIRONMENT=production` and `EDTA_EXPOSE_ERROR_DETAILS=auto`, or
- `EDTA_EXPOSE_ERROR_DETAILS=false`

API errors use `application/problem+json` with `request_id` for correlation without leaking stack traces.

## Transport and headers

The API adds:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security` when `EDTA_ENVIRONMENT=production`

Terminate TLS at your ingress/load balancer in production.

## Secrets management

- Do not commit `.env` files (see `.gitignore`)
- Inject `EDTA_API_KEY` and `OPENAI_API_KEY` via your secret manager or orchestrator secrets
- Rotate API keys periodically

## Data stores

- SQLite (`EDTA_DB_PATH`) holds EML, TKGE snapshots, TAPL audit, HAOE telemetry, webhooks, and jobs
- Feedback events also append to `FEEDBACK_STORE_FILE` JSON
- Restrict filesystem permissions on `data/` in container deployments

## Rate limiting

`EDTA_RATE_LIMIT_PER_MINUTE` applies per client IP in memory. For multi-instance deployments, enforce limits at the edge (API gateway, WAF, or shared store).

## LLM integration

When `OPENAI_API_KEY` is configured:

- Outbound calls go to OpenAI; review data residency and PII policies before sending customer context
- HAOE enforces cost budget and circuit breaker (`HAOE_LLM_COST_BUDGET`, `HAOE_LLM_FAILURE_THRESHOLD`)

## Compliance-sensitive domains

Healthcare and banking candidates carry higher `compliance_sensitivity` scores. TAPL policies in `config/tapl_policies.yaml` govern show/soften/delay/suppress actions — review and extend for your regulatory context.

## Reporting issues

Treat this package as a reference architecture. For production systems, add vulnerability scanning, dependency updates, penetration testing, and security review appropriate to your organization.
