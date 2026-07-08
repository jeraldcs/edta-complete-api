from typing import Any

from app.observability.logging import get_logger
from app.observability.metrics import record_recommendation

logger = get_logger("edta.audit")


def log_recommendation_audit(
    *,
    request_id: str,
    route: str,
    channel: str,
    candidate_id: str | None,
    tapl_action: str | None,
    intent: str | None,
    journey_stage: str | None,
    llm_enabled: bool,
    recommendation_count: int,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "event": "recommendation.audit",
        "route": route,
        "channel": channel,
        "candidate_id": candidate_id,
        "tapl_action": tapl_action,
        "intent": intent,
        "journey_stage": journey_stage,
        "llm_enabled": llm_enabled,
        "recommendation_count": recommendation_count,
    }
    if extra:
        payload.update(extra)

    logger.info(
        "Recommendation audit",
        extra={
            "request_id": request_id,
            **payload,
        },
    )
    if candidate_id and tapl_action:
        record_recommendation(channel=channel, tapl_action=tapl_action)
