from fastapi import APIRouter, HTTPException, Request

from app import config as edta_config
from app.middleware.http import get_request_id
from app.models import (
    EmpathySimulationRequest,
    FeedbackEvent,
    RecommendationRequest,
    ScenarioRecommendationRequest,
    SimulationRequest,
)
from app.services import recommendation_handlers
import app.container as app_container


router = APIRouter(prefix="/demo-api", tags=["demo-proxy"])


def _ensure_demo_proxy_enabled() -> None:
    settings = edta_config.settings
    if not settings.auth_enabled:
        raise HTTPException(status_code=404, detail="Demo proxy is unavailable without API authentication.")
    if settings.expose_demo_api_key:
        raise HTTPException(
            status_code=404,
            detail="Demo proxy is disabled while EDTA_EXPOSE_DEMO_API_KEY is enabled.",
        )


@router.post("/recommend")
async def demo_recommend(request: RecommendationRequest, http_request: Request):
    _ensure_demo_proxy_enabled()
    response = recommendation_handlers.handlers.recommend(request, request_id=get_request_id(http_request))
    await app_container.container.event_bus.publish(
        "recommendation.created",
        {"request_id": response.request_summary.request_id, "demo_proxy": True},
    )
    return response.model_dump(mode="json")


@router.post("/recommend-from-scenario")
def demo_recommend_from_scenario(request: ScenarioRecommendationRequest, http_request: Request):
    _ensure_demo_proxy_enabled()
    return recommendation_handlers.handlers.recommend_from_scenario(
        request,
        request_id=get_request_id(http_request),
    ).model_dump(mode="json")


@router.post("/simulate")
def demo_simulate(request: SimulationRequest, http_request: Request):
    _ensure_demo_proxy_enabled()
    return recommendation_handlers.handlers.simulate(
        request,
        request_id=get_request_id(http_request),
    ).model_dump(mode="json")


@router.post("/feedback")
async def demo_feedback(event: FeedbackEvent, http_request: Request):
    _ensure_demo_proxy_enabled()
    payload = recommendation_handlers.handlers.feedback(event)
    await app_container.container.event_bus.publish(
        "feedback.received",
        {"request_id": get_request_id(http_request), "demo_proxy": True},
    )
    return payload


@router.post("/empathy/simulate")
def demo_empathy_simulate(request: EmpathySimulationRequest, http_request: Request):
    _ensure_demo_proxy_enabled()
    return recommendation_handlers.handlers.empathy_simulate(request, request_id=get_request_id(http_request))


@router.get("/travel-scenario-benchmark")
def demo_travel_scenario_benchmark():
    _ensure_demo_proxy_enabled()
    return recommendation_handlers.handlers.travel_scenario_benchmark()
