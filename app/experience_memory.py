import os
from pathlib import Path

from app.db import Database
from app.eml_store import EMLStore
from app.models import CustomerContext, ExperienceMemorySnapshot, FeedbackEvent


class ExperienceMemoryLayer:
    """Persistent memory for anonymous and known-user personalization state."""

    def __init__(self, memory_path: str | None = None, db_path: str | None = None):
        legacy_path = memory_path or os.getenv("EXPERIENCE_MEMORY_FILE", "data/experience_memory.json")
        self.store = EMLStore(
            db=Database(db_path or os.getenv("EDTA_DB_PATH", "data/edta.db")),
            legacy_json_path=Path(legacy_path),
        )

    @staticmethod
    def subject_key(context: CustomerContext | FeedbackEvent) -> tuple[str, str]:
        return EMLStore.subject_key(context)

    def resolve_subject(self, context: CustomerContext | FeedbackEvent) -> tuple[str, str]:
        return self.store.resolve_subject(context)

    def get_snapshot(self, context: CustomerContext) -> ExperienceMemorySnapshot:
        return self.store.get_snapshot(context)

    def get_calibration(self, context: CustomerContext) -> dict[str, float]:
        return self.store.get_calibration(context)

    def enrich_context(self, context: CustomerContext) -> tuple[CustomerContext, ExperienceMemorySnapshot]:
        snapshot = self.get_snapshot(context)
        attrs = dict(context.profile_attributes)
        attrs.setdefault("trust_score", snapshot.trust_score)
        attrs.setdefault("fatigue_count", round(snapshot.fatigue_score * 10))
        attrs["experience_memory_subject"] = snapshot.subject_id
        attrs["experience_memory_type"] = snapshot.subject_type
        if snapshot.preferences:
            attrs["experience_preferences"] = snapshot.preferences
        return context.model_copy(update={"profile_attributes": attrs}), snapshot

    def record_recommendations(self, context: CustomerContext, recommendations: list) -> ExperienceMemorySnapshot:
        return self.store.record_recommendations(context, recommendations)

    def record_feedback(self, event: FeedbackEvent) -> ExperienceMemorySnapshot:
        return self.store.record_feedback(event)

    def is_writable(self) -> bool:
        return self.store.is_writable()
