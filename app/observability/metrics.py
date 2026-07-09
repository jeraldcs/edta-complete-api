import re
import time
from typing import Any

from app.config import settings

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when dependency missing
    _PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _NoopMetric:
        def __init__(self, *args, **kwargs):
            return None

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

    def generate_latest(*args, **kwargs):
        return b""

    Counter = Histogram = _NoopMetric  # type: ignore[misc,assignment]

HTTP_REQUESTS = Counter(
    "edta_http_requests_total",
    "Total HTTP requests processed",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "edta_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
RECOMMENDATIONS = Counter(
    "edta_recommendations_total",
    "Recommendations served",
    ["channel", "tapl_action"],
)
FEEDBACK_EVENTS = Counter(
    "edta_feedback_events_total",
    "Feedback events recorded",
    ["event_type", "converted"],
)

_ROUTE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^/v1/jobs/[^/]+$"), "/v1/jobs/{job_id}"),
    (re.compile(r"^/v1/.*"), "/v1/*"),
]


def metrics_enabled() -> bool:
    return settings.metrics_enabled and _PROMETHEUS_AVAILABLE


def normalize_route(path: str) -> str:
    for pattern, label in _ROUTE_PATTERNS:
        if pattern.match(path):
            return label
    if path in {"/", "/health", "/live", "/ready", "/metrics", "/docs", "/openapi.json"}:
        return path
    if path.startswith("/static/"):
        return "/static/*"
    return path.split("?")[0]


def record_http_request(*, method: str, path: str, status: int, duration_seconds: float) -> None:
    if not metrics_enabled():
        return
    route = normalize_route(path)
    HTTP_REQUESTS.labels(method=method, route=route, status=str(status)).inc()
    HTTP_LATENCY.labels(method=method, route=route).observe(duration_seconds)


def record_recommendation(*, channel: str, tapl_action: str) -> None:
    if not metrics_enabled():
        return
    RECOMMENDATIONS.labels(channel=channel, tapl_action=tapl_action).inc()


def record_feedback(*, event_type: str, converted: bool) -> None:
    if not metrics_enabled():
        return
    FEEDBACK_EVENTS.labels(event_type=event_type, converted=str(converted).lower()).inc()


def render_metrics() -> tuple[bytes, str]:
    if not metrics_enabled():
        return b"", CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST


class RequestTimer:
    def __init__(self):
        self.start = time.perf_counter()

    @property
    def elapsed_seconds(self) -> float:
        return time.perf_counter() - self.start

    @property
    def elapsed_ms(self) -> float:
        return self.elapsed_seconds * 1000
