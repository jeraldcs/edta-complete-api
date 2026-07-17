#!/usr/bin/env python3
"""Generate travel scenario score matrix JSON and markdown report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.recommendation_handlers import RecommendationHandlers
from app.services.travel_benchmark import benchmark_to_markdown
import app.container as app_container


def main() -> int:
    handlers = RecommendationHandlers(app_container.container)
    payload = handlers.travel_scenario_benchmark()

    out_json = ROOT / "data" / "generated" / "travel_scenario_scores.json"
    out_md = ROOT / "docs" / "TRAVEL_SCENARIO_SCORES.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_md.write_text(benchmark_to_markdown(payload), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print(f"Vehicle match rate: {payload['vehicle_match_rate']:.0%} ({payload['vehicle_match_count']}/{payload['scenario_count']})")
    return 0 if payload["vehicle_match_count"] == payload["scenario_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
