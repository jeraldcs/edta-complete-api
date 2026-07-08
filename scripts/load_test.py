"""Lightweight HTTP load test for EDTA API baseline checks."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAYLOAD = json.loads(
    (ROOT / "sample_requests" / "web_family_suv.json").read_text(encoding="utf-8")
)


def _request(client: httpx.Client, method: str, url: str, payload: dict | None = None) -> tuple[int, float]:
    started = time.perf_counter()
    if method == "GET":
        response = client.get(url)
    else:
        response = client.post(url, json=payload)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return response.status_code, elapsed_ms


def run_load_test(
    *,
    base_url: str,
    workers: int,
    requests_per_worker: int,
    p95_budget_ms: float,
) -> dict:
    health_url = f"{base_url.rstrip('/')}/health"
    recommend_url = f"{base_url.rstrip('/')}/recommend"
    latencies: list[float] = []
    errors = 0

    with httpx.Client(timeout=30.0) as client:
        warmup_status, _ = _request(client, "GET", health_url)
        if warmup_status != 200:
            raise RuntimeError(f"Warmup GET /health failed with status {warmup_status}")

        def worker(_index: int) -> list[tuple[int, float]]:
            results: list[tuple[int, float]] = []
            for _ in range(requests_per_worker):
                if len(results) % 2 == 0:
                    results.append(_request(client, "GET", health_url))
                else:
                    results.append(_request(client, "POST", recommend_url, DEFAULT_PAYLOAD))
            return results

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(worker, index) for index in range(workers)]
            for future in as_completed(futures):
                for status, elapsed_ms in future.result():
                    latencies.append(elapsed_ms)
                    if status >= 400:
                        errors += 1

    latencies.sort()
    p95_index = max(0, int(len(latencies) * 0.95) - 1)
    summary = {
        "requests": len(latencies),
        "errors": errors,
        "p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(latencies[p95_index], 2),
        "max_ms": round(max(latencies), 2),
        "workers": workers,
        "requests_per_worker": requests_per_worker,
        "p95_budget_ms": p95_budget_ms,
        "passed": errors == 0 and latencies[p95_index] <= p95_budget_ms,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a lightweight EDTA load test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--requests-per-worker", type=int, default=5)
    parser.add_argument("--p95-budget-ms", type=float, default=3000.0)
    args = parser.parse_args()

    summary = run_load_test(
        base_url=args.base_url,
        workers=args.workers,
        requests_per_worker=args.requests_per_worker,
        p95_budget_ms=args.p95_budget_ms,
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
