import json
from pathlib import Path
from typing import Any

from app.profile.adapters.base import ProfileLookupAdapter


class JsonFileProfileAdapter:
    """Local JSON profile store for demos and offline development."""

    def __init__(self, profile_path: Path):
        self.profile_path = profile_path

    @property
    def adapter_name(self) -> str:
        return "json_file"

    @property
    def source_label(self) -> str:
        return str(self.profile_path)

    def _load_profiles(self) -> dict[str, dict[str, Any]]:
        if not self.profile_path.exists():
            return {}
        try:
            return json.loads(self.profile_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def lookup(self, customer_id: str) -> dict[str, Any] | None:
        return self._load_profiles().get(customer_id)
