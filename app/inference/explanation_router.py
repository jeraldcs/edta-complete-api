from __future__ import annotations

from typing import Any, Callable

from app.llm.provider_config import get_inference_provider_config
from app.llm.slm_client import SLMClient
from app.llm.llm_provider import LLMProvider


class ExplanationRouter:
    """Route recommendation explanations: SLM first, LLM escalation when enabled."""

    def __init__(
        self,
        slm: SLMClient,
        llm: LLMProvider,
        *,
        on_provider_cost: Callable[[float], None] | None = None,
    ):
        self.slm = slm
        self.llm = llm
        self.on_provider_cost = on_provider_cost
        explanation_cfg = get_inference_provider_config().explanation_config()
        self.prefer_slm_first = bool(explanation_cfg.get("prefer_slm_first", True))
        self.allow_llm_escalation = bool(explanation_cfg.get("allow_llm_escalation", True))

    def explain(
        self,
        context_text: str,
        recommendation_payload: dict[str, Any],
        *,
        use_llm_explanation: bool,
    ) -> tuple[str | None, str | None]:
        if not use_llm_explanation:
            return None, None

        if self.prefer_slm_first:
            slm_text = self.slm.explain_recommendation(context_text, recommendation_payload)
            if slm_text:
                self._maybe_record_slm_cost()
                return slm_text, "slm"

        if self.allow_llm_escalation and self.llm.enabled:
            llm_text = self.llm.explain_recommendation(context_text, recommendation_payload)
            if llm_text:
                return llm_text, "llm"

        slm_text = self.slm.explain_recommendation(context_text, recommendation_payload)
        if slm_text:
            self._maybe_record_slm_cost()
            return slm_text, "slm_rules_fallback"

        return None, None

    def _maybe_record_slm_cost(self) -> None:
        if self.slm.remote is None or self.slm.remote.last_usage is None:
            return
        usage = self.slm.remote.last_usage
        if self.on_provider_cost is not None:
            self.on_provider_cost(usage.estimated_cost_units)

    def status(self) -> dict[str, Any]:
        return {
            "prefer_slm_first": self.prefer_slm_first,
            "allow_llm_escalation": self.allow_llm_escalation,
            "config_source": "config/inference_providers.yaml#explanation",
        }
