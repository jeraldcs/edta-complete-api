"""Compare load-test results across Rules, ML, SLM, and LLM inference tiers."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_metrics import build_tier_result, extract_probe_metrics, utc_run_id

LOAD_TEST_DIR = ROOT / "sample_requests" / "load_test"

TIER_CONFIG = {
    "rules": {
        "payload": LOAD_TEST_DIR / "rules.json",
        "p95_budget_ms": 250.0,
        "expected_tier": "rules",
        "expected_candidate_id": "vehicle_upgrade_suv",
        "probe_count": 5,
    },
    "ml": {
        "payload": LOAD_TEST_DIR / "ml.json",
        "p95_budget_ms": 1500.0,
        "expected_tier": "ml",
        "expected_candidate_id": "vehicle_upgrade_suv",
        "probe_count": 5,
    },
    "slm": {
        "payload": LOAD_TEST_DIR / "slm.json",
        "p95_budget_ms": 800.0,
        "expected_tier": "slm",
        "expected_candidate_id": "vehicle_upgrade_suv",
        "probe_count": 5,
        "warm_slm": True,
    },
    "llm": {
        "payload": LOAD_TEST_DIR / "llm.json",
        "p95_budget_ms": 8000.0,
        "expected_tier": "llm",
        "expected_candidate_id": None,
        "probe_count": 5,
    },
}


def _headers(api_key: str | None) -> dict[str, str]:
    if api_key:
        return {"X-API-Key": api_key}
    return {}


def _probe_recommend(
    client: httpx.Client,
    base_url: str,
    payload: dict,
    headers: dict[str, str],
    *,
    expected_tier: str,
    expected_candidate_id: str | None,
) -> dict:
    response = client.post(f"{base_url.rstrip('/')}/recommend", json=payload, headers=headers)
    if response.status_code >= 400:
        return {
            "status": response.status_code,
            "observed_tier": None,
            "tier_match": False,
            "confidence": None,
            "fallback": True,
            "rules_fired_count": 0,
            "alignment_match": None,
            "session_cost_units": 0.0,
            "provider_cost_units": 0.0,
        }
    metrics = extract_probe_metrics(
        response.json(),
        expected_tier=expected_tier,
        expected_candidate_id=expected_candidate_id,
    )
    metrics["status"] = response.status_code
    return metrics


def _maybe_warm_slm() -> dict | None:
    if not TIER_CONFIG["slm"].get("warm_slm"):
        return None
    from scripts.warm_slm_store import warm_store

    return warm_store(limit=25)


def run_tier_load_test(
    *,
    tier_name: str,
    base_url: str,
    workers: int,
    requests_per_worker: int,
    api_key: str | None,
    warm_slm: bool,
) -> dict:
    config = TIER_CONFIG[tier_name]
    payload = json.loads(config["payload"].read_text(encoding="utf-8"))
    headers = _headers(api_key)
    recommend_url = f"{base_url.rstrip('/')}/recommend"
    latencies: list[float] = []
    errors = 0

    if tier_name == "slm" and warm_slm:
        _maybe_warm_slm()

    started_at = time.perf_counter()
    with httpx.Client(timeout=60.0, headers=headers) as client:
        warmup = client.get(f"{base_url.rstrip('/')}/health")
        if warmup.status_code >= 400:
            raise RuntimeError(f"Warmup failed for {tier_name}: HTTP {warmup.status_code}")

        def worker(_index: int) -> list[tuple[int, float]]:
            results: list[tuple[int, float]] = []
            for _ in range(requests_per_worker):
                request_started = time.perf_counter()
                response = client.post(recommend_url, json=payload)
                elapsed_ms = (time.perf_counter() - request_started) * 1000
                results.append((response.status_code, elapsed_ms))
            return results

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, index) for index in range(workers)]
            for future in as_completed(futures):
                for status, elapsed_ms in future.result():
                    latencies.append(elapsed_ms)
                    if status >= 400:
                        errors += 1

        probe_count = int(config.get("probe_count", 5))
        probes = [
            _probe_recommend(
                client,
                base_url,
                payload,
                headers,
                expected_tier=config["expected_tier"],
                expected_candidate_id=config.get("expected_candidate_id"),
            )
            for _ in range(probe_count)
        ]

    duration_seconds = max(time.perf_counter() - started_at, 0.001)
    return build_tier_result(
        tier_name=tier_name,
        latencies_ms=latencies,
        errors=errors,
        probes=probes,
        p95_budget_ms=config["p95_budget_ms"],
        expected_tier=config["expected_tier"],
        duration_seconds=duration_seconds,
        llm_enabled=bool(os.getenv("OPENAI_API_KEY")),
        slm_enabled=os.getenv("SLM_ENABLED", "true").strip().lower() in {"1", "true", "yes"},
    )


def compare_tiers(
    *,
    base_url: str,
    workers: int,
    requests_per_worker: int,
    api_key: str | None,
    tiers: list[str],
    environment: str,
    warm_slm: bool,
) -> dict:
    results = [
        run_tier_load_test(
            tier_name=tier_name,
            base_url=base_url,
            workers=workers,
            requests_per_worker=requests_per_worker,
            api_key=api_key,
            warm_slm=warm_slm,
        )
        for tier_name in tiers
    ]
    return {
        "run_id": utc_run_id(),
        "environment": environment,
        "base_url": base_url,
        "workers": workers,
        "requests_per_worker": requests_per_worker,
        "tiers": results,
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
    parser.add_argument("--environment", default=os.getenv("EDTA_BENCHMARK_ENV", "local"))
    parser.add_argument(
        "--warm-slm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Warm distilled SLM store before the SLM tier benchmark",
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    tiers = [tier.strip() for tier in args.tiers.split(",") if tier.strip()]
    unknown = [tier for tier in tiers if tier not in TIER_CONFIG]
    if unknown:
        raise SystemExit(f"Unknown tier(s): {', '.join(unknown)}")

    summary = compare_tiers(
        base_url=args.base_url,
        workers=args.workers,
        requests_per_worker=args.requests_per_worker,
        api_key=args.api_key,
        tiers=tiers,
        environment=args.environment,
        warm_slm=args.warm_slm,
    )
    rendered = json.dumps(summary, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
