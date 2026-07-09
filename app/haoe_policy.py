import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_POLICIES: dict[str, Any] = {
    "costs": {
        "llm": 1.0,
        "ml": 0.05,
        "slm": 0.02,
        "distilled_pattern": 0.02,
        "tkge": 0.01,
        "rules": 0.0,
    },
    "latency_ms": {
        "llm": 900,
        "ml": 45,
        "slm": 35,
        "distilled_pattern": 35,
        "tkge": 20,
        "rules": 5,
    },
    "confidence": {
        "rules_min_confidence": 0.75,
        "tkge_min_confidence": 0.55,
        "tkge_escalate_above_parser_delta": 0.15,
    },
    "ambiguity": {
        "require_search_terms": False,
        "unknown_token_triggers_escalation": True,
        "rich_context_word_threshold": 80,
    },
    "distilled": {
        "min_token_overlap": 0.35,
        "distill_min_confidence": 0.75,
    },
    "circuit_breaker": {
        "failure_threshold": 3,
        "session_cost_budget": 10.0,
    },
}


class HAOEPolicyEngine:
    """Load configurable Hybrid AI Orchestration rules from YAML."""

    def __init__(self, policy_path: str | None = None):
        configured = policy_path or os.getenv("HAOE_POLICY_FILE", "config/haoe_policies.yaml")
        self.policy_path = Path(configured)
        self.policies = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.policy_path.exists():
            return DEFAULT_POLICIES.copy()
        try:
            loaded = yaml.safe_load(self.policy_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return DEFAULT_POLICIES.copy()
        merged = DEFAULT_POLICIES.copy()
        for section, values in loaded.items():
            if isinstance(values, dict) and isinstance(merged.get(section), dict):
                merged[section] = {**merged[section], **values}
            else:
                merged[section] = values
        return merged

    def section(self, name: str) -> dict[str, Any]:
        value = self.policies.get(name, {})
        return value if isinstance(value, dict) else {}

    def cost(self, tier: str) -> float:
        return float(self.section("costs").get(tier, 0.0))

    def latency_ms(self, tier: str) -> int:
        return int(self.section("latency_ms").get(tier, 45))
