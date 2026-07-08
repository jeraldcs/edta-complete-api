import os

from app.haoe_telemetry import HAOETelemetryStore
from app.models import CustomerContext, OrchestrationDecision


class HybridAIOrchestrationEngine:
    """Routes inference to the cheapest tier that should be reliable enough."""

    DISTILLED_TIER = "distilled_pattern"

    def __init__(self, telemetry: HAOETelemetryStore | None = None):
        self.telemetry = telemetry or HAOETelemetryStore()
        self.llm_failures = 0
        self.llm_circuit_open = False
        self.session_cost_units = 0.0
        self.cost_budget = float(os.getenv("HAOE_LLM_COST_BUDGET", "10.0"))
        self.failure_threshold = int(os.getenv("HAOE_LLM_FAILURE_THRESHOLD", "3"))

    def record_llm_failure(self) -> None:
        self.llm_failures += 1
        if self.llm_failures >= self.failure_threshold:
            self.llm_circuit_open = True

    def record_llm_success(self) -> None:
        self.llm_failures = 0

    def _budget_allows_llm(self, estimated_cost: float) -> bool:
        return (self.session_cost_units + estimated_cost) <= self.cost_budget

    def _finalize(self, decision: OrchestrationDecision) -> OrchestrationDecision:
        self.session_cost_units += decision.estimated_cost_units
        self.telemetry.record(
            tier=decision.tier,
            reason=decision.reason,
            estimated_latency_ms=decision.estimated_latency_ms,
            estimated_cost_units=decision.estimated_cost_units,
            llm_circuit_open=self.llm_circuit_open,
        )
        return decision

    def choose_route(
        self,
        context: CustomerContext,
        context_text: str,
        use_ai_models: bool,
        use_llm: bool,
        llm_enabled: bool,
        distilled_pattern_available: bool,
    ) -> OrchestrationDecision:
        if (
            context.current_intent
            and context.journey_stage
            and context.channel_context.get("source") == "free_text_scenario"
        ):
            return self._finalize(OrchestrationDecision(
                tier="rules",
                reason="Scenario parser supplied intent and journey with high confidence.",
                estimated_latency_ms=5,
                estimated_cost_units=0.0,
            ))

        llm_cost = 1.0
        if use_llm and llm_enabled and not self.llm_circuit_open:
            high_ambiguity = (
                len(context.search_terms) == 0
                or "unknown" in context_text
                or len(context_text.split()) > 80
            )
            if high_ambiguity and self._budget_allows_llm(llm_cost):
                return self._finalize(OrchestrationDecision(
                    tier="llm",
                    reason="Ambiguous or rich context benefits from frontier teacher reasoning.",
                    estimated_latency_ms=900,
                    estimated_cost_units=llm_cost,
                    used_teacher_signal=True,
                ))
            if high_ambiguity and not self._budget_allows_llm(llm_cost):
                return self._finalize(OrchestrationDecision(
                    tier="ml",
                    reason="LLM route skipped because HAOE cost budget would be exceeded.",
                    estimated_latency_ms=45,
                    estimated_cost_units=0.05,
                ))

        if self.llm_circuit_open and use_llm:
            return self._finalize(OrchestrationDecision(
                tier="ml",
                reason="LLM circuit breaker is open after repeated failures; using local ML.",
                estimated_latency_ms=45,
                estimated_cost_units=0.05,
            ))

        if distilled_pattern_available and use_ai_models:
            return self._finalize(OrchestrationDecision(
                tier=self.DISTILLED_TIER,
                reason="A distilled local pattern memory match was found for this request.",
                estimated_latency_ms=35,
                estimated_cost_units=0.02,
            ))

        if use_ai_models:
            return self._finalize(OrchestrationDecision(
                tier="ml",
                reason="Local trained classifiers provide low-latency intent and journey inference.",
                estimated_latency_ms=45,
                estimated_cost_units=0.05,
            ))

        return self._finalize(OrchestrationDecision(
            tier="rules",
            reason="AI models disabled; using explicit inputs and deterministic defaults.",
            estimated_latency_ms=5,
            estimated_cost_units=0.0,
        ))

    def status(self) -> dict:
        return {
            "session_cost_units": round(self.session_cost_units, 4),
            "cost_budget": self.cost_budget,
            "llm_failures": self.llm_failures,
            "llm_circuit_open": self.llm_circuit_open,
            "failure_threshold": self.failure_threshold,
            "distilled_tier_name": self.DISTILLED_TIER,
            "telemetry": self.telemetry.summary(),
        }
