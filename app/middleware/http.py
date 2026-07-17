import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings
from app.observability.logging import get_logger, request_id_ctx
from app.observability.metrics import RequestTimer, normalize_route, record_http_request

REQUEST_ID_HEADER = "X-Request-ID"
logger = get_logger(__name__)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def problem_response(
    *,
    request: Request,
    status: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
) -> JSONResponse:
    request_id = get_request_id(request)
    return JSONResponse(
        status_code=status,
        content={
            "type": type_,
            "title": title,
            "status": status,
            "detail": detail,
            "instance": str(request.url.path),
            "request_id": request_id,
        },
        media_type="application/problem+json",
        headers={REQUEST_ID_HEADER: request_id},
    )


class ProblemDetail(Exception):
    def __init__(self, status: int, title: str, detail: str, type_: str = "about:blank"):
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type_


def register_exception_handlers(app) -> None:
    from fastapi import HTTPException

    @app.exception_handler(ProblemDetail)
    async def problem_detail_handler(request: Request, exc: ProblemDetail):
        return problem_response(
            request=request,
            status=exc.status,
            title=exc.title,
            detail=exc.detail,
            type_=exc.type,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        title = "Request Error" if exc.status_code < 500 else "Server Error"
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return problem_response(
            request=request,
            status=exc.status_code,
            title=title,
            detail=detail,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception",
            extra={
                "event": "unhandled_exception",
                "path": request.url.path,
                "method": request.method,
            },
        )
        detail = str(exc) if settings.expose_error_details else "An unexpected error occurred."
        return problem_response(
            request=request,
            status=500,
            title="Internal Server Error",
            detail=detail,
        )


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id
        token = request_id_ctx.set(request_id)
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            request_id_ctx.reset(token)


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        timer = RequestTimer()
        client_ip = request.client.host if request.client else "unknown"
        try:
            response = await call_next(request)
        except Exception:
            duration = timer.elapsed_seconds
            record_http_request(
                method=request.method,
                path=request.url.path,
                status=500,
                duration_seconds=duration,
            )
            logger.exception(
                "Request failed",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "route": normalize_route(request.url.path),
                    "status_code": 500,
                    "duration_ms": round(timer.elapsed_ms, 2),
                    "client_ip": client_ip,
                },
            )
            raise

        duration = timer.elapsed_seconds
        record_http_request(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_seconds=duration,
        )
        logger.info(
            "HTTP request completed",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "route": normalize_route(request.url.path),
                "status_code": response.status_code,
                "duration_ms": round(timer.elapsed_ms, 2),
                "client_ip": client_ip,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Request-ID", get_request_id(request))
        if settings.environment == "production":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int):
        super().__init__(app)
        self.limit_per_minute = limit_per_minute
        self.hits: dict[str, list[float]] = {}
        self._max_tracked_clients = 10_000

    async def dispatch(self, request: Request, call_next):
        if self.limit_per_minute <= 0:
            return await call_next(request)

        import time

        now = time.time()
        client_host = request.client.host if request.client else "unknown"
        window_start = now - 60
        recent = [stamp for stamp in self.hits.get(client_host, []) if stamp >= window_start]
        if len(recent) >= self.limit_per_minute:
            return problem_response(
                request=request,
                status=429,
                title="Too Many Requests",
                detail=f"Rate limit exceeded ({self.limit_per_minute} requests/minute).",
            )

        recent.append(now)
        self.hits[client_host] = recent
        if len(self.hits) > self._max_tracked_clients:
            self._prune_clients(window_start)
        return await call_next(request)

    def _prune_clients(self, window_start: float) -> None:
        stale = [
            host
            for host, stamps in self.hits.items()
            if not any(stamp >= window_start for stamp in stamps)
        ]
        for host in stale:
            self.hits.pop(host, None)


_LEGACY_EXEMPT_PREFIXES = (
    "/v1",
    "/static",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
    "/live",
    "/ready",
    "/demo-api",
    "/scenario-demo",
    "/demo",
    "/empathy-demo",
    "/demo-config",
)


class LegacyDeprecationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if path in {"/", "/health"}:
            return response
        if any(path.startswith(prefix) for prefix in _LEGACY_EXEMPT_PREFIXES):
            return response
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} or path.startswith("/"):
            response.headers.setdefault("Deprecation", "true")
            response.headers.setdefault("Sunset", "Sat, 01 Jan 2028 00:00:00 GMT")
            response.headers.setdefault("Link", '</v1>; rel="successor-version"')
        return response
