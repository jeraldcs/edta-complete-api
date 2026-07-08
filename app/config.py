import os
from pathlib import Path


def _split_origins(value: str) -> list[str]:
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins or ["*"]


class Settings:
    """Runtime configuration loaded from environment variables."""

    api_key: str | None
    cors_origins: list[str]
    edta_db_path: Path
    experience_memory_file: Path
    feedback_store_file: Path
    distilled_slm_file: Path
    profile_lookup_file: Path
    tapl_policy_file: Path
    profile_lookup_adapter: str
    rate_limit_per_minute: int
    webhook_timeout_seconds: float

    required_models: tuple[str, ...] = (
        "models/intent_model.joblib",
        "models/journey_model.joblib",
        "models/tapl_model.joblib",
        "models/outcome_conversion_model.joblib",
        "models/outcome_revenue_model.joblib",
        "models/final_ranker_model.joblib",
    )

    def __init__(self) -> None:
        self.api_key = os.getenv("EDTA_API_KEY") or None
        self.cors_origins = _split_origins(os.getenv("EDTA_CORS_ORIGINS", "*"))
        self.edta_db_path = Path(os.getenv("EDTA_DB_PATH", "data/edta.db"))
        self.experience_memory_file = Path(
            os.getenv("EXPERIENCE_MEMORY_FILE", "data/experience_memory.json")
        )
        self.feedback_store_file = Path(
            os.getenv("FEEDBACK_STORE_FILE", "data/feedback_events.json")
        )
        self.distilled_slm_file = Path(
            os.getenv("DISTILLED_SLM_FILE", "data/distilled_slm_memory.json")
        )
        self.profile_lookup_file = Path(
            os.getenv("PROFILE_LOOKUP_FILE", "data/customer_profiles.json")
        )
        self.tapl_policy_file = Path(
            os.getenv("TAPL_POLICY_FILE", "config/tapl_policies.yaml")
        )
        self.profile_lookup_adapter = os.getenv("PROFILE_LOOKUP_ADAPTER", "json_file")
        self.rate_limit_per_minute = int(os.getenv("EDTA_RATE_LIMIT_PER_MINUTE", "120"))
        self.webhook_timeout_seconds = float(os.getenv("EDTA_WEBHOOK_TIMEOUT_SECONDS", "5.0"))
        self.environment = os.getenv("EDTA_ENVIRONMENT", "development").strip().lower()
        self.log_level = os.getenv("EDTA_LOG_LEVEL", "INFO")
        self.log_format = os.getenv("EDTA_LOG_FORMAT", "json").strip().lower()
        self.metrics_enabled = os.getenv("EDTA_METRICS_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        self.otel_enabled = os.getenv("OTEL_ENABLED", "false").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        self.otel_service_name = os.getenv("OTEL_SERVICE_NAME", "edta-api")
        self.otel_exporter_otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or None
        expose_errors = os.getenv("EDTA_EXPOSE_ERROR_DETAILS", "auto").strip().lower()
        if expose_errors == "auto":
            self.expose_error_details = self.environment != "production"
        else:
            self.expose_error_details = expose_errors in {"1", "true", "yes"}

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)


settings = Settings()
