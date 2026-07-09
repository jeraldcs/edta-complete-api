from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PROVIDERS: dict[str, Any] = {
    "providers": {
        "llm": {
            "driver": "openai_compatible",
            "api_mode": "responses",
            "enabled_when_env_set": "OPENAI_API_KEY",
            "base_url_env": "OPENAI_BASE_URL",
            "api_key_env": "OPENAI_API_KEY",
            "model_env": "OPENAI_MODEL",
            "default_model": "gpt-4o-mini",
            "timeout_env": "LLM_REQUEST_TIMEOUT",
            "default_timeout_seconds": 30,
            "max_retries_env": "LLM_MAX_RETRIES",
            "default_max_retries": 2,
        },
        "slm": {
            "driver": "openai_compatible",
            "api_mode": "chat",
            "enabled_env": "SLM_ENABLED",
            "default_enabled": True,
            "base_url_env": "SLM_BASE_URL",
            "api_key_env": "SLM_API_KEY",
            "model_env": "SLM_MODEL",
            "default_model": "edta-local-slm",
            "default_api_key": "local-slm",
            "timeout_env": "SLM_REQUEST_TIMEOUT",
            "default_timeout_seconds": 15,
            "max_retries_env": "SLM_MAX_RETRIES",
            "default_max_retries": 1,
            "remote_requires_base_url": True,
        },
        "distilled": {
            "store_path_env": "DISTILLED_SLM_FILE",
            "default_store_path": "data/distilled_slm_memory.json",
            "min_overlap": 0.35,
        },
    }
}


@dataclass(frozen=True)
class ProviderSettings:
    name: str
    driver: str
    api_mode: str
    enabled: bool
    model: str
    api_key: str | None
    base_url: str | None
    timeout_seconds: float
    max_retries: int
    remote_available: bool


class InferenceProviderConfig:
    """Load provider settings from config/inference_providers.yaml and environment."""

    def __init__(self, config_path: str | None = None):
        configured = config_path or os.getenv("INFERENCE_PROVIDERS_FILE", "config/inference_providers.yaml")
        self.config_path = Path(configured)
        self.config = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return DEFAULT_PROVIDERS.copy()
        try:
            loaded = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return DEFAULT_PROVIDERS.copy()
        merged = DEFAULT_PROVIDERS.copy()
        providers = loaded.get("providers", {})
        merged_providers = dict(merged.get("providers", {}))
        for name, values in providers.items():
            if isinstance(values, dict) and isinstance(merged_providers.get(name), dict):
                merged_providers[name] = {**merged_providers[name], **values}
            else:
                merged_providers[name] = values
        merged["providers"] = merged_providers
        return merged

    def section(self, name: str) -> dict[str, Any]:
        section = self.config.get("providers", {}).get(name, {})
        return section if isinstance(section, dict) else {}

    @staticmethod
    def _env_bool(name: str, default: bool = False) -> bool:
        raw = os.getenv(name)
        if raw is None:
            return default
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _env_value(section: dict[str, Any], key: str, default: Any) -> Any:
        env_name = section.get(f"{key}_env")
        if env_name:
            value = os.getenv(str(env_name))
            if value is not None and value != "":
                return value
        default_key = f"default_{key}"
        if default_key in section:
            return section[default_key]
        return default

    def provider_settings(self, name: str) -> ProviderSettings:
        section = self.section(name)
        driver = str(section.get("driver", "openai_compatible"))
        api_mode = str(section.get("api_mode", "chat"))

        enabled = False
        if section.get("enabled_when_env_set"):
            enabled = bool(os.getenv(str(section["enabled_when_env_set"])))
        elif section.get("enabled_env"):
            enabled = self._env_bool(str(section["enabled_env"]), bool(section.get("default_enabled", False)))
        else:
            enabled = bool(section.get("default_enabled", False))

        base_url = self._env_value(section, "base_url", None)
        api_key = self._env_value(section, "api_key", section.get("default_api_key"))
        model = str(self._env_value(section, "model", "gpt-4o-mini"))
        timeout_seconds = float(self._env_value(section, "timeout_seconds", 30))
        max_retries = int(self._env_value(section, "max_retries", 2))

        remote_requires_base_url = bool(section.get("remote_requires_base_url", False))
        remote_available = bool(base_url) if remote_requires_base_url else enabled

        if name == "slm":
            enabled = self._env_bool(str(section.get("enabled_env", "SLM_ENABLED")), True)

        if name == "llm" and section.get("enabled_when_env_set"):
            enabled = bool(os.getenv(str(section["enabled_when_env_set"])))

        return ProviderSettings(
            name=name,
            driver=driver,
            api_mode=api_mode,
            enabled=enabled,
            model=model,
            api_key=str(api_key) if api_key is not None else None,
            base_url=str(base_url) if base_url else None,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            remote_available=remote_available and base_url is not None if remote_requires_base_url else enabled,
        )


_config: InferenceProviderConfig | None = None


def get_inference_provider_config() -> InferenceProviderConfig:
    global _config
    if _config is None:
        _config = InferenceProviderConfig()
    return _config
