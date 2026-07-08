import os
from pathlib import Path
from typing import Any

import yaml

from app.models import Channel, TAPLAction


DEFAULT_POLICIES: dict[str, Any] = {
    "consent": {
        "required_flag": "personalization",
        "fallback_action": "generic_fallback",
        "reason": "Personalization consent missing.",
    },
    "fatigue": {
        "delay_threshold": 0.70,
        "delay_action": "delay",
        "reason": "High fatigue detected from repeated exposure.",
    },
    "sensitive_channels": {
        "channels": ["sms", "push", "wearable", "voice_assistant", "iot"],
        "sensitivity_threshold": 0.80,
        "action": "suppress",
        "reason": "Sensitive recommendation is not suitable for this constrained channel.",
    },
    "trust_weights": {
        "consent": 0.30,
        "memory_trust": 0.25,
        "compliance": 0.20,
        "fatigue_inverse": 0.15,
        "sensitivity_inverse": 0.10,
    },
}


class TAPLPolicyEngine:
    """Load auditable TAPL governance rules from YAML."""

    def __init__(self, policy_path: str | None = None):
        self.policy_path = Path(
            policy_path or os.getenv("TAPL_POLICY_FILE", "config/tapl_policies.yaml")
        )
        self.policies = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.policy_path.exists():
            return DEFAULT_POLICIES
        try:
            loaded = yaml.safe_load(self.policy_path.read_text(encoding="utf-8"))
            return loaded if isinstance(loaded, dict) else DEFAULT_POLICIES
        except (OSError, yaml.YAMLError):
            return DEFAULT_POLICIES

    def evaluate_overrides(
        self,
        *,
        consent_score: float,
        fatigue_score: float,
        channel: Channel,
        compliance_sensitivity: float,
    ) -> tuple[TAPLAction | None, str | None, str | None]:
        consent_policy = self.policies.get("consent", {})
        if consent_score == 0:
            return (
                TAPLAction(consent_policy.get("fallback_action", "generic_fallback")),
                consent_policy.get("reason", "Personalization consent missing."),
                "policy:consent",
            )

        sensitive = self.policies.get("sensitive_channels", {})
        sensitive_channels = set()
        for value in sensitive.get("channels", []):
            try:
                sensitive_channels.add(Channel(value))
            except ValueError:
                continue
        threshold = float(sensitive.get("sensitivity_threshold", 0.80))
        if compliance_sensitivity >= threshold and channel in sensitive_channels:
            return (
                TAPLAction(sensitive.get("action", "suppress")),
                sensitive.get(
                    "reason",
                    "Sensitive recommendation is not suitable for this constrained channel.",
                ),
                "policy:sensitive_channel",
            )

        fatigue_policy = self.policies.get("fatigue", {})
        delay_threshold = float(fatigue_policy.get("delay_threshold", 0.70))
        if fatigue_score >= delay_threshold:
            return (
                TAPLAction(fatigue_policy.get("delay_action", "delay")),
                fatigue_policy.get("reason", "High fatigue detected from repeated exposure."),
                "policy:fatigue",
            )

        return None, None, None

    def trust_score(
        self,
        *,
        consent_score: float,
        memory_trust: float,
        compliance_score: float,
        fatigue_score: float,
        sensitivity_score: float,
    ) -> float:
        weights = self.policies.get("trust_weights", DEFAULT_POLICIES["trust_weights"])
        return max(
            0.0,
            min(
                1.0,
                weights.get("consent", 0.30) * consent_score
                + weights.get("memory_trust", 0.25) * memory_trust
                + weights.get("compliance", 0.20) * compliance_score
                + weights.get("fatigue_inverse", 0.15) * (1.0 - fatigue_score)
                + weights.get("sensitivity_inverse", 0.10) * (1.0 - sensitivity_score),
            ),
        )
