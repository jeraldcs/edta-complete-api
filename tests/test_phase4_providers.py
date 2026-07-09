from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.inference.explanation_router import ExplanationRouter
from app.llm.cost_estimator import estimate_cost_units, estimate_tokens
from app.llm.llm_provider import LLMProvider
from app.llm.provider_config import InferenceProviderConfig, ProviderSettings
from app.provider_telemetry import ProviderTelemetryStore


def test_cost_estimator_computes_token_cost():
    cost = estimate_cost_units(
        input_tokens=1000,
        output_tokens=500,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
    )
    assert cost > 0


def test_provider_settings_include_cost_fields():
    settings = InferenceProviderConfig().provider_settings("llm")
    assert settings.cost_per_1k_input_tokens > 0
    assert settings.cost_per_1k_output_tokens > 0


def test_explanation_router_prefers_slm_first(monkeypatch):
    slm = MagicMock()
    llm = MagicMock()
    slm.explain_recommendation.return_value = "SLM explanation"
    llm.enabled = True
    llm.explain_recommendation.return_value = "LLM explanation"

    router = ExplanationRouter(slm, llm)
    text, source = router.explain("context", {"candidate_title": "SUV"}, use_llm_explanation=True)
    assert text == "SLM explanation"
    assert source == "slm"
    llm.explain_recommendation.assert_not_called()


def test_explanation_router_escalates_to_llm_when_slm_empty(monkeypatch):
    slm = MagicMock()
    llm = MagicMock()
    slm.explain_recommendation.side_effect = [None, None]
    llm.enabled = True
    llm.explain_recommendation.return_value = "LLM explanation"

    router = ExplanationRouter(slm, llm)
    text, source = router.explain("context", {"candidate_title": "SUV"}, use_llm_explanation=True)
    assert text == "LLM explanation"
    assert source == "llm"


def test_provider_telemetry_records_usage(tmp_path):
    db_path = tmp_path / "provider.db"
    from app.db import Database

    store = ProviderTelemetryStore(Database(db_path))
    store.record(
        __import__("app.llm.cost_estimator", fromlist=["CompletionUsage"]).CompletionUsage(
            provider="llm",
            operation="explain_recommendation",
            model="gpt-4o-mini",
            input_tokens=120,
            output_tokens=40,
            estimated_cost_units=0.002,
            latency_ms=15,
        )
    )
    summary = store.summary()
    assert summary["call_count"] == 1
    assert summary["providers"]["llm"]["count"] == 1


def test_llm_provider_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = LLMProvider()
    assert provider.enabled is False
