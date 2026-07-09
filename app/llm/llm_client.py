from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from app.llm.llm_provider import LLMProvider

if TYPE_CHECKING:
    from app.provider_telemetry import ProviderTelemetryStore


class LLMClient(LLMProvider):
    """Backward-compatible alias for the pluggable LLM provider."""

    def __init__(
        self,
        telemetry: "ProviderTelemetryStore | None" = None,
        orchestrator_callback: Callable[[float], None] | None = None,
    ):
        super().__init__(telemetry=telemetry, orchestrator_callback=orchestrator_callback)

    def enrich_intent(self, context_text: str) -> Optional[dict[str, Any]]:
        return super().enrich_intent(context_text)
