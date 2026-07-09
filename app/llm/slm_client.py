from __future__ import annotations

from typing import Any, Optional

from app.inference.providers.distilled_slm_provider import DistilledSLMProvider
from app.llm.openai_compatible_client import OpenAICompatibleClient
from app.llm.prompt_templates import enrich_intent_prompt, explain_recommendation_prompt
from app.llm.provider_config import ProviderSettings, get_inference_provider_config
from app.models import IntentType, JourneyStage
from app.provider_telemetry import ProviderTelemetryStore
from app.rules_engine import RulesEngine
from app.self_distillation import SelfDistillationStore


class SLMClient:
    """Local Small Language Model strategy for deployed environments.

    Unified SLM tier: distilled pattern memory -> optional OpenAI-compatible
    endpoint -> rules fallback. Works with no external API when SLM_BASE_URL is unset.
    """

    def __init__(
        self,
        model: str | None = None,
        *,
        rules: RulesEngine | None = None,
        distillation: SelfDistillationStore | None = None,
        telemetry: ProviderTelemetryStore | None = None,
    ):
        self.settings = get_inference_provider_config().provider_settings("slm")
        self.model = model or self.settings.model
        self.enabled = self.settings.enabled
        self.base_url = self.settings.base_url
        self.timeout_seconds = self.settings.timeout_seconds
        self.telemetry = telemetry
        self.distillation = distillation or SelfDistillationStore()
        self.rules = rules or RulesEngine()
        from app.scenario_nlp import ScenarioNLPParser

        self.parser = ScenarioNLPParser()
        self.remote: OpenAICompatibleClient | None = None
        self.last_status = "ready" if self.enabled else "disabled"
        self.last_error = None
        if self.enabled and self.settings.base_url:
            remote_settings = ProviderSettings(
                name=self.settings.name,
                driver=self.settings.driver,
                api_mode="chat",
                enabled=True,
                model=self.model,
                api_key=self.settings.api_key,
                base_url=self.settings.base_url,
                timeout_seconds=self.settings.timeout_seconds,
                max_retries=self.settings.max_retries,
                remote_available=True,
            )
            self.remote = OpenAICompatibleClient(remote_settings)
            self.last_status = self.remote.last_status
            self.last_error = self.remote.last_error
        elif self.enabled:
            self.last_status = "local_only"
        self.provider = DistilledSLMProvider(
            distillation=self.distillation,
            rules=self.rules,
            remote_enricher=self.remote_enrich_intent if self.remote and self.remote.client else None,
        )

    def status(self) -> dict[str, Any]:
        provider_status = self.provider.status()
        return {
            "enabled": self.enabled,
            "model": self.model,
            "base_url": self.base_url,
            "adapter": "openai_compatible",
            "mode": "distilled_pattern_only" if not self.base_url else "distilled_plus_remote",
            "last_status": self.last_status,
            "last_error": self.last_error,
            "pattern_count": provider_status.get("pattern_count", 0),
            "strategy": "distilled_slm_unified",
            "provider": provider_status,
            "remote": self.remote.status() if self.remote else None,
        }

    def remote_enrich_intent(self, context_text: str) -> Optional[dict[str, Any]]:
        if self.remote is None or self.remote.client is None:
            return None
        try:
            result = self.remote.complete_text(
                enrich_intent_prompt(context_text),
                operation="slm_enrich_intent",
            )
            if self.telemetry is not None:
                self.telemetry.record(result.usage)
            payload = self.remote.parse_json(result.text)
            self.last_status = "remote_slm_success"
            self.last_error = None
            return payload
        except Exception as exc:
            self.last_status = "remote_slm_failed"
            self.last_error = str(exc)
            return None

    def enrich_intent(self, context_text: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            self.last_status = "disabled"
            return None

        intent, journey, result = self.provider.infer(context_text)
        self.last_status = result.sub_source or "slm"
        self.last_error = None
        return {
            "intent": intent.label,
            "journey_stage": journey.label,
            "confidence": max(intent.confidence, journey.confidence),
            "reason": result.metadata.get("reason") or f"Unified SLM via {result.sub_source}",
        }

    def explain_recommendation(
        self,
        context_text: str,
        recommendation_payload: dict[str, Any],
    ) -> Optional[str]:
        if not self.enabled:
            return None
        if self.remote is not None and self.remote.client is not None:
            try:
                result = self.remote.complete_text(
                    explain_recommendation_prompt(context_text, recommendation_payload),
                    operation="slm_explain_recommendation",
                    temperature=0.2,
                )
                if self.telemetry is not None:
                    self.telemetry.record(result.usage)
                text = result.text.strip()
                if text:
                    self.last_status = "remote_explanation_generated"
                    return text
            except Exception as exc:
                self.last_status = "remote_explanation_failed"
                self.last_error = str(exc)
        return self.rules.explain(context_text, recommendation_payload)

    def parse_scenario_context(self, scenario_text: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None

        context, details = self.parser.parse(scenario_text, use_llm=False)
        payload = context.model_dump(mode="json")
        payload["confidence"] = details.get("parser_confidence", 0.75)
        payload["parse_reason"] = details.get("reason", "SLM heuristic scenario parser")
        payload["channel_context"] = {
            **(payload.get("channel_context") or {}),
            "source": "free_text_scenario",
            "parser": "slm",
        }
        self.last_status = "scenario_parsed"
        return payload

    def generate_synthetic_training_data(self, domain: str, count: int) -> Optional[list[dict[str, Any]]]:
        if not self.enabled:
            return None
        templates = {
            "travel": ("family SUV airport rental booking", IntentType.purchase.value),
            "banking": ("compare credit card rewards application", IntentType.research.value),
            "healthcare": ("hcp obesity product education", IntentType.research.value),
            "restaurant": ("restaurant table reservation menu browse", IntentType.purchase.value),
        }
        text, intent = templates.get(domain, (f"{domain} customer browsing options", IntentType.research.value))
        return [{"text": text, "intent": intent} for _ in range(min(count, 20))]
