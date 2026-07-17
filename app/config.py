from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_origins(value: str) -> list[str]:
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins or ["*"]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    api_key: str | None = Field(default=None, alias="EDTA_API_KEY")
    cors_origins_raw: str = Field(default="*", alias="EDTA_CORS_ORIGINS")
    edta_db_path: Path = Field(default=Path("data/edta.db"), alias="EDTA_DB_PATH")
    experience_memory_file: Path = Field(
        default=Path("data/experience_memory.json"),
        alias="EXPERIENCE_MEMORY_FILE",
    )
    feedback_store_file: Path = Field(
        default=Path("data/feedback_events.json"),
        alias="FEEDBACK_STORE_FILE",
    )
    distilled_slm_file: Path = Field(
        default=Path("data/distilled_slm_memory.json"),
        alias="DISTILLED_SLM_FILE",
    )
    profile_lookup_file: Path = Field(
        default=Path("data/customer_profiles.json"),
        alias="PROFILE_LOOKUP_FILE",
    )
    tapl_policy_file: Path = Field(
        default=Path("config/tapl_policies.yaml"),
        alias="TAPL_POLICY_FILE",
    )
    eml_policy_file: Path = Field(
        default=Path("config/eml_policies.yaml"),
        alias="EML_POLICY_FILE",
    )
    haoe_policy_file: Path = Field(
        default=Path("config/haoe_policies.yaml"),
        alias="HAOE_POLICY_FILE",
    )
    profile_lookup_adapter: str = Field(default="json_file", alias="PROFILE_LOOKUP_ADAPTER")
    rate_limit_per_minute: int = Field(default=120, alias="EDTA_RATE_LIMIT_PER_MINUTE")
    webhook_timeout_seconds: float = Field(default=5.0, alias="EDTA_WEBHOOK_TIMEOUT_SECONDS")
    environment: Literal["development", "production", "test"] = Field(
        default="development",
        alias="EDTA_ENVIRONMENT",
    )
    log_level: str = Field(default="INFO", alias="EDTA_LOG_LEVEL")
    log_format: Literal["json", "text"] = Field(default="json", alias="EDTA_LOG_FORMAT")
    metrics_enabled: bool = Field(default=True, alias="EDTA_METRICS_ENABLED")
    otel_enabled: bool = Field(default=False, alias="OTEL_ENABLED")
    otel_service_name: str = Field(default="edta-api", alias="OTEL_SERVICE_NAME")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        alias="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    expose_error_details_raw: str = Field(default="auto", alias="EDTA_EXPOSE_ERROR_DETAILS")
    expose_demo_api_key: bool = Field(default=True, alias="EDTA_EXPOSE_DEMO_API_KEY")
    idempotency_ttl_seconds: int = Field(default=86400, alias="EDTA_IDEMPOTENCY_TTL_SECONDS")

    required_models: tuple[str, ...] = (
        "models/intent_model.joblib",
        "models/journey_model.joblib",
        "models/tapl_model.joblib",
        "models/outcome_conversion_model.joblib",
        "models/outcome_revenue_model.joblib",
        "models/final_ranker_model.joblib",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value: object) -> str:
        text = str(value or "development").strip().lower()
        if text not in {"development", "production", "test"}:
            return "development"
        return text

    @field_validator("log_format", mode="before")
    @classmethod
    def normalize_log_format(cls, value: object) -> str:
        text = str(value or "json").strip().lower()
        return text if text in {"json", "text"} else "json"

    @field_validator("metrics_enabled", "otel_enabled", "expose_demo_api_key", mode="before")
    @classmethod
    def parse_bool(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes"}

    @model_validator(mode="after")
    def apply_production_defaults(self) -> "Settings":
        if self.environment == "production":
            if self.expose_demo_api_key:
                object.__setattr__(self, "expose_demo_api_key", False)
            if self.cors_origins_raw.strip() in {"", "*"}:
                object.__setattr__(self, "cors_origins_raw", "")
        return self

    @property
    def cors_origins(self) -> list[str]:
        if self.environment == "production" and not self.cors_origins_raw.strip():
            return []
        return _split_origins(self.cors_origins_raw)

    @property
    def cors_allow_credentials(self) -> bool:
        return "*" not in self.cors_origins

    @property
    def expose_error_details(self) -> bool:
        if self.expose_error_details_raw.strip().lower() == "auto":
            return self.environment != "production"
        return self.expose_error_details_raw.strip().lower() in {"1", "true", "yes"}

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)

    def validate_for_startup(self) -> None:
        if self.environment == "production" and not self.api_key:
            raise RuntimeError(
                "EDTA_API_KEY is required when EDTA_ENVIRONMENT=production. "
                "Set a strong secret before deploying."
            )
        if self.environment == "production" and "*" in self.cors_origins:
            raise RuntimeError(
                "EDTA_CORS_ORIGINS must not include '*' in production when credentials are used."
            )
        missing_models = [path for path in self.required_models if not Path(path).exists()]
        if missing_models:
            raise RuntimeError(
                "Missing trained model artifacts: "
                + ", ".join(missing_models)
                + ". Run python scripts/train_all_models.py"
            )
        if not self.tapl_policy_file.exists():
            raise RuntimeError(f"TAPL policy file not found: {self.tapl_policy_file}")


settings = Settings()
