import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_POLICIES: dict[str, Any] = {
    "defaults": {
        "trust_baseline": 0.65,
        "fatigue_baseline": 0.0,
    },
    "decay": {
        "trust_half_life_hours": 168.0,
        "fatigue_half_life_hours": 48.0,
    },
    "feedback": {
        "click_trust_delta": 0.03,
        "click_preference_delta": 0.25,
        "dismiss_trust_delta": -0.08,
        "dismiss_fatigue_delta": 0.12,
        "dismiss_preference_delta": -0.5,
        "convert_trust_delta": 0.05,
        "convert_candidate_preference_delta": 1.0,
        "convert_channel_preference_delta": 0.5,
        "convert_type_preference_delta": 0.35,
        "convert_category_preference_delta": 0.2,
    },
    "exposure": {
        "deliver_fatigue_delta": 0.04,
        "soften_fatigue_delta": 0.03,
        "delay_fatigue_delta": 0.01,
    },
    "ranking": {
        "max_preference_boost": 0.12,
        "max_preference_penalty": -0.15,
        "candidate_weight_scale": 0.04,
        "channel_weight_scale": 0.02,
        "type_weight_scale": 0.02,
        "category_weight_scale": 0.015,
    },
}


class EMLPolicyEngine:
    """Load configurable Experience Memory Layer rules from YAML."""

    def __init__(self, policy_path: str | None = None):
        configured = policy_path or os.getenv("EML_POLICY_FILE", "config/eml_policies.yaml")
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
