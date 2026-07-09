"""Compare load-test results across Rules, ML, SLM, and LLM inference tiers."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
LOAD_TEST_DIR = ROOT / "sample_requests" / "load_test"

TIER_CONFIG = {
    "rules": {
        "payload": LOAD_TEST_DIR / "rules.json",
        "p95_budget_ms": 250.0,
        "expected_tier": "rules",
    },
    "ml": {
        "payload": LOAD_TEST_DIR / "ml.json",
        "p95_budget_ms": 1500.0,
        "expected_tier": "ml",
    },
    "slm": {
        "payload": LOAD_TEST_DIR / "slm.json",
        "p95_budget_ms": 800.0,
        "expected_tier": "slm",
    },
    "llm": {
        "payload": LOAD_TEST_DIR / "llm.json",
        "p95_budget_ms": 8000.0,
        "expected_tier": "llm",
    },
}


def _headers(api_key: str | None) -> dict[str, str]:
    if api_key:
        return {"X-API-Key": api_key}
    return {}


def _sample_tier(client: httpx.Client, base_url: str, payload: dict, headers: dict[str, str]) -> dict:
    response = client.post(f"{base_url.rstrip('/')}/recommend", json=payload, headers=headers)
    if response.status_code >= 400:
        return {"status": response.status_code, "tier": None, "intent_source": None}
    body = response.json()
    top = (body.get("recommendations") or [{}])[0]
    ai = top.get("ai_score") or {}
    orchestration = ai.get("orchestration") or {}
    intent = ai.get("intent") or {}
    return {
        "status": response.status_code,
        "tier": orchestration.get("tier"),
        "intent_source": intent.get("source"),
    }


def run_tier_load_test(
    *,
    tier_name: str,
    base_url: str,
    workers: int,
    requests_per_worker: int,
    api_key: str | None,
) -> dict:
    config = TIER_CONFIG[tier_name]
    payload = json.loads(config["payload"].read_text(encoding="utf-8"))
    headers = _headers(api_key)
    recommend_url = f"{base_url.rstrip('/')}/recommend"
    latencies: list[float] = []
    errors = 0
    tier_samples: list[str | None] = []
    source_samples: list[str | None] = []

    with httpx.Client(timeout=60.0, headers=headers) as client:
        warmup = client.get(f"{base_url.rstrip('/')}/health")
        if warmup.status_code >= 400:
            raise RuntimeError(f"Warmup failed for {tier_name}: HTTP {warmup.status_code}")

        def worker(_index: int) -> list[tuple[int, float]]:
            results: list[tuple[int, float]] = []
            for _ in range(requests_per_worker):
                started = time.perf_counter()
                response = client.post(recommend_url, json=payload)
                elapsed_ms = (time.perf_counter() - started) * 1000
                results.append((response.status_code, elapsed_ms))
            return results

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, index) for index in range(workers)]
            for future in as_completed(futures):
                for status, elapsed_ms in future.result():
                    latencies.append(elapsed_ms)
                    if status >= 400:
                        errors += 1

        for _ in range(min(5, max(1, workers))):
            sample = _sample_tier(client, base_url, payload, headers)
            tier_samples.append(sample.get("tier"))
            source_samples.append(sample.get("intent_source"))

    latencies.sort()
    p95_index = max(0, int(len(latencies) * 0.95) - 1)
    p95_ms = latencies[p95_index] if latencies else 0.0
    observed_tier = next((tier for tier in tier_samples if tier), None)
    return {
        "tier": tier_name,
        "requests": len(latencies),
        "errors": errors,
        "p50_ms": round(statistics.median(latencies), 2) if latencies else 0.0,
        "p95_ms": round(p95_ms, 2),
        "max_ms": round(max(latencies), 2) if latencies else 0.0,
        "p95_budget_ms": config["p95_budget_ms"],
        "expected_tier": config["expected_tier"],
        "observed_tier": observed_tier,
        "intent_sources": sorted({source for source in source_samples if source}),
        "passed": errors == 0 and p95_ms <= config["p95_budget_ms"],
        "llm_enabled": bool(os.getenv("OPENAI_API_KEY")),
        "slm_enabled": os.getenv("SLM_ENABLED", "true").strip().lower() in {"1", "true", "yes"},
    }


def compare_tiers(
    *,
    base_url: str,
    workers: int,
    requests_per_worker: int,
    api_key: str | None,
    tiers: list[str],
) -> dict:
    results = [
        run_tier_load_test(
            tier_name=tier_name,
            base_url=base_url,
            workers=workers,
            requests_per_worker=requests_per_worker,
            api_key=api_key,
        )
        for tier_name in tiers
    ]
    return {
        "base_url": base_url,
        "workers": workers,
        "requests_per_worker": requests_per_worker,
        "results": results,
        "passed": all(item["passed"] for item in results),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare EDTA load across inference tiers.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--requests-per-worker", type=int, default=5)
    parser.add_argument("--api-key", default=os.getenv("EDTA_API_KEY"))
    parser.add_argument(
        "--tiers",
        default="rules,ml,slm,llm",
        help="Comma-separated tier names to benchmark",
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    tiers = [tier.strip() for tier in args.tiers.split(",") if tier.strip()]
    summary = compare_tiers(
        base_url=args.base_url,
        workers=args.workers,
        requests_per_worker=args.requests_per_worker,
        api_key=args.api_key,
        tiers=tiers,
    )
    rendered = json.dumps(summary, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
