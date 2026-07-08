import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from app.config import settings

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_configured = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "edta-api",
            "environment": settings.environment,
        }
        request_id = request_id_ctx.get()
        if request_id:
            payload["request_id"] = request_id
        for key in (
            "request_id",
            "event",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
            "route",
            "channel",
            "candidate_id",
            "tapl_action",
            "llm_enabled",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
