"""
ASGI middleware stack.

1. CorrelationIdMiddleware  – generates/propagates X-Request-ID header
2. RequestLoggingMiddleware – logs every request with duration_ms
3. ErrorHandlerMiddleware   – catches unhandled exceptions, returns JSON error

Middleware is added in main.py in reverse order (last added = outermost).
"""
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger, set_request_id

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 1. Correlation ID
# ---------------------------------------------------------------------------
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Reads X-Request-ID from incoming request headers or generates a new UUID.
    Injects it into the logging context and echoes it back in the response.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# ---------------------------------------------------------------------------
# 2. Request logging
# ---------------------------------------------------------------------------
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs HTTP method, path, status code, and wall-clock duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


# ---------------------------------------------------------------------------
# 3. Global error handler
# ---------------------------------------------------------------------------
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Catches any unhandled exception that escapes route handlers.
    Returns a structured JSON error so clients always receive JSON.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception("unhandled_exception", exc_info=exc)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
