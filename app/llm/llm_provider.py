from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.llm.prompt_templates import (
    enrich_intent_prompt,
    explain_recommendation_prompt,
    parse_scenario_prompt,
    synthetic_training_prompt,
)
from app.llm.provider_config import get_inference_provider_config

if TYPE_CHECKING:
    from app.provider_telemetry import ProviderTelemetryStore


class LLMProvider:
    """Pluggable LLM provider backed by config/inference_providers.yaml."""

    def __init__(
        self,
        telemetry: "ProviderTelemetryStore | None" = None,
        orchestrator_callback: Callable[[float], None] | None = None,
    ):
        self.settings = get_inference_provider_config().provider_settings("llm")
        self.adapter = OpenAICompatibleClient(self.settings) if self.settings.enabled else None
        self.telemetry = telemetry
        self.orchestrator_callback = orchestrator_callback
        self.model = self.settings.model
        self.enabled = self.settings.enabled and self.adapter is not None and self.adapter.client is not None
        self.base_url = self.settings.base_url
        self.timeout_seconds = self.settings.timeout_seconds
        self.max_retries = self.settings.max_retries
        self.last_status = self.adapter.last_status if self.adapter else "not_configured"
        self.last_error = self.adapter.last_error if self.adapter else "OPENAI_API_KEY is not set."

    def _record_usage(self, usage) -> None:
        if self.telemetry is not None:
            self.telemetry.record(usage)
        if self.orchestrator_callback is not None:
            self.orchestrator_callback(usage.estimated_cost_units)

    def status(self) -> dict[str, Any]:
        payload = self.adapter.status() if self.adapter else {
            "provider": "llm",
            "enabled": False,
            "model": self.model,
            "base_url": self.base_url,
            "last_status": "not_configured",
            "last_error": "OPENAI_API_KEY is not set.",
        }
        payload["adapter"] = "openai_compatible"
        payload["plugable_via"] = "config/inference_providers.yaml"
        return payload

    def enrich_intent(self, context_text: str) -> Optional[dict[str, Any]]:
        if not self.enabled or self.adapter is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None
        try:
            result = self.adapter.complete_text(enrich_intent_prompt(context_text), operation="enrich_intent")
            payload = self.adapter.parse_json(result.text)
            self._record_usage(result.usage)
            self.last_status = "intent_enriched"
            self.last_error = None
            return payload
        except Exception as exc:
            self.last_status = "intent_failed"
            self.last_error = str(exc)
            return None

    def explain_recommendation(
        self,
        context_text: str,
        recommendation_payload: dict[str, Any],
    ) -> Optional[str]:
        if not self.enabled or self.adapter is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None
        try:
            result = self.adapter.complete_text(
                explain_recommendation_prompt(context_text, recommendation_payload),
                operation="explain_recommendation",
                temperature=0.2,
            )
            self._record_usage(result.usage)
            self.last_status = "explanation_generated"
            self.last_error = None
            return result.text
        except Exception as exc:
            self.last_status = "explanation_failed"
            self.last_error = str(exc)
            return None

    def generate_synthetic_training_data(self, domain: str, count: int) -> Optional[list[dict[str, Any]]]:
        if not self.enabled or self.adapter is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None
        try:
            result = self.adapter.complete_text(
                synthetic_training_prompt(domain, count),
                operation="synthetic_training_data",
            )
            payload = self.adapter.parse_json(result.text)
            self._record_usage(result.usage)
            self.last_status = "synthetic_data_generated"
            self.last_error = None
            return payload
        except Exception as exc:
            self.last_status = "synthetic_data_failed"
            self.last_error = str(exc)
            return None

    def parse_scenario_context(self, scenario_text: str) -> Optional[dict[str, Any]]:
        if not self.enabled or self.adapter is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None
        try:
            result = self.adapter.complete_text(
                parse_scenario_prompt(scenario_text),
                operation="parse_scenario_context",
            )
            payload = self.adapter.parse_json(result.text)
            self._record_usage(result.usage)
            self.last_status = "scenario_parsed"
            self.last_error = None
            return payload
        except Exception as exc:
            self.last_status = "scenario_parse_failed"
            self.last_error = str(exc)
            return None
