from __future__ import annotations

import json
import time
from typing import Any

from app.llm.provider_config import ProviderSettings


class OpenAICompatibleClient:
    """Shared OpenAI SDK adapter for LLM and SLM providers."""

    def __init__(self, settings: ProviderSettings):
        self.settings = settings
        self.client = None
        self.last_status = "not_configured"
        self.last_error: str | None = None
        if settings.enabled and (settings.api_key or settings.base_url):
            try:
                from openai import OpenAI

                kwargs: dict[str, Any] = {"timeout": settings.timeout_seconds}
                if settings.api_key:
                    kwargs["api_key"] = settings.api_key
                if settings.base_url:
                    kwargs["base_url"] = settings.base_url
                self.client = OpenAI(**kwargs)
                self.last_status = "ready"
            except Exception as exc:
                self.client = None
                self.last_status = "client_init_failed"
                self.last_error = str(exc)
        elif settings.enabled and settings.name == "slm":
            self.last_status = "local_only"
        else:
            self.last_status = "not_configured"

    @staticmethod
    def parse_json(text: str) -> Any:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.removeprefix("json").strip()
        start = min([index for index in [cleaned.find("{"), cleaned.find("[")] if index >= 0], default=0)
        end = max(cleaned.rfind("}"), cleaned.rfind("]"))
        if end >= start:
            cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)

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
        if parts:
            return "\n".join(parts).strip()

        choices = getattr(response, "choices", None) or []
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None) if message else None
            if content:
                return str(content).strip()
        return ""

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.settings.name,
            "driver": self.settings.driver,
            "api_mode": self.settings.api_mode,
            "enabled": self.settings.enabled,
            "model": self.settings.model,
            "base_url": self.settings.base_url,
            "timeout_seconds": self.settings.timeout_seconds,
            "max_retries": self.settings.max_retries,
            "remote_available": self.settings.remote_available,
            "last_status": self.last_status,
            "last_error": self.last_error,
        }

    def chat_text(self, prompt: str, *, temperature: float = 0.1) -> str:
        if self.client is None:
            raise RuntimeError(f"{self.settings.name} client is not configured.")
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                if self.settings.api_mode == "responses":
                    response = self.client.responses.create(
                        model=self.settings.model,
                        input=prompt,
                    )
                else:
                    response = self.client.chat.completions.create(
                        model=self.settings.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                    )
                text = self._response_text(response)
                if not text:
                    raise RuntimeError("Empty model response.")
                self.last_status = "success"
                self.last_error = None
                return text
            except Exception as exc:
                last_error = exc
                if attempt >= self.settings.max_retries:
                    break
                time.sleep(min(2 ** attempt, 3))
        self.last_status = "request_failed"
        self.last_error = str(last_error)
        raise last_error or RuntimeError(f"{self.settings.name} request failed.")

    def chat_json(self, prompt: str, *, temperature: float = 0.1) -> Any:
        text = self.chat_text(prompt, temperature=temperature)
        return self.parse_json(text)
