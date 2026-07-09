from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.catalog import DEFAULT_CANDIDATES
from app.context_graph import ContextGraph
from app.inference.ml_service import MLInferenceService
from app.models import Channel, CustomerContext


ROOT = Path(__file__).resolve().parents[1]


def test_ml_inference_service_warms_catalog():
    service = MLInferenceService()
    status = service.status()
    assert status["catalog_warmed"] is True
    assert status["provider"] == "ml_inference_service"


def test_ml_inference_service_predicts_intent_journey():
    service = MLInferenceService()
    context = CustomerContext(
        anonymous_id="anon-ml",
        channel=Channel.web,
        search_terms=["family", "suv", "airport", "rental", "booking"],
        session_events=["started_booking"],
    )
    graph = ContextGraph(context)
    context_text = graph.to_text()
    result = service.infer_intent_journey(context_text, graph)
    assert result.intent.label
    assert result.journey.label
    assert result.confidence > 0
    assert "intent_model" in result.models_used


def test_ml_inference_service_semantic_batch_after_warm_start():
    service = MLInferenceService()
    context_text = "family suv airport rental booking"
    candidate_texts = [MLInferenceService.candidate_text(candidate) for candidate in DEFAULT_CANDIDATES[:5]]
    scores = service.semantic_model.score_batch(context_text, candidate_texts)
    assert len(scores) == 5
    assert all(0.0 <= score <= 1.0 for score in scores)


@pytest.mark.skipif(not (ROOT / "data" / "scenario_training_master.csv").exists(), reason="training CSV missing")
def test_evaluate_ml_models_script_writes_summary(tmp_path, monkeypatch):
    output = tmp_path / "ml_eval_summary.json"
    monkeypatch.setenv("PYTHONPATH", str(ROOT))

    import scripts.evaluate_ml_models as evaluator

    monkeypatch.setattr(evaluator, "OUTPUT_PATH", output)
    assert evaluator.main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "intent" in payload
    assert payload["intent"]["accuracy"] >= 0.0
    assert "overall" in payload
