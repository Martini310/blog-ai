"""
FastAPI application entry point.

Startup sequence:
  1. configure_logging()          – structlog + stdlib bridge
  2. Sentry SDK init              – before any route handlers
  3. Middleware stack (LIFO)      – error handler → logging → correlation ID
  4. Exception handlers           – domain errors → HTTP codes
  5. API router mount             – all routes under /api/v1

This file owns composition only. No business logic here.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    CorrelationIdMiddleware,
    ErrorHandlerMiddleware,
    RequestLoggingMiddleware,
)
from app.core.security import AuthError

# Configure logging as early as possible so all subsequent imports can log
configure_logging()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Sentry – initialise before the app so it captures startup errors too
# ---------------------------------------------------------------------------
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
        ],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
    )


# ---------------------------------------------------------------------------
# Lifespan – startup / shutdown hooks
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "application_starting",
        environment=settings.ENVIRONMENT,
        version=settings.APP_VERSION,
    )
    # Place DB warm-up, cache priming, etc. here
    yield
    logger.info("application_shutdown")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Custom middleware (added in reverse order – last added = outermost)
    # ------------------------------------------------------------------
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    # ------------------------------------------------------------------
    # Exception handlers – map domain errors to HTTP responses
    # ------------------------------------------------------------------
    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app


app = create_app()
