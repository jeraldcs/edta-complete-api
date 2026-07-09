from __future__ import annotations

from typing import Any

from app.eml_policy import EMLPolicyEngine
from app.models import Channel, RecommendationCandidate


def preference_adjustment(
    preferences: dict[str, Any] | None,
    candidate: RecommendationCandidate,
    channel: Channel,
    policy: EMLPolicyEngine | None = None,
) -> tuple[float, list[str]]:
    """Return a score delta from learned EML preferences for ranking."""
    if not preferences:
        return 0.0, []

    policy = policy or EMLPolicyEngine()
    ranking = policy.section("ranking")
    adjustment = 0.0
    reasons: list[str] = []

    candidate_pref = preferences.get(f"candidate:{candidate.id}", {})
    candidate_weight = float(candidate_pref.get("weight", 0.0) if isinstance(candidate_pref, dict) else 0.0)
    if candidate_weight:
        delta = candidate_weight * float(ranking.get("candidate_weight_scale", 0.04))
        adjustment += delta
        reasons.append("eml_candidate_preference")

    channel_pref = preferences.get(f"channel:{channel.value}", {})
    channel_weight = float(channel_pref.get("weight", 0.0) if isinstance(channel_pref, dict) else 0.0)
    if channel_weight:
        delta = channel_weight * float(ranking.get("channel_weight_scale", 0.02))
        adjustment += delta
        reasons.append("eml_channel_preference")

    type_pref = preferences.get(f"type:{candidate.type}", {})
    type_weight = float(type_pref.get("weight", 0.0) if isinstance(type_pref, dict) else 0.0)
    if type_weight:
        delta = type_weight * float(ranking.get("type_weight_scale", 0.02))
        adjustment += delta
        reasons.append("eml_type_preference")

    category_scale = float(ranking.get("category_weight_scale", 0.015))
    for tag in candidate.content_tags[:3]:
        category_pref = preferences.get(f"category:{tag.lower()}", {})
        category_weight = float(category_pref.get("weight", 0.0) if isinstance(category_pref, dict) else 0.0)
        if category_weight:
            adjustment += category_weight * category_scale
            reasons.append("eml_category_preference")

    max_boost = float(ranking.get("max_preference_boost", 0.12))
    max_penalty = float(ranking.get("max_preference_penalty", -0.15))
    adjustment = max(max_penalty, min(max_boost, round(adjustment, 4)))
    return adjustment, reasons
