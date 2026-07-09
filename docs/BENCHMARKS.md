# EDTA Four-Tier Benchmarks

This document describes how to benchmark the public inference tiers:

**Rules → SLM → ML → LLM**

Each tier is tested in isolation using dedicated payloads under `sample_requests/load_test/` and `inference_mode` force-routing.

## Quick start

Start the API locally:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Run the four-tier comparison:

```bash
python scripts/load_test_tiers.py \
  --base-url http://127.0.0.1:8000 \
  --workers 4 \
  --requests-per-worker 5 \
  --output data/generated/benchmark_tiers.json
```

Generate a markdown summary:

```bash
python scripts/load_test_report.py data/generated/benchmark_tiers.json \
  --output docs/BENCHMARK_REPORT.md
```

## What gets measured

| Metric | Meaning |
| --- | --- |
| **p50 / p95 latency** | End-to-end `/recommend` latency per tier |
| **Throughput (rps)** | Total requests divided by tier run duration |
| **Error rate** | HTTP 4xx/5xx during the load phase |
| **Fallback rate** | Probe requests where inference used a fallback path (`fallback_from`, `rules_fallback`, etc.) |
| **Tier match rate** | Probe requests where `request_summary.inference.tier` matches the forced tier |
| **Avg confidence** | Mean unified inference confidence from probe requests |
| **Alignment top-1** | Demo accuracy proxy: top recommendation matches expected training candidate |
| **Rules fired avg** | Average fired-rule count (Rules tier explainability) |
| **Cost units** | HAOE session cost + provider telemetry cost estimates |

## Benchmark scenarios

| ID | Tier | Payload | Expected behavior |
| --- | --- | --- | --- |
| B1 | Rules | `rules.json` | Structured SUV rental context, `use_ai_models: false`, top-1 aligns with `vehicle_upgrade_suv` |
| B2 | ML | `ml.json` | Catalog-aligned web context, forced `inference_mode: ml` |
| B3 | SLM | `slm.json` | Same structured context with distilled/SLM path; store warmed before run |
| B4 | LLM | `llm.json` | Sparse ambiguous context with `use_llm: true` (requires `OPENAI_API_KEY`) |

SLM benchmarks call `scripts/warm_slm_store.py` automatically unless `--no-warm-slm` is passed.

## Expected results (local Docker / dev)

These are **demo targets**, not production SLOs:

| Tier | p95 target | Throughput | Alignment top-1 | Fallback rate | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| Rules | < 50 ms | Highest | ≥ 0.80 | ~0 | Deterministic YAML + EDS |
| SLM | < 100 ms | High | ≥ 0.80 | Low | Distilled memory + optional remote endpoint |
| ML | < 300 ms | Medium | ≥ 0.80 | Low | sklearn classifiers on warmed catalog |
| LLM | < 3–8 s | Low | n/a | Medium–high | Depends on provider latency and API key |

On **Render free tier**, expect higher cold-start latency on the first request. Run a warm-up health check and note cold start separately in `EDTA_BENCHMARK_ENV=render`.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `EDTA_API_KEY` | Optional API auth for load tests |
| `EDTA_BENCHMARK_ENV` | Label in JSON output (`local`, `docker`, `render`) |
| `OPENAI_API_KEY` | Required for LLM tier benchmark pass |
| `SLM_BASE_URL` | Optional remote SLM endpoint (Ollama, etc.) |
| `SLM_ENABLED` | Defaults to `true`; pattern-only SLM works without external API |

## CI and contract tests

Unit tests validate payload shape and probe metric extraction without a running server:

```bash
pytest tests/test_load_test_contracts.py -q
```

ML offline evaluation is published separately via `scripts/evaluate_ml_models.py` (see CI artifact `ml-eval-summary`).

## Interpreting accuracy

The **alignment top-1** metric compares the top recommendation against `expected_candidate_id` from the training CSV for structured SUV rental scenarios. It is a **demo proxy** for repeatability, not a claim of production accuracy.

For scenario-demo free text, alignment is metadata-only and does not force candidate selection.

## One-command workflow

```bash
python scripts/load_test_tiers.py --output data/generated/benchmark_tiers.json && \
python scripts/load_test_report.py data/generated/benchmark_tiers.json --output docs/BENCHMARK_REPORT.md
```

Review `data/generated/benchmark_tiers.json` for machine-readable results and `docs/BENCHMARK_REPORT.md` for the comparison table.
