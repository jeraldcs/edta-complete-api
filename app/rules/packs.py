from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.models import CustomerContext


@dataclass(frozen=True)
class RulePack:
    id: str
    domain: str
    priority: int
    enabled: bool
    aliases: tuple[str, ...] = ()
    intent_signals: dict[str, tuple[str, ...]] = field(default_factory=dict)
    journey_signals: dict[str, tuple[str, ...]] = field(default_factory=dict)
    channel_event_boosts: dict[str, tuple[str, ...]] = field(default_factory=dict)
    rules: tuple[dict[str, Any], ...] = ()


class RulePackRegistry:
    """Load prioritized domain rule packs from config/rules/."""

    def __init__(self, rules_root: str | Path | None = None):
        configured = rules_root or os.getenv("RULES_INDEX_FILE", "config/rules/index.yaml")
        self.index_path = Path(configured)
        self.rules_root = self.index_path.parent
        self.packs = self._load_packs()

    def _load_packs(self) -> list[RulePack]:
        if not self.index_path.exists():
            return []
        try:
            index = yaml.safe_load(self.index_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return []

        packs_dir = self.rules_root / str(index.get("packs_dir", "packs"))
        loaded: list[RulePack] = []
        for entry in index.get("packs", []):
            if not isinstance(entry, dict):
                continue
            pack_id = str(entry.get("id", "unknown"))
            enabled = bool(entry.get("enabled", True))
            if not enabled:
                continue
            file_name = str(entry.get("file", f"{pack_id}.yaml"))
            pack_path = packs_dir / file_name if not file_name.startswith("base") else self.rules_root / file_name
            if not pack_path.exists() and file_name != "base.yaml":
                pack_path = self.rules_root / file_name
            pack_data: dict[str, Any] = {}
            if pack_path.exists():
                try:
                    pack_data = yaml.safe_load(pack_path.read_text(encoding="utf-8")) or {}
                except (OSError, yaml.YAMLError):
                    pack_data = {}
            loaded.append(
                RulePack(
                    id=pack_id,
                    domain=str(entry.get("domain", pack_data.get("domain", "*"))),
                    priority=int(entry.get("priority", pack_data.get("priority", 0))),
                    enabled=True,
                    aliases=tuple(str(item) for item in (entry.get("aliases") or pack_data.get("aliases") or [])),
                    intent_signals=self._signal_map(pack_data.get("intent_signals")),
                    journey_signals=self._signal_map(pack_data.get("journey_signals")),
                    channel_event_boosts=self._signal_map(pack_data.get("channel_event_boosts")),
                    rules=tuple(item for item in (pack_data.get("rules") or []) if isinstance(item, dict)),
                )
            )
        loaded.sort(key=lambda pack: pack.priority, reverse=True)
        return loaded

    @staticmethod
    def _signal_map(section: Any) -> dict[str, tuple[str, ...]]:
        if not isinstance(section, dict):
            return {}
        return {
            str(label): tuple(str(signal) for signal in signals)
            for label, signals in section.items()
            if isinstance(signals, list)
        }

    @staticmethod
    def detect_domain(context: CustomerContext) -> str | None:
        for source in (context.business_context, context.profile_attributes, context.channel_context):
            if not isinstance(source, dict):
                continue
            for key in ("detected_domain", "training_domain", "domain"):
                value = source.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().lower()
        return None

    def active_packs(self, context: CustomerContext) -> list[RulePack]:
        domain = self.detect_domain(context)
        active: list[RulePack] = []
        for pack in self.packs:
            if pack.domain == "*":
                active.append(pack)
                continue
            if domain is None:
                continue
            if domain == pack.domain or domain in pack.aliases:
                active.append(pack)
        if not any(pack.domain != "*" for pack in active):
            return [pack for pack in self.packs if pack.domain == "*"]
        return active

    def merged_signal_maps(self, context: CustomerContext) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
        intent: dict[str, tuple[str, ...]] = {}
        journey: dict[str, tuple[str, ...]] = {}
        channel: dict[str, tuple[str, ...]] = {}
        for pack in reversed(self.active_packs(context)):
            for label, signals in pack.intent_signals.items():
                intent[label] = intent.get(label, ()) + signals
            for label, signals in pack.journey_signals.items():
                journey[label] = journey.get(label, ()) + signals
            for label, signals in pack.channel_event_boosts.items():
                channel[label] = channel.get(label, ()) + signals
        return intent, journey, channel

    def explicit_rules(self, context: CustomerContext) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []
        for pack in self.active_packs(context):
            for rule in pack.rules:
                rules.append({**rule, "pack_id": pack.id, "pack_priority": pack.priority})
        rules.sort(key=lambda item: int(item.get("priority", 0)), reverse=True)
        return rules

    def provider_name(self, context: CustomerContext) -> str:
        domain = self.detect_domain(context)
        if domain:
            return f"rules.{domain}"
        return "rules.base"


_registry: RulePackRegistry | None = None


def get_rule_pack_registry() -> RulePackRegistry:
    global _registry
    if _registry is None:
        _registry = RulePackRegistry()
    return _registry
