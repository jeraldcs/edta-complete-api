from typing import Any

from app.models import CustomerContext
from app.profile.adapters.base import ProfileLookupAdapter
from app.profile.factory import build_profile_adapter


class ProfileLookupService:
    """Customer profile lookup facade with pluggable adapters."""

    def __init__(self, adapter: ProfileLookupAdapter | None = None):
        self.adapter = adapter or build_profile_adapter()

    @staticmethod
    def _merge_dict(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        merged.update(overlay)
        return merged

    @staticmethod
    def _merge_transactions(
        profile_transactions: list[dict[str, Any]],
        request_transactions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        import json

        seen = set()
        merged = []
        for item in [*request_transactions, *profile_transactions]:
            key = json.dumps(item, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                merged.append(item)
        return merged

    def enrich_context(self, context: CustomerContext) -> tuple[CustomerContext, dict[str, Any]]:
        if not context.customer_id:
            return context, {
                "profile_lookup": "skipped",
                "reason": "missing_customer_id",
                "customer_id": None,
                "fields_merged": [],
                "adapter": self.adapter.adapter_name,
            }

        if context.consent.get("profile_lookup") is False:
            return context, {
                "profile_lookup": "skipped",
                "reason": "profile_lookup_consent_false",
                "customer_id": context.customer_id,
                "fields_merged": [],
                "adapter": self.adapter.adapter_name,
            }

        profile = self.adapter.lookup(context.customer_id)
        if not profile:
            return context, {
                "profile_lookup": "not_found",
                "reason": "no_profile_record",
                "customer_id": context.customer_id,
                "fields_merged": [],
                "adapter": self.adapter.adapter_name,
            }

        fields_merged = []
        update: dict[str, Any] = {}

        for field in ["profile_attributes", "business_context", "channel_context", "device_context", "consent"]:
            profile_value = profile.get(field)
            if isinstance(profile_value, dict):
                request_value = getattr(context, field)
                update[field] = self._merge_dict(profile_value, request_value)
                fields_merged.append(field)

        profile_transactions = profile.get("past_transactions")
        if isinstance(profile_transactions, list):
            update["past_transactions"] = self._merge_transactions(
                profile_transactions,
                context.past_transactions,
            )
            fields_merged.append("past_transactions")

        enriched = context.model_copy(update=update)
        return enriched, {
            "profile_lookup": "enriched",
            "reason": "profile_record_merged",
            "customer_id": context.customer_id,
            "source": self.adapter.source_label,
            "adapter": self.adapter.adapter_name,
            "fields_merged": fields_merged,
        }
