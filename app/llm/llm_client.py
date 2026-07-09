import json
import os
import time
from typing import Any, Optional


class LLMClient:
    """Optional OpenAI-compatible LLM helper for cloud teacher models."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = os.getenv("OPENAI_MODEL", model)
        self.enabled = bool(os.getenv("OPENAI_API_KEY"))
        self.base_url = os.getenv("OPENAI_BASE_URL") or None
        self.timeout_seconds = float(os.getenv("LLM_REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("LLM_MAX_RETRIES", "2"))
        self.client = None
        self.last_status = "not_configured" if not self.enabled else "ready"
        self.last_error = None
        if self.enabled:
            try:
                from openai import OpenAI

                kwargs: dict[str, Any] = {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "timeout": self.timeout_seconds,
                }
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self.client = OpenAI(**kwargs)
            except Exception as exc:
                self.enabled = False
                self.client = None
                self.last_status = "client_init_failed"
                self.last_error = str(exc)

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "last_status": self.last_status,
            "last_error": self.last_error,
        }

    @staticmethod
    def _response_text(response: Any) -> str:
        text = getattr(response, "output_text", None)
        if text:
            return str(text).strip()

        parts = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                value = getattr(content, "text", None)
                if value:
                    parts.append(str(value))
        return "\n".join(parts).strip()

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

    def _call_responses_api(self, prompt: str) -> str:
        if self.client is None:
            raise RuntimeError("LLM client is not configured.")
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.responses.create(model=self.model, input=prompt)
                return self._response_text(response)
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 3))
        raise last_error or RuntimeError("LLM request failed.")

    def enrich_intent(self, context_text: str) -> Optional[dict[str, Any]]:
        if not self.enabled or self.client is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None

        prompt = f"""
Analyze this customer session context and return JSON only.

Context:
{context_text}

Return exactly this schema:
{{
  "intent": "research|purchase|support|retention|upgrade|unknown",
  "confidence": 0.0,
  "journey_stage": "awareness|research|consideration|purchase|service|retention",
  "reason": "short reason"
}}
"""
        try:
            text = self._call_responses_api(prompt)
            self.last_status = "intent_enriched"
            self.last_error = None
            return self._parse_json(text)
        except Exception as exc:
            self.last_status = "intent_failed"
            self.last_error = str(exc)
            return None

    def explain_recommendation(
        self,
        context_text: str,
        recommendation_payload: dict[str, Any],
    ) -> Optional[str]:
        if not self.enabled or self.client is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None

        prompt = f"""
Explain why this recommendation was selected in simple enterprise architecture language.

Customer context:
{context_text}

Recommendation payload:
{json.dumps(recommendation_payload, indent=2)}

Rules:
- Under 70 words.
- Mention intent, journey, TAPL governance, expected outcome, and business value if relevant.
- Do not invent facts.
"""
        try:
            text = self._call_responses_api(prompt)
            self.last_status = "explanation_generated"
            self.last_error = None
            return text
        except Exception as exc:
            self.last_status = "explanation_failed"
            self.last_error = str(exc)
            return None

    def generate_synthetic_training_data(self, domain: str, count: int) -> Optional[list[dict[str, Any]]]:
        if not self.enabled or self.client is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None

        prompt = f"""
Generate {count} synthetic intent-classification training records for the {domain} domain.
Return JSON array only. Each item must have: text, intent.
Allowed intents: research, purchase, support, retention, upgrade, unknown.
"""
        try:
            text = self._call_responses_api(prompt)
            self.last_status = "synthetic_data_generated"
            self.last_error = None
            return self._parse_json(text)
        except Exception as exc:
            self.last_status = "synthetic_data_failed"
            self.last_error = str(exc)
            return None

    def parse_scenario_context(self, scenario_text: str) -> Optional[dict[str, Any]]:
        if not self.enabled or self.client is None:
            self.last_status = "not_configured"
            self.last_error = "OPENAI_API_KEY is not set."
            return None

        prompt = f"""
Convert this free-text customer scenario into JSON only.

Scenario:
{scenario_text}

Return exactly this schema:
{{
  "customer_id": "string or null",
  "anonymous_id": "string or null",
  "channel": "web|mobile|email|sms|push|in_app|call_center|chatbot|voice_assistant|iot|wearable|connected_car|kiosk|smart_tv|ar_vr|social|marketplace|partner_api",
  "journey_stage": "awareness|research|consideration|purchase|service|retention|null",
  "current_intent": "research|purchase|support|retention|upgrade|unknown|null",
  "session_events": ["short_event_names"],
  "search_terms": ["short search phrases"],
  "profile_attributes": {{}},
  "business_context": {{}},
  "channel_context": {{}},
  "device_context": {{}},
  "consent": {{"personalization": true, "profile_lookup": true}},
  "confidence": 0.0,
  "parse_reason": "short reason"
}}

Rules:
- Infer only from the scenario.
- Use snake_case event names.
- Keep arrays concise.
- If consent is explicitly missing or opted out, set personalization false.
"""
        try:
            text = self._call_responses_api(prompt)
            self.last_status = "scenario_parsed"
            self.last_error = None
            return self._parse_json(text)
        except Exception as exc:
            self.last_status = "scenario_parse_failed"
            self.last_error = str(exc)
            return None
