import os

from app.haoe_policy import HAOEPolicyEngine
from app.haoe_telemetry import HAOETelemetryStore
from app.inference.contracts import PUBLIC_INFERENCE_TIERS
from app.models import CustomerContext, IntentType, OrchestrationDecision
from app.rules.confidence import combined_rules_confidence, scenario_rules_ready


class HybridAIOrchestrationEngine:
    """Routes inference to the cheapest public tier that should be reliable enough."""

    SLM_TIER = "slm"

    def __init__(
        self,
        telemetry: HAOETelemetryStore | None = None,
        policy: HAOEPolicyEngine | None = None,
    ):
        self.telemetry = telemetry or HAOETelemetryStore()
        self.policy = policy or HAOEPolicyEngine()
        self.llm_failures = 0
        self.llm_circuit_open = False
        self.session_cost_units = 0.0
        circuit = self.policy.section("circuit_breaker")
        self.cost_budget = float(os.getenv("HAOE_LLM_COST_BUDGET", circuit.get("session_cost_budget", 10.0)))
        self.failure_threshold = int(os.getenv("HAOE_LLM_FAILURE_THRESHOLD", circuit.get("failure_threshold", 3)))

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

    def _decision(self, tier: str, reason: str, *, used_teacher_signal: bool = False) -> OrchestrationDecision:
        return OrchestrationDecision(
            tier=tier,
            reason=reason,
            estimated_latency_ms=self.policy.latency_ms(tier),
            estimated_cost_units=self.policy.cost(tier),
            used_teacher_signal=used_teacher_signal,
        )

    @staticmethod
    def _normalize_inference_mode(mode: str) -> str:
        normalized = (mode or "auto").strip().lower()
        aliases = {
            "distilled_pattern": "slm",
            "distilled": "slm",
            "tkge": "rules",
        }
        return aliases.get(normalized, normalized)

    @staticmethod
    def _parser_confidence(context: CustomerContext, parser_confidence: float | None) -> float:
        if parser_confidence is not None:
            return max(0.0, min(1.0, float(parser_confidence)))
        channel_context = context.channel_context if isinstance(context.channel_context, dict) else {}
        stored = channel_context.get("parser_confidence")
        if stored is not None:
            return max(0.0, min(1.0, float(stored)))
        if channel_context.get("source") == "free_text_scenario":
            return 0.9
        return 0.0

    def _is_ambiguous(self, context: CustomerContext, context_text: str) -> bool:
        ambiguity = self.policy.section("ambiguity")
        triggers = []
        if ambiguity.get("require_search_terms", False) and len(context.search_terms) == 0:
            triggers.append("missing_search_terms")
        if ambiguity.get("unknown_token_triggers_escalation", True) and "unknown" in context_text.lower():
            triggers.append("unknown_context_token")
        threshold = int(ambiguity.get("rich_context_word_threshold", 80))
        if len(context_text.split()) > threshold:
            triggers.append("rich_context")
        if context.current_intent == IntentType.unknown:
            triggers.append("unknown_intent")
        return bool(triggers)

    def choose_route(
        self,
        context: CustomerContext,
        context_text: str,
        use_ai_models: bool,
        use_llm: bool,
        use_slm: bool,
        llm_enabled: bool,
        slm_enabled: bool,
        distilled_pattern_available: bool,
        parser_confidence: float | None = None,
        tkge_intent_confidence: float | None = None,
        tkge_inferred_intent: str | None = None,
        rules_engine_confidence: float = 0.0,
        inference_mode: str = "auto",
    ) -> OrchestrationDecision:
        mode = self._normalize_inference_mode(inference_mode)
        if mode in PUBLIC_INFERENCE_TIERS:
            return self._finalize(self._decision(
                mode,
                f"Inference mode forced to {mode} for benchmarking or explicit request control.",
            ))

        confidence_cfg = self.policy.section("confidence")
        rules_min = float(confidence_cfg.get("rules_min_confidence", 0.75))
        parser_score = self._parser_confidence(context, parser_confidence)
        combined_rules = combined_rules_confidence(
            parser_confidence=parser_score,
            tkge_intent_confidence=tkge_intent_confidence,
            rules_engine_confidence=rules_engine_confidence,
        )
        llm_cost = self.policy.cost("llm")

        if scenario_rules_ready(context) and combined_rules >= rules_min:
            tkge_note = ""
            if tkge_intent_confidence is not None and tkge_intent_confidence >= rules_min:
                tkge_note = f" TKGE timeline boosted confidence to {combined_rules:.2f}."
            return self._finalize(self._decision(
                "rules",
                f"Scenario parser and rules confidence met threshold ({combined_rules:.2f}).{tkge_note}",
            ))

        high_ambiguity = self._is_ambiguous(context, context_text)
        if use_llm and llm_enabled and not self.llm_circuit_open:
            if high_ambiguity and self._budget_allows_llm(llm_cost):
                return self._finalize(self._decision(
                    "llm",
                    "Ambiguous or rich context benefits from frontier teacher reasoning.",
                    used_teacher_signal=True,
                ))
            if high_ambiguity and not self._budget_allows_llm(llm_cost):
                return self._finalize(self._decision(
                    "ml",
                    "LLM route skipped because HAOE cost budget would be exceeded.",
                ))

        if self.llm_circuit_open and use_llm:
            return self._finalize(self._decision(
                "ml",
                "LLM circuit breaker is open after repeated failures; using local ML.",
            ))

        slm_cfg = self.policy.section("slm")
        slm_allowed = slm_enabled and slm_cfg.get("enabled", True)
        if use_slm and slm_allowed and use_ai_models:
            if distilled_pattern_available:
                return self._finalize(self._decision(
                    self.SLM_TIER,
                    "Distilled pattern memory match available under the unified SLM tier.",
                ))
            return self._finalize(self._decision(
                self.SLM_TIER,
                "Local SLM route selected for deployed inference without external LLM dependency.",
            ))

        if use_ai_models:
            return self._finalize(self._decision(
                "ml",
                "Local trained classifiers provide low-latency intent and journey inference.",
            ))

        return self._finalize(self._decision(
            "rules",
            "AI models disabled; using explicit inputs and deterministic defaults.",
        ))

    def status(self) -> dict:
        return {
            "session_cost_units": round(self.session_cost_units, 4),
            "cost_budget": self.cost_budget,
            "llm_failures": self.llm_failures,
            "llm_circuit_open": self.llm_circuit_open,
            "failure_threshold": self.failure_threshold,
            "public_tiers": list(PUBLIC_INFERENCE_TIERS),
            "slm_tier_name": self.SLM_TIER,
            "policy_file": str(self.policy.policy_path),
            "telemetry": self.telemetry.summary(),
        }
