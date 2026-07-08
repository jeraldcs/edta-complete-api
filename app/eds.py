from app.models import EDSBreakdown, IntentType, JourneyStage


class EDSScoringEngine:
    def score(self, context, candidate, graph, intent_label: str, journey_label: str):
        reasons = []

        try:
            intent = IntentType(intent_label)
        except Exception:
            intent = IntentType.unknown

        try:
            journey = JourneyStage(journey_label)
        except Exception:
            journey = context.journey_stage or JourneyStage.research

        intent_score = 1.0 if intent in candidate.intent_tags else 0.2
        if intent_score == 1.0:
            reasons.append("intent_match")

        engagement_score = min(1.0, len(context.session_events) * 0.12 + len(context.search_terms) * 0.18)
        engagement_score = max(0.2, engagement_score)
        if len(context.session_events) >= 3:
            reasons.append("high_session_engagement")

        business_score = candidate.business_value * 0.5 + candidate.margin_weight * 0.3 + candidate.inventory_weight * 0.2
        if business_score > 0.7:
            reasons.append("high_business_value")

        journey_score = 1.0 if journey in candidate.journey_tags else 0.4
        if journey_score == 1.0:
            reasons.append("journey_stage_match")

        graph_words = graph.keywords()
        candidate_words = set()
        for tag in candidate.content_tags:
            candidate_words.update(tag.lower().replace("_", " ").split())
        overlap = graph_words.intersection(candidate_words)
        context_score = max(0.2, min(1.0, len(overlap) / max(1, len(candidate_words))))
        if overlap:
            reasons.append("context_overlap:" + ",".join(sorted(overlap)))

        risk_adjustment = 0.0
        if not context.consent.get("personalization", False):
            risk_adjustment = 0.5
            reasons.append("personalization_consent_missing")
        elif candidate.compliance_sensitivity >= 0.7:
            risk_adjustment = 0.1
            reasons.append("compliance_sensitive_content")

        final = (
            intent_score * 0.25
            + engagement_score * 0.15
            + business_score * 0.20
            + journey_score * 0.20
            + context_score * 0.20
            - risk_adjustment
        )
        final = max(0.0, min(1.0, final))

        return EDSBreakdown(
            intent_score=round(intent_score, 4),
            engagement_score=round(engagement_score, 4),
            business_value_score=round(business_score, 4),
            journey_momentum_score=round(journey_score, 4),
            context_relevance_score=round(context_score, 4),
            risk_adjustment=round(risk_adjustment, 4),
            final_eds_score=round(final, 4),
        ), reasons
