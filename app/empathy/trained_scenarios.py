from pathlib import Path
from typing import Any

import yaml


def load_trained_scenarios(config_path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    path = Path(config_path or "config/empathy/trained_scenarios.yaml")
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    scenarios = payload.get("scenarios") or {}
    return {key: dict(value) for key, value in scenarios.items() if isinstance(value, dict)}


TRAINED_SCENARIOS = load_trained_scenarios()
