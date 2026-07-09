from __future__ import annotations

import json

import pytest

from app.llm.llm_client import LLMClient
from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.llm.prompt_templates import enrich_intent_prompt, explain_recommendation_prompt
from app.llm.provider_config import InferenceProviderConfig, ProviderSettings
from app.llm.slm_client import SLMClient


def test_openai_compatible_client_parse_json_strips_fences():
    payload = OpenAICompatibleClient.parse_json(
        '```json\n{"intent":"purchase","confidence":0.8,"journey_stage":"purchase","reason":"test"}\n```'
    )
    assert payload["intent"] == "purchase"
    assert payload["confidence"] == 0.8


def test_shared_prompt_templates_are_consistent():
    context = "family suv airport rental booking"
    llm_prompt = enrich_intent_prompt(context)
    slm_prompt = enrich_intent_prompt(context)
    assert llm_prompt == slm_prompt
    assert "journey_stage" in llm_prompt


def test_inference_provider_config_loads_yaml():
    config = InferenceProviderConfig()
    llm = config.provider_settings("llm")
    slm = config.provider_settings("slm")
    assert llm.name == "llm"
    assert slm.name == "slm"
    assert slm.driver == "openai_compatible"


def test_slm_client_works_without_external_api(monkeypatch):
    monkeypatch.delenv("SLM_BASE_URL", raising=False)
    monkeypatch.setenv("SLM_ENABLED", "true")
    client = SLMClient()
    status = client.status()
    assert status["enabled"] is True
    assert status["mode"] == "distilled_pattern_only"
    enriched = client.enrich_intent("web purchase family suv airport rental started booking")
    assert enriched is not None
    assert enriched["confidence"] > 0


def test_slm_client_marks_remote_mode_when_base_url_set(monkeypatch):
    monkeypatch.setenv("SLM_ENABLED", "true")
    monkeypatch.setenv("SLM_BASE_URL", "http://127.0.0.1:11434/v1")
    client = SLMClient()
    assert client.status()["mode"] == "distilled_plus_remote"


def test_llm_client_disabled_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = LLMClient()
    assert client.enabled is False
    assert client.enrich_intent("test context") is None


def test_openai_compatible_client_chat_json_with_stub(monkeypatch):
    settings = ProviderSettings(
        name="slm",
        driver="openai_compatible",
        api_mode="chat",
        enabled=True,
        model="test-model",
        api_key="local-slm",
        base_url="http://example.test/v1",
        timeout_seconds=5,
        max_retries=0,
        remote_available=True,
    )
    client = OpenAICompatibleClient(settings)

    class FakeMessage:
        content = '{"intent":"research","confidence":0.7,"journey_stage":"research","reason":"stub"}'

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        @staticmethod
        def create(**kwargs):
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        chat = FakeChat()

    client.client = FakeOpenAI()
    payload = client.chat_json(enrich_intent_prompt("visitor comparing hotel rooms"))
    assert payload["intent"] == "research"


def test_explain_prompt_serializes_payload():
    prompt = explain_recommendation_prompt(
        "family traveler booking SUV",
        {"candidate_title": "Premium SUV upgrade", "intent": "purchase"},
    )
    assert "Premium SUV upgrade" in prompt
    assert json.loads(json.dumps({"ok": True}))
