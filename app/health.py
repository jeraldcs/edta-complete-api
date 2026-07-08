from pathlib import Path

from app.config import settings
from app.db import Database


def _path_status(path: Path) -> dict:
    return {
        "path": str(path),
        "exists": path.exists(),
    }


def _models_status() -> dict:
    missing = [name for name in settings.required_models if not Path(name).exists()]
    present = len(settings.required_models) - len(missing)
    return {
        "ready": len(missing) == 0,
        "present": present,
        "required": len(settings.required_models),
        "missing": missing,
    }


def _sqlite_writable() -> bool:
    try:
        Database(settings.edta_db_path).init_schema()
        with Database(settings.edta_db_path).transaction() as connection:
            connection.execute("SELECT 1")
        return True
    except OSError:
        return False


def build_health_payload(
    *,
    llm_enabled: bool,
    self_distillation: dict,
    feedback_writable: bool,
    eml_writable: bool,
    graph_writable: bool,
    haoe_status: dict,
) -> dict:
    models = _models_status()
    profile = _path_status(settings.profile_lookup_file)
    tapl_policy = _path_status(settings.tapl_policy_file)
    sqlite_ready = _sqlite_writable()

    checks = {
        "models": models,
        "sqlite": {
            "path": str(settings.edta_db_path),
            "writable": sqlite_ready,
        },
        "experience_memory": {
            "backend": "sqlite",
            "writable": eml_writable and sqlite_ready,
        },
        "tkge_store": {
            "backend": "sqlite",
            "writable": graph_writable and sqlite_ready,
        },
        "feedback_store": {
            "path": str(settings.feedback_store_file),
            "writable": feedback_writable,
        },
        "profile_lookup": profile,
        "tapl_policy": tapl_policy,
        "haoe": haoe_status,
    }

    ready = (
        models["ready"]
        and sqlite_ready
        and eml_writable
        and graph_writable
        and feedback_writable
        and profile["exists"]
        and tapl_policy["exists"]
    )

    return {
        "status": "ok" if ready else "degraded",
        "ready": ready,
        "checks": checks,
        "auth_enabled": settings.auth_enabled,
        "environment": settings.environment,
        "llm_enabled": llm_enabled,
        "self_distillation": self_distillation,
    }


def build_live_payload() -> dict:
    return {
        "status": "alive",
        "service": "edta-api",
        "environment": settings.environment,
    }

