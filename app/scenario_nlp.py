import re
from typing import Any

from app.llm.llm_client import LLMClient
from app.models import Channel, CustomerContext, IntentType, JourneyStage


class ScenarioNLPParser:
    """Free-text scenario parser for the demo UI.

    It can ask the optional LLM for structured context, then falls back to a
    deterministic keyword parser so the page works without external services.
    """

    def __init__(self):
        self.llm = LLMClient()
        self.stop_words = {
            "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "he", "her",
            "his", "i", "in", "is", "it", "of", "on", "or", "she", "that", "the", "their",
            "they", "this", "to", "using", "was", "with", "website", "page", "user",
            "customer", "unknown", "someone", "then", "form", "from", "accessing", "reading", "viewing", "looking",
            "sitting", "siiting",
        }
        self.domain_terms = {
            "healthcare": {"healthcare", "doctor", "physician", "hcp", "clinical", "medical", "patient", "therapy", "obesity", "diabetes", "product"},
            "lodging": {"hotel", "room", "stay", "lodging", "reservation", "booking", "availability"},
            "banking": {"bank", "banking", "credit", "card", "loan", "mortgage", "finance", "financial", "rewards", "rate", "application", "eligibility"},
            "restaurant": {"restaurant", "restaurent", "restuarent", "table", "dining", "food", "cuisine", "menu", "dish", "meal", "reservation", "booking", "barcode", "qr"},
            "travel": {"travel", "rental", "airport", "suv", "vehicle", "car", "booking", "reservation", "trip", "family"},
            "iot": {"iot", "device", "sensor", "battery", "firmware", "maintenance", "alert"},
            "wearable": {"wearable", "watch", "smartwatch", "wellness", "reminder", "notification"},
            "support": {"support", "help", "issue", "problem", "service", "case"},
        }

    def parse(self, scenario_text: str, use_llm: bool = False) -> tuple[CustomerContext, dict[str, Any]]:
        if use_llm:
            parsed = self.llm.parse_scenario_context(scenario_text)
            context = self._context_from_llm(parsed) if parsed else None
            if context:
                return context, {
                    "parser": "llm",
                    "llm_enabled": self.llm.enabled,
                    "llm_status": self.llm.status(),
                    "llm_fallback": False,
                    "reason": parsed.get("parse_reason", "scenario parsed by LLM"),
                    "parser_confidence": context.channel_context.get("parser_confidence", 0.85),
                }

        context, details = self._heuristic_parse(scenario_text)
        details["llm_enabled"] = self.llm.enabled
        details["llm_status"] = self.llm.status()
        if use_llm:
            details["llm_fallback"] = True
            details["llm_fallback_reason"] = (
                self.llm.last_error
                or "LLM parsing was requested but no valid LLM context was returned."
            )
        return context, details

    def _context_from_llm(self, parsed: dict[str, Any] | None) -> CustomerContext | None:
        if not isinstance(parsed, dict):
            return None
        try:
            channel_context = dict(parsed.get("channel_context") or {})
            channel_context.setdefault("source", "free_text_scenario")
            try:
                channel_context["parser_confidence"] = round(
                    max(0.0, min(1.0, float(parsed.get("confidence", 0.85)))),
                    4,
                )
            except (TypeError, ValueError):
                channel_context["parser_confidence"] = 0.85
            return CustomerContext(**{
                "customer_id": parsed.get("customer_id"),
                "anonymous_id": parsed.get("anonymous_id") or "scenario-user",
                "channel": parsed.get("channel") or Channel.web.value,
                "journey_stage": parsed.get("journey_stage"),
                "current_intent": parsed.get("current_intent"),
                "session_events": parsed.get("session_events") or [],
                "search_terms": parsed.get("search_terms") or [],
                "profile_attributes": parsed.get("profile_attributes") or {},
                "business_context": parsed.get("business_context") or {},
                "channel_context": channel_context,
                "device_context": parsed.get("device_context") or {},
                "consent": parsed.get("consent") or {"personalization": True, "profile_lookup": True},
            })
        except Exception:
            return None

    @staticmethod
    def _estimate_parser_confidence(
        domain: str,
        intent: IntentType,
        journey: JourneyStage,
        keywords: list[str],
        search_terms: list[str],
    ) -> float:
        score = 0.45
        if domain and domain != "general":
            score += 0.15
        if intent != IntentType.unknown:
            score += 0.2
        if journey is not None:
            score += 0.1
        if len(keywords) >= 4:
            score += 0.1
        elif len(keywords) >= 2:
            score += 0.05
        if search_terms:
            score += 0.05
        return round(min(0.95, score), 4)

    def _heuristic_parse(self, scenario_text: str) -> tuple[CustomerContext, dict[str, Any]]:
        text = scenario_text.strip()
        lower = text.lower()
        keywords = self._extract_keywords(text)
        domain = self._infer_domain(keywords)

        channel = self._infer_channel(lower)
        intent = self._infer_intent(lower, keywords, domain)
        journey = self._infer_journey(lower, intent)
        customer_id = self._find_customer_id(text)
        events = self._infer_events(lower, keywords, domain)

        profile = self._infer_profile(lower, keywords, domain)
        business = self._infer_business_context(lower, keywords, domain)
        channel_context = self._infer_channel_context(lower, channel, keywords, domain)
        device_context = self._infer_device_context(lower, channel)
        consent = {
            "personalization": not any(
                term in lower
                for term in [
                    "no personalization",
                    "opted out",
                    "without consent",
                    "consent false",
                    "consent is false",
                    "consent: false",
                    "personalization consent false",
                    "personalization false",
                    "personalization consent is false",
                ]
            ),
            "profile_lookup": "no profile lookup" not in lower,
        }
        search_terms = self._search_terms(text, keywords)

        context = CustomerContext(
            anonymous_id="scenario-user",
            customer_id=customer_id,
            channel=channel,
            journey_stage=journey,
            current_intent=intent,
            session_events=events,
            search_terms=search_terms,
            profile_attributes=profile,
            business_context=business,
            channel_context=channel_context,
            device_context=device_context,
            consent=consent,
        )
        parser_confidence = self._estimate_parser_confidence(domain, intent, journey, keywords, search_terms)
        context = context.model_copy(update={
            "channel_context": {
                **channel_context,
                "source": "free_text_scenario",
                "parser_confidence": parser_confidence,
            },
        })
        return context, {
            "parser": "keyword_heuristic",
            "reason": "scenario converted using channel, intent, journey, profile, and context keywords",
            "detected_channel": channel.value,
            "detected_intent": intent.value,
            "detected_journey_stage": journey.value,
            "detected_domain": domain,
            "keywords": keywords,
            "parser_confidence": parser_confidence,
        }

    @staticmethod
    def _find_customer_id(text: str) -> str | None:
        match = re.search(r"\b(?:customer|cust(?:omer)?[-_\s]*id)?\s*(cust[-_][a-z0-9-]+)\b", text, re.IGNORECASE)
        if match:
            return match.group(1).replace("_", "-")
        return None

    @staticmethod
    def _infer_channel(lower: str) -> Channel:
        checks = [
            (Channel.chatbot, ["chatbot", "chat bot", "chat", "conversation"]),
            (Channel.iot, ["iot", "sensor", "device", "firmware", "low battery"]),
            (Channel.wearable, ["wearable", "watch", "smartwatch"]),
            (Channel.connected_car, ["connected car", "vehicle dashboard", "in-car"]),
            (Channel.mobile, ["mobile app", "phone app", "iphone", "android", "mobile", "barcode", "qr code", "qr"]),
            (Channel.email, ["email"]),
            (Channel.sms, ["sms", "text message"]),
            (Channel.call_center, ["call center", "agent", "phone call"]),
            (Channel.web, ["web", "website", "page", "browser", "landing page"]),
        ]
        for channel, keywords in checks:
            if any(keyword in lower for keyword in keywords):
                return channel
        return Channel.web

    @staticmethod
    def _infer_intent(lower: str, keywords: list[str], domain: str) -> IntentType:
        if any(term in lower for term in ["upgrade", "premium", "larger", "better vehicle"]):
            return IntentType.upgrade
        if (
            domain == "restaurant"
            and "menu" in keywords
            and (
                {"table", "meal", "dish"}.intersection(keywords)
                or any(term in lower for term in ["sitting", "siiting", "at the restaurant", "in the restaurant", "barcode", "qr code", "qr"])
            )
        ):
            return IntentType.purchase
        if any(term in lower for term in ["book", "booking", "reservation", "reserve", "checkout", "buy", "purchase", "started booking", "apply", "application"]):
            return IntentType.purchase
        if any(term in lower for term in ["support", "help", "issue", "problem", "maintenance", "service", "change reservation"]):
            return IntentType.support
        if any(term in lower for term in ["renew", "retain", "loyalty", "churn", "cancel"]):
            return IntentType.retention
        if any(term in lower for term in ["research", "compare", "compares", "comparing", "search", "searches", "searching", "browse", "browses", "browsing", "looking for", "reading", "accessing", "reviewing", "viewing", "view menu", "menu"]):
            return IntentType.research
        return IntentType.unknown

    @staticmethod
    def _infer_journey(lower: str, intent: IntentType) -> JourneyStage:
        if any(term in lower for term in ["started booking", "checkout", "ready to book", "reserve"]):
            return JourneyStage.purchase
        if intent == IntentType.purchase:
            return JourneyStage.purchase
        if any(term in lower for term in ["compare", "compares", "comparing", "availability", "considering", "vehicle page", "reservation", "hotel", "restaurant", "credit card", "loan", "mortgage"]):
            return JourneyStage.consideration
        if intent == IntentType.support:
            return JourneyStage.service
        if intent == IntentType.retention:
            return JourneyStage.retention
        if intent == IntentType.research:
            return JourneyStage.research
        if intent == IntentType.upgrade:
            return JourneyStage.consideration
        return JourneyStage.research

    def _infer_events(self, lower: str, keywords: list[str], domain: str) -> list[str]:
        mappings = [
            ("viewed_healthcare_site", ["healthcare website", "hcp website", "medical website"]),
            ("read_obesity_product_content", ["obesity", "obesity products", "obesity product"]),
            ("viewed_clinical_content", ["doctor", "physician", "hcp", "clinical"]),
            ("viewed_vehicle_page", ["vehicle page", "car page", "suv page"]),
            ("viewed_hotel_reservation_page", ["hotel", "reservation", "room", "lodging"]),
            ("viewed_banking_product_page", ["bank", "banking", "credit card", "loan", "mortgage"]),
            ("viewed_restaurant_page", ["restaurant", "dining", "menu", "cuisine"]),
            ("scanned_restaurant_qr_menu", ["barcode", "qr code", "qr", "scanning"]),
            ("checked_table_availability", ["table", "reservation", "availability"]),
            ("searched_suv", ["suv"]),
            ("checked_location_availability", ["availability", "available", "location"]),
            ("started_booking", ["started booking", "reserve", "checkout", "book"]),
            ("opened_chatbot", ["chatbot", "chat"]),
            ("asked_about_booking", ["booking", "reservation"]),
            ("device_low_battery", ["low battery", "battery"]),
            ("maintenance_due", ["maintenance", "service due"]),
            ("short_notification_window", ["wearable", "watch", "notification"]),
        ]
        events = [event for event, keywords in mappings if any(keyword in lower for keyword in keywords)]
        if domain != "general":
            events.append(f"identified_{domain}_context")
        for keyword in keywords[:6]:
            dynamic_event = f"keyword_{keyword}"
            if dynamic_event not in events:
                events.append(dynamic_event)
        return events or ["described_scenario"]

    def _infer_profile(self, lower: str, keywords: list[str], domain: str) -> dict[str, Any]:
        profile: dict[str, Any] = {"scenario_keywords": keywords, "detected_domain": domain}
        if "preferred" in lower:
            profile["loyalty_tier"] = "preferred"
        if "gold" in lower:
            profile["loyalty_tier"] = "gold"
        if "family" in lower:
            profile["trip_type"] = "family"
            profile["family_traveler"] = True
        if "business trip" in lower:
            profile["trip_type"] = "business"
        if {"doctor", "physician", "hcp"}.intersection(keywords) or "healthcare professional" in lower:
            profile["audience_type"] = "hcp"
            profile["profession"] = "doctor"
        therapeutic_keywords = [term for term in ["obesity", "diabetes", "cardiology", "oncology"] if term in keywords]
        if therapeutic_keywords:
            profile["therapeutic_interest"] = therapeutic_keywords[0]
        fatigue = re.search(r"fatigue(?: count)?\s*(?:is|=|:)?\s*(\d+)", lower)
        if fatigue:
            profile["fatigue_count"] = int(fatigue.group(1))
            profile["parsed_fatigue_count"] = True
        elif any(
            term in lower
            for term in [
                "high fatigue",
                "fatigued",
                "ad fatigue",
                "many ads",
                "bombarded",
                "overwhelmed by ads",
                "too many recommendations",
            ]
        ):
            profile["fatigue_count"] = 8
            profile["parsed_fatigue_count"] = True
        elif any(term in lower for term in ["some fatigue", "tired of ads", "repeated exposure", "seen too many"]):
            profile["fatigue_count"] = 5
            profile["parsed_fatigue_count"] = True
        if any(term in lower for term in ["distrust", "skeptical", "low trust", "privacy concerned", "do not trust"]):
            profile["trust_score"] = 0.38
            profile["parsed_trust_score"] = True
        elif any(term in lower for term in ["first time", "first-time", "new customer", "nervous", "beginner"]):
            profile["trust_score"] = 0.45
            profile["parsed_trust_score"] = True
        elif "gold" in lower:
            profile["trust_score"] = 0.90
            profile["parsed_trust_score"] = True
        elif "preferred" in lower or "loyalty" in lower:
            profile["trust_score"] = 0.82
            profile["parsed_trust_score"] = True
        return profile

    def _infer_business_context(self, lower: str, keywords: list[str], domain: str) -> dict[str, Any]:
        context: dict[str, Any] = {"detected_domain": domain, "scenario_keywords": keywords}
        if "suv" in keywords:
            context["inventory_suv"] = "available" if "not available" not in lower else "unavailable"
        if "summer" in keywords:
            context["season"] = "summer"
        if "high value" in lower:
            context["customer_value_segment"] = "high"
        if domain == "healthcare":
            context["industry"] = "healthcare"
        if domain == "lodging":
            context["industry"] = "hospitality"
            context["content_category"] = "hotel_reservation"
        if domain == "banking":
            context["industry"] = "financial_services"
            context["content_category"] = "banking_product"
        if domain == "restaurant":
            context["industry"] = "restaurant"
            context["content_category"] = "qr_menu" if {"barcode", "qr"}.intersection(keywords) else "restaurant_menu" if "menu" in keywords else "dining_reservation"
        if "hotel" in keywords:
            context["product_category"] = "hotel"
        if "credit" in keywords or "card" in keywords:
            context["product_category"] = "credit_card"
        if "loan" in keywords or "mortgage" in keywords:
            context["product_category"] = "loan"
        if "restaurant" in keywords or "restaurent" in keywords or "restuarent" in keywords or "dining" in keywords:
            context["product_category"] = "restaurant"
        if "obesity" in keywords:
            context["therapeutic_area"] = "obesity"
        if "product" in keywords:
            context["content_category"] = "product_education"
        return context

    @staticmethod
    def _infer_channel_context(lower: str, channel: Channel, keywords: list[str], domain: str) -> dict[str, Any]:
        context: dict[str, Any] = {
            "source": "free_text_scenario",
            "detected_domain": domain,
            "scenario_keywords": keywords,
        }
        if channel == Channel.web:
            if domain == "healthcare":
                context["page_type"] = "hcp_product_content"
            elif domain == "lodging":
                context["page_type"] = "hotel_reservation"
            elif domain == "banking":
                context["page_type"] = "banking_product"
            elif domain == "restaurant":
                context["page_type"] = "restaurant_qr_menu" if "barcode" in keywords or "qr" in keywords else "restaurant_menu" if "menu" in keywords else "restaurant_reservation"
            else:
                context["page_type"] = "vehicle_detail" if "vehicle" in lower or "suv" in lower else "landing_page"
        if channel == Channel.chatbot:
            context["conversation_turn"] = 3
        if channel in {Channel.iot, Channel.wearable}:
            context["max_notification_length"] = 80
        return context

    @staticmethod
    def _infer_device_context(lower: str, channel: Channel) -> dict[str, Any]:
        if channel == Channel.wearable:
            return {"device": "smart_watch"}
        if channel == Channel.iot:
            return {"device_type": "connected_device"}
        if channel == Channel.mobile:
            return {"device_type": "mobile", "interaction": "qr_or_barcode_scan" if "barcode" in lower or "qr" in lower else "mobile_browse"}
        return {"device_type": "desktop"}

    @staticmethod
    def _search_phrase(text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.strip())
        return cleaned[:180]

    def _extract_keywords(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
        normalized = []
        for token in tokens:
            token = token.replace("-", "_")
            if token in {"restaurent", "restuarent"}:
                token = "restaurant"
            if token.endswith("s") and not token.endswith("ss") and len(token) > 4:
                token = token[:-1]
            if len(token) < 3 or token in self.stop_words:
                continue
            if token not in normalized:
                normalized.append(token)
        return normalized[:24]

    def _infer_domain(self, keywords: list[str]) -> str:
        keyword_set = set(keywords)
        scores = {
            domain: len(keyword_set.intersection(terms))
            for domain, terms in self.domain_terms.items()
        }
        best_domain, best_score = max(scores.items(), key=lambda item: item[1])
        return best_domain if best_score > 0 else "general"

    def _search_terms(self, text: str, keywords: list[str]) -> list[str]:
        terms = [self._search_phrase(text)]
        if keywords:
            terms.append(" ".join(keywords[:8]))
        return terms
