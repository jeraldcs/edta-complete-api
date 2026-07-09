from app.config import settings
from app.db import Database
from app.events import EventBus, JobStore
from app.experience_memory import ExperienceMemoryLayer
from app.feedback_store import FeedbackStore
from app.graph_store import GraphStore
from app.profile_service import ProfileLookupService
from app.provider_telemetry import ProviderTelemetryStore
from app.recommender import RecommendationEngine
from app.rules_audit import RulesAuditLog
from app.scenario_nlp import ScenarioNLPParser
from app.tapl_audit import TAPLAuditLog


class ServiceContainer:
    """Shared application services for route handlers."""

    def __init__(self) -> None:
        self.database = Database(str(settings.edta_db_path))
        self.graph_store = GraphStore(self.database)
        self.tapl_audit = TAPLAuditLog(self.database)
        self.rules_audit = RulesAuditLog(self.database)
        self.provider_telemetry = ProviderTelemetryStore(self.database)
        self.engine = RecommendationEngine(
            tapl_audit=self.tapl_audit,
            rules_audit=self.rules_audit,
            provider_telemetry=self.provider_telemetry,
        )
        self.llm_client = self.engine.llm
        self.profile_service = ProfileLookupService()
        self.scenario_parser = ScenarioNLPParser()
        self.experience_memory = ExperienceMemoryLayer(
            memory_path=str(settings.experience_memory_file),
            db_path=str(settings.edta_db_path),
        )
        self.feedback_store = FeedbackStore(str(settings.feedback_store_file))
        self.event_bus = EventBus(self.database)
        self.job_store = JobStore(self.database)


container = ServiceContainer()
