"""
Health check routes.

/health      – liveness probe (always returns 200 if app is running)
/health/ready – readiness probe (checks DB + Redis connectivity)
"""
from fastapi import APIRouter, status
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness() -> dict:
    """Kubernetes liveness probe – returns 200 if the process is alive."""
    return {"status": "ok", "version": settings.APP_VERSION}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness() -> dict:
    """
    Readiness probe – verifies the app can reach its dependencies.
    Returns 503 if any dependency is unavailable.
    """
    checks: dict[str, str] = {}

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error("readiness_db_failed", exc=str(exc))
        checks["database"] = "error"

    # Redis check
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.error("readiness_redis_failed", exc=str(exc))
        checks["redis"] = "error"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = status.HTTP_200_OK if overall == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )
