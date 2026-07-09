from __future__ import annotations

INTENT_JSON_SCHEMA = """
{
  "intent": "research|purchase|support|retention|upgrade|unknown",
  "confidence": 0.0,
  "journey_stage": "awareness|research|consideration|purchase|service|retention",
  "reason": "short reason"
}
""".strip()


def enrich_intent_prompt(context_text: str) -> str:
    return f"""
Analyze this customer session context and return JSON only.

Context:
{context_text}

Return exactly this schema:
{INTENT_JSON_SCHEMA}
""".strip()


def explain_recommendation_prompt(context_text: str, recommendation_payload: dict) -> str:
    import json

    return f"""
Explain why this recommendation was selected in simple enterprise architecture language.

Customer context:
{context_text}

Recommendation payload:
{json.dumps(recommendation_payload, indent=2)}

Rules:
- Under 70 words.
- Mention intent, journey, TAPL governance, expected outcome, and business value if relevant.
- Do not invent facts.
""".strip()


def synthetic_training_prompt(domain: str, count: int) -> str:
    return f"""
Generate {count} synthetic intent-classification training records for the {domain} domain.
Return JSON array only. Each item must have: text, intent.
Allowed intents: research, purchase, support, retention, upgrade, unknown.
""".strip()


def parse_scenario_prompt(scenario_text: str) -> str:
    return f"""
Convert this free-text customer scenario into JSON only.

Scenario:
{scenario_text}

Return exactly this schema:
{{
  "customer_id": "string or null",
  "anonymous_id": "string or null",
  "channel": "web|mobile|email|sms|push|in_app|call_center|chatbot|voice_assistant|iot|wearable|connected_car|kiosk|smart_tv|ar_vr|social|marketplace|partner_api",
  "journey_stage": "awareness|research|consideration|purchase|service|retention|null",
  "current_intent": "research|purchase|support|retention|upgrade|unknown|null",
  "session_events": ["short_event_names"],
  "search_terms": ["short search phrases"],
  "profile_attributes": {{}},
  "business_context": {{}},
  "channel_context": {{}},
  "device_context": {{}},
  "consent": {{"personalization": true, "profile_lookup": true}},
  "confidence": 0.0,
  "parse_reason": "short reason"
}}

Rules:
- Infer only from the scenario.
- Use snake_case event names.
- Keep arrays concise.
- If consent is explicitly missing or opted out, set personalization false.
""".strip()
