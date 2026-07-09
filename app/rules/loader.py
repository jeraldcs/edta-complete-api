from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

DEFAULT_RULES: dict[str, Any] = {
    "intent_signals": {
        "purchase": ["buy", "book", "checkout", "reserve", "quote", "price", "purchase", "order", "converted"],
        "support": ["help", "issue", "maintenance", "repair", "support", "problem", "service", "return"],
        "upgrade": ["upgrade", "premium", "suv", "larger", "better", "enhanced"],
        "retention": ["renew", "loyalty", "churn", "cancel", "retain", "win back"],
        "research": ["compare", "research", "browse", "learn", "options", "explore", "looking", "dismiss"],
    },
    "journey_signals": {
        "purchase": ["checkout", "book", "purchase", "started_booking", "apply"],
        "consideration": ["compare", "availability", "quote", "shortlist", "options"],
        "research": ["browse", "search", "viewed", "research", "learn"],
        "retention": ["renew", "loyalty", "churn", "cancel"],
        "service": ["support", "help", "issue", "maintenance"],
        "awareness": ["landing", "discover", "intro"],
    },
    "channel_event_boosts": {
        "web": ["viewed", "page", "banner", "detail"],
        "mobile": ["scan", "qr", "barcode", "app"],
        "chatbot": ["chat", "conversation", "message"],
        "email": ["email", "newsletter", "campaign"],
    },
    "confidence": {
        "explicit_intent_base": 0.82,
        "explicit_signal_bonus": 0.12,
        "keyword_hit_base": 0.45,
        "keyword_hit_increment": 0.12,
        "channel_boost": 0.05,
        "tkge_timeline_weight": 1.0,
    },
}


class RulesConfig:
    """Load shared deterministic rule packs from YAML."""

    def __init__(self, rules_path: str | None = None):
        configured = rules_path or os.getenv("RULES_POLICY_FILE", "config/rules/base.yaml")
        self.rules_path = Path(configured)
        self.rules = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.rules_path.exists():
            return DEFAULT_RULES.copy()
        try:
            loaded = yaml.safe_load(self.rules_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return DEFAULT_RULES.copy()
        merged = DEFAULT_RULES.copy()
        for section, values in loaded.items():
            if isinstance(values, dict) and isinstance(merged.get(section), dict):
                merged[section] = {**merged[section], **values}
            else:
                merged[section] = values
        return merged

    def signal_map(self, name: str) -> dict[str, tuple[str, ...]]:
        section = self.rules.get(name, {})
        if not isinstance(section, dict):
            return {}
        return {
            str(label): tuple(str(signal) for signal in signals)
            for label, signals in section.items()
            if isinstance(signals, list)
        }

    def confidence(self) -> dict[str, float]:
        section = self.rules.get("confidence", {})
        return section if isinstance(section, dict) else {}


_rules_config: RulesConfig | None = None


def get_rules_config() -> RulesConfig:
    global _rules_config
    if _rules_config is None:
        _rules_config = RulesConfig()
    return _rules_config
