from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import CompareOutcomesResponseV1, RecommendationResponseV1
import app.container as app_container
from app.idempotency import read_idempotency_key
from app.middleware.http import get_request_id
from app.models import (
    BatchRecommendationRequest,
    CompareOutcomesRequest,
    FeedbackEvent,
    JobAcceptedResponse,
    RecommendationRequest,
    ScenarioRecommendationRequest,
    SimulationRequest,
    SyntheticTrainingRequest,
    WebhookRegistrationRequest,
    EmpathySimulationRequest,
)
from app.security import require_api_key
from app.services import recommendation_handlers


router = APIRouter(prefix="/v1", tags=["v1"])


@router.post("/recommend", response_model=RecommendationResponseV1, dependencies=[Depends(require_api_key)])
async def recommend_v1(request: RecommendationRequest, http_request: Request):
    idempotency_key = read_idempotency_key(http_request)
    if idempotency_key:
        cached = app_container.container.idempotency_store.get(idempotency_key)
        if cached:
            return cached

    response = recommendation_handlers.handlers.recommend(request, request_id=get_request_id(http_request))
    await app_container.container.event_bus.publish(
        "recommendation.created",
        {
            "request_id": response.request_summary.request_id,
            "customer_id": response.request_summary.customer_id,
            "recommendation_count": len(response.recommendations),
        },
    )
    payload = response.model_dump(mode="json")
    if idempotency_key:
        app_container.container.idempotency_store.save(idempotency_key, payload)
    return response


@router.post("/recommend/batch", response_model=JobAcceptedResponse, status_code=202, dependencies=[Depends(require_api_key)])
def recommend_batch_v1(
    request: BatchRecommendationRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
):
    job_id = app_container.container.job_store.create("recommend_batch", {"count": len(request.requests)})
    background_tasks.add_task(recommendation_handlers.handlers.process_batch, job_id, request)
    return JobAcceptedResponse(job_id=job_id, status_url=f"/v1/jobs/{job_id}")


@router.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_job_v1(job_id: str):
    job = app_container.container.job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job


@router.post("/recommend-from-scenario", response_model=RecommendationResponseV1, dependencies=[Depends(require_api_key)])
def recommend_from_scenario_v1(request: ScenarioRecommendationRequest, http_request: Request):
    return recommendation_handlers.handlers.recommend_from_scenario(request, request_id=get_request_id(http_request))


@router.post("/empathy/simulate", dependencies=[Depends(require_api_key)])
def empathy_simulate_v1(request: EmpathySimulationRequest, http_request: Request):
    return recommendation_handlers.handlers.empathy_simulate(request, request_id=get_request_id(http_request))


@router.post("/simulate", response_model=RecommendationResponseV1, dependencies=[Depends(require_api_key)])
def simulate_v1(request: SimulationRequest, http_request: Request):
    return recommendation_handlers.handlers.simulate(request, request_id=get_request_id(http_request))


@router.post("/compare-outcomes", response_model=CompareOutcomesResponseV1, dependencies=[Depends(require_api_key)])
def compare_outcomes_v1(request: CompareOutcomesRequest, http_request: Request):
    try:
        return recommendation_handlers.handlers.compare_outcomes(request, request_id=get_request_id(http_request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/context-graph", dependencies=[Depends(require_api_key)])
def context_graph_v1(
    customer_id: Optional[str] = None,
    anonymous_id: Optional[str] = None,
    include_live: bool = True,
):
    return recommendation_handlers.handlers.get_context_graph(customer_id, anonymous_id, include_live)


@router.get("/orchestration-status", dependencies=[Depends(require_api_key)])
def orchestration_status_v1():
    return app_container.container.engine.orchestrator.status()


@router.post("/feedback", dependencies=[Depends(require_api_key)])
async def feedback_v1(event: FeedbackEvent, http_request: Request):
    idempotency_key = read_idempotency_key(http_request)
    if idempotency_key:
        cached = app_container.container.idempotency_store.get(idempotency_key)
        if cached:
            return cached

    payload = recommendation_handlers.handlers.feedback(event)
    await app_container.container.event_bus.publish(
        "feedback.received",
        {
            "request_id": get_request_id(http_request),
            "recommendation_id": event.recommendation_id,
            "event_type": event.event_type.value,
            "converted": event.converted,
        },
    )
    if idempotency_key:
        app_container.container.idempotency_store.save(idempotency_key, payload)
    return payload


@router.get("/experience-memory", dependencies=[Depends(require_api_key)])
def experience_memory_v1(customer_id: Optional[str] = None, anonymous_id: Optional[str] = None):
    from app.models import CustomerContext

    context = CustomerContext(customer_id=customer_id, anonymous_id=anonymous_id)
    return app_container.container.experience_memory.get_snapshot(context).model_dump(mode="json")


@router.get("/self-distillation", dependencies=[Depends(require_api_key)])
def self_distillation_v1():
    return app_container.container.engine.distillation.status()


@router.get("/scenario-examples", dependencies=[Depends(require_api_key)])
def scenario_examples_v1():
    return recommendation_handlers.handlers.scenario_examples()


@router.post("/synthetic-training-data", dependencies=[Depends(require_api_key)])
def synthetic_training_data_v1(request: SyntheticTrainingRequest):
    records = app_container.container.llm_client.generate_synthetic_training_data(request.domain, request.count)
    if records is None:
        return {
            "status": "llm_unavailable",
            "message": "Set OPENAI_API_KEY to generate synthetic data.",
            "records": [],
        }
    return {"status": "generated", "records": records}


@router.post("/webhooks", dependencies=[Depends(require_api_key)])
def register_webhook_v1(request: WebhookRegistrationRequest):
    try:
        return app_container.container.event_bus.register_webhook(
            request.target_url,
            [event_type.value for event_type in request.event_types],
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/webhooks", dependencies=[Depends(require_api_key)])
def list_webhooks_v1():
    return {"webhooks": app_container.container.event_bus.list_webhooks()}


@router.delete("/webhooks/{webhook_id}", dependencies=[Depends(require_api_key)])
def delete_webhook_v1(webhook_id: str):
    if not app_container.container.event_bus.deactivate_webhook(webhook_id):
        raise HTTPException(status_code=404, detail=f"Webhook not found: {webhook_id}")
    return {"status": "deactivated", "id": webhook_id}


@router.get("/events/stream", dependencies=[Depends(require_api_key)])
async def events_stream_v1():
    return StreamingResponse(
        app_container.container.event_bus.stream_events(),
        media_type="text/event-stream",
    )
