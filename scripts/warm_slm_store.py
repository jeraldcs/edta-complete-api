"""Warm the SLM distilled pattern store from training scenarios."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from app.context_graph import ContextGraph
from app.models import CustomerContext
from app.recommender import RecommendationEngine
from app.scenario_nlp import ScenarioNLPParser

ROOT = Path(__file__).resolve().parents[1]
TRAINING_CSV = ROOT / "data" / "scenario_training_master.csv"


def warm_store(limit: int) -> dict:
    parser = ScenarioNLPParser()
    engine = RecommendationEngine()
    warmed = 0
    rows = list(csv.DictReader(TRAINING_CSV.open(encoding="utf-8")))
    for row in rows[:limit]:
        scenario_text = row.get("scenario_text") or row.get("scenario") or ""
        if len(scenario_text.strip()) < 10:
            continue
        context, _ = parser.parse(scenario_text, use_llm=False)
        graph = ContextGraph(context)
        engine._resolve_predictions(
            context,
            graph.to_text(),
            use_ai_models=True,
            use_llm=False,
            use_slm=True,
            inference_mode="slm",
            graph=graph,
        )
        warmed += 1
    status = engine.distillation.status()
    return {"warmed_scenarios": warmed, **status}


def main() -> None:
    args = argparse.ArgumentParser(description="Warm SLM distilled pattern memory.")
    args.add_argument("--limit", type=int, default=25)
    parsed = args.parse_args()
    print(json.dumps(warm_store(parsed.limit), indent=2))


if __name__ == "__main__":
    main()
