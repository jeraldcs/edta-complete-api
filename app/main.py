from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.config import settings
import app.container as app_container
from app.health import build_health_payload, build_live_payload
from app.middleware.http import (
    AccessLogMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    get_request_id,
    register_exception_handlers,
)
from app.models import (
    CompareOutcomesRequest,
    CompareOutcomesResponse,
    FeedbackEvent,
    RecommendationRequest,
    RecommendationResponse,
    ScenarioRecommendationRequest,
    SimulationRequest,
    SyntheticTrainingRequest,
    EmpathySimulationRequest,
)
from app.observability.logging import configure_logging, get_logger
from app.observability.metrics import metrics_enabled, render_metrics
from app.observability.tracing import configure_tracing, shutdown_tracing
from app.services import recommendation_handlers
from app.security import require_api_key

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    configure_tracing(app)
    logger.info(
        "EDTA API starting",
        extra={
            "event": "startup",
            "environment": settings.environment,
            "metrics_enabled": metrics_enabled(),
            "auth_enabled": settings.auth_enabled,
        },
    )
    yield
    logger.info("EDTA API shutting down", extra={"event": "shutdown"})
    shutdown_tracing()


app = FastAPI(
    title="EDTA Full AI Models",
    description="Detailed AI models for EDTA: intent, journey, TAPL, channel, outcome simulation, and ranking.",
    version="2.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(v1_router)


def _health_response():
    payload = build_health_payload(
        llm_enabled=app_container.container.llm_client.enabled,
        self_distillation=app_container.container.engine.distillation.status(),
        feedback_writable=app_container.container.feedback_store.is_writable(),
        eml_writable=app_container.container.experience_memory.is_writable(),
        graph_writable=app_container.container.graph_store.is_writable(),
        haoe_status=app_container.container.engine.orchestrator.status(),
    )
    payload.update({
        "service": "EDTA Full AI Models",
        "api_version": "v1",
        "profile_lookup": app_container.container.profile_service.adapter.adapter_name,
        "experience_memory": "sqlite",
        "tkge": "enabled",
        "hybrid_ai_orchestration": "rules_slm_ml_llm",
        "supported_channels": [c.value for c in __import__("app.models", fromlist=["Channel"]).Channel],
        "demo": "/scenario-demo",
        "scenario_demo": "/scenario-demo",
        "swagger": "/docs",
        "openapi": "/openapi.json",
        "v1_base": "/v1",
        "live_probe": "/live",
        "ready_probe": "/ready",
        "metrics_path": "/metrics" if metrics_enabled() else None,
    })
    return payload


@app.get("/")
def health_check():
    return _health_response()


@app.get("/health")
def health():
    return _health_response()


@app.get("/live")
def live():
    return build_live_payload()


@app.get("/ready")
def ready():
    payload = _health_response()
    status_code = 200 if payload["ready"] else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(content=payload, status_code=status_code)


@app.get("/metrics")
def metrics():
    if not metrics_enabled():
        raise HTTPException(status_code=404, detail="Metrics are disabled.")
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)


@app.get("/demo-config")
def demo_config():
    from app.config import settings as runtime_settings

    if not runtime_settings.auth_enabled:
        return {"auth_enabled": False, "api_key": None}
    if runtime_settings.expose_demo_api_key:
        return {"auth_enabled": True, "api_key": runtime_settings.api_key}
    return {"auth_enabled": True, "api_key": None}


@app.get("/demo")
def demo_redirect():
    return RedirectResponse(url="/scenario-demo", status_code=307)


@app.get("/scenario-demo")
def scenario_demo():
    return FileResponse(Path("static/scenario.html"))


@app.get("/empathy-demo")
def empathy_demo():
    return RedirectResponse(url="/scenario-demo?mode=empathy", status_code=307)


@app.get("/scenario-examples")
def scenario_examples():
    return recommendation_handlers.handlers.scenario_examples()


@app.post("/recommend", response_model=RecommendationResponse, dependencies=[Depends(require_api_key)])
async def recommend_legacy(request: RecommendationRequest, http_request: Request):
    response = recommendation_handlers.handlers.recommend(request, request_id=get_request_id(http_request))
    await app_container.container.event_bus.publish(
        "recommendation.created",
        {"request_id": response.request_summary.request_id, "legacy_route": True},
    )
    return response.model_dump(mode="json")


@app.post("/recommend-from-scenario", response_model=RecommendationResponse, dependencies=[Depends(require_api_key)])
def recommend_from_scenario_legacy(request: ScenarioRecommendationRequest, http_request: Request):
    return recommendation_handlers.handlers.recommend_from_scenario(request, request_id=get_request_id(http_request)).model_dump(mode="json")


@app.post("/empathy/simulate", dependencies=[Depends(require_api_key)])
def empathy_simulate_legacy(request: EmpathySimulationRequest, http_request: Request):
    return recommendation_handlers.handlers.empathy_simulate(request, request_id=get_request_id(http_request))


@app.post("/simulate", response_model=RecommendationResponse, dependencies=[Depends(require_api_key)])
def simulate_legacy(request: SimulationRequest, http_request: Request):
    return recommendation_handlers.handlers.simulate(request, request_id=get_request_id(http_request)).model_dump(mode="json")


@app.post("/compare-outcomes", response_model=CompareOutcomesResponse, dependencies=[Depends(require_api_key)])
def compare_outcomes_legacy(request: CompareOutcomesRequest, http_request: Request):
    try:
        response = recommendation_handlers.handlers.compare_outcomes(request, request_id=get_request_id(http_request))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return response.model_dump(mode="json")


@app.get("/context-graph")
def get_context_graph_legacy(
    customer_id: str | None = None,
    anonymous_id: str | None = None,
    include_live: bool = True,
):
    return recommendation_handlers.handlers.get_context_graph(customer_id, anonymous_id, include_live)


@app.get("/orchestration-status")
def orchestration_status_legacy():
    return app_container.container.engine.orchestrator.status()


@app.post("/feedback", dependencies=[Depends(require_api_key)])
async def feedback_legacy(event: FeedbackEvent, http_request: Request):
    payload = recommendation_handlers.handlers.feedback(event)
    await app_container.container.event_bus.publish(
        "feedback.received",
        {"request_id": get_request_id(http_request), "legacy_route": True},
    )
    return payload


@app.get("/experience-memory")
def get_experience_memory_legacy(customer_id: str | None = None, anonymous_id: str | None = None):
    from app.models import CustomerContext

    context = CustomerContext(customer_id=customer_id, anonymous_id=anonymous_id)
    return app_container.container.experience_memory.get_snapshot(context).model_dump(mode="json")


@app.get("/self-distillation")
def self_distillation_status_legacy():
    return app_container.container.engine.distillation.status()


@app.post("/synthetic-training-data", dependencies=[Depends(require_api_key)])
def synthetic_training_data_legacy(request: SyntheticTrainingRequest):
    records = app_container.container.llm_client.generate_synthetic_training_data(request.domain, request.count)
    if records is None:
        return {
            "status": "llm_unavailable",
            "message": "Set OPENAI_API_KEY to generate synthetic data.",
            "records": [],
        }
    return {"status": "generated", "records": records}
