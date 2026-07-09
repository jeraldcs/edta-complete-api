"""Generate markdown comparison tables from tier benchmark JSON runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_runs(paths: list[Path]) -> list[dict]:
    runs: list[dict] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "tiers" in payload:
            runs.append(payload)
        elif "results" in payload:
            runs.append(
                {
                    "run_id": payload.get("run_id", path.stem),
                    "environment": payload.get("environment", "unknown"),
                    "base_url": payload.get("base_url", ""),
                    "tiers": payload["results"],
                }
            )
        else:
            raise ValueError(f"Unsupported benchmark JSON shape: {path}")
    return runs


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.2f}{suffix}"
    return f"{value}{suffix}"


def render_markdown(runs: list[dict]) -> str:
    lines = ["# EDTA Four-Tier Benchmark Report", ""]
    for run in runs:
        lines.extend(
            [
                f"## Run `{run.get('run_id', 'unknown')}`",
                "",
                f"- Environment: `{run.get('environment', 'unknown')}`",
                f"- Base URL: `{run.get('base_url', '')}`",
                f"- Workers: `{run.get('workers', 'n/a')}`",
                f"- Requests per worker: `{run.get('requests_per_worker', 'n/a')}`",
                f"- Overall pass: `{run.get('passed', False)}`",
                "",
                "| Tier | Requests | p50 (ms) | p95 (ms) | p95 budget | Throughput (rps) | Error rate | Fallback rate | Tier match | Avg confidence | Alignment top-1 | Rules fired avg | Pass |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for tier in run.get("tiers", []):
            latency = tier.get("latency_ms") or {}
            accuracy = tier.get("accuracy_proxy") or {}
            explainability = tier.get("explainability") or {}
            lines.append(
                "| {tier} | {requests} | {p50} | {p95} | {budget} | {rps} | {error_rate} | {fallback_rate} | {tier_match} | {confidence} | {alignment} | {rules_avg} | {passed} |".format(
                    tier=tier.get("tier", "unknown"),
                    requests=tier.get("requests", 0),
                    p50=_fmt(latency.get("p50")),
                    p95=_fmt(latency.get("p95")),
                    budget=_fmt(tier.get("p95_budget_ms")),
                    rps=_fmt(tier.get("throughput_rps")),
                    error_rate=_fmt(tier.get("error_rate")),
                    fallback_rate=_fmt(tier.get("fallback_rate")),
                    tier_match=_fmt(tier.get("observed_tier_match_rate")),
                    confidence=_fmt(tier.get("avg_confidence")),
                    alignment=_fmt(accuracy.get("training_alignment_top1")),
                    rules_avg=_fmt(explainability.get("rules_fired_avg")),
                    passed="yes" if tier.get("passed") else "no",
                )
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render EDTA tier benchmark JSON as markdown.")
    parser.add_argument("inputs", nargs="+", help="Benchmark JSON file(s)")
    parser.add_argument("--output", default="", help="Optional markdown output path")
    args = parser.parse_args()

    paths = [Path(item) for item in args.inputs]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise SystemExit(f"Missing input file(s): {', '.join(missing)}")

    markdown = render_markdown(_load_runs(paths))
    print(markdown, end="")
    if args.output:
        Path(args.output).write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
