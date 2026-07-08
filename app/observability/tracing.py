from app.config import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)
_configured = False


def configure_tracing(app) -> None:
    global _configured
    if _configured or not settings.otel_enabled:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "OpenTelemetry enabled but packages are not installed; tracing disabled",
            extra={"event": "otel_unavailable"},
        )
        return

    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "deployment.environment": settings.environment,
    })
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            logger.warning(
                "OTLP exporter package missing; using no-op tracer provider",
                extra={"event": "otel_exporter_unavailable"},
            )

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/metrics,/live,/ready,/health")
    _configured = True
    logger.info("OpenTelemetry tracing configured", extra={"event": "otel_configured"})


def shutdown_tracing() -> None:
    global _configured
    if not _configured:
        return
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            shutdown()
    except Exception:  # pragma: no cover - best effort shutdown
        pass
    _configured = False
