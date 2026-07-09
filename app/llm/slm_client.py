from __future__ import annotations

import json
import os
from typing import Any, Optional

from app.inference.providers.distilled_slm_provider import DistilledSLMProvider
from app.models import IntentType, JourneyStage
from app.rules_engine import RulesEngine
from app.scenario_nlp import ScenarioNLPParser
from app.self_distillation import SelfDistillationStore


class SLMClient:
    """Local Small Language Model strategy for deployed environments.

    Public surface mirrors LLMClient; inference runs through DistilledSLMProvider:
    distilled pattern memory -> optional OpenAI-compatible endpoint -> rules fallback.
    """

    def __init__(
        self,
        model: str = "edta-local-slm",
        *,
        rules: RulesEngine | None = None,
        distillation: SelfDistillationStore | None = None,
    ):
        self.model = os.getenv("SLM_MODEL", model)
        self.enabled = os.getenv("SLM_ENABLED", "true").strip().lower() in {"1", "true", "yes"}
        self.base_url = os.getenv("SLM_BASE_URL") or None
        self.api_key = os.getenv("SLM_API_KEY") or "local-slm"
        self.timeout_seconds = float(os.getenv("SLM_REQUEST_TIMEOUT", "15"))
        self.distillation = distillation or SelfDistillationStore()
        self.rules = rules or RulesEngine()
        self.parser = ScenarioNLPParser()
        self.client = None
        self.last_status = "ready" if self.enabled else "disabled"
        self.last_error = None
        if self.base_url:
            try:
                from openai import OpenAI

                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout_seconds)
                self.last_status = "remote_endpoint_ready"
            except Exception as exc:
                self.client = None
                self.last_status = "remote_endpoint_init_failed"
                self.last_error = str(exc)
        self.provider = DistilledSLMProvider(
            distillation=self.distillation,
            rules=self.rules,
            remote_enricher=self.remote_enrich_intent if self.client is not None else None,
        )

    def status(self) -> dict[str, Any]:
        provider_status = self.provider.status()
        return {
            "enabled": self.enabled,
            "model": self.model,
            "base_url": self.base_url,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "pattern_count": provider_status.get("pattern_count", 0),
            "strategy": "distilled_slm_unified",
            "provider": provider_status,
        }

    @staticmethod
    def _parse_json(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        start = min([index for index in [cleaned.find("{"), cleaned.find("[")] if index >= 0], default=0)
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        if end >= start:
            cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)

    def remote_enrich_intent(self, context_text: str) -> Optional[dict[str, Any]]:
        if self.client is None:
            return None
        prompt = f"""
Analyze this customer session context and return JSON only.
Context:
{context_text}
Return schema: {{"intent":"research|purchase|support|retention|upgrade|unknown","confidence":0.0,"journey_stage":"awareness|research|consideration|purchase|service|retention","reason":"short reason"}}
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            content = response.choices[0].message.content or ""
            self.last_status = "remote_slm_success"
            self.last_error = None
            return self._parse_json(content)
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
        if self.client is not None:
            prompt = (
                "Explain this recommendation in under 70 words using the payload JSON.\n"
                f"Context:\n{context_text}\nPayload:\n{json.dumps(recommendation_payload, indent=2)}"
            )
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                )
                text = (response.choices[0].message.content or "").strip()
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
