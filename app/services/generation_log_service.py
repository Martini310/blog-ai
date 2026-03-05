"""
GenerationLog service.

Provides a simple write-only interface for recording LLM operations.
Called from Celery tasks after each generation step.
"""
import time
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, get_request_id
from app.models.generation_log import GenerationLog
from app.schemas.generation_log import GenerationLogCreate

logger = get_logger(__name__)


class GenerationLogService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(self, entry: GenerationLogCreate) -> GenerationLog:
        """Persist one generation log entry."""
        log = GenerationLog(
            **entry.model_dump(),
            request_id=entry.request_id or get_request_id() or None,
        )
        self._db.add(log)
        await self._db.flush()

        logger.debug(
            "generation_logged",
            step=entry.step,
            status=entry.status,
            tokens_used=entry.tokens_used,
            duration_ms=entry.duration_ms,
        )
        return log


@asynccontextmanager
async def timed_generation_step(
    db: AsyncSession,
    *,
    step: str,
    task_name: str | None = None,
    extra: dict[str, Any] | None = None,
    **log_kwargs: Any,
):
    """
    Async context manager that automatically records a GenerationLog entry
    with timing information.

    Usage in a Celery task:
        async with timed_generation_step(db, step="outline", project_id=pid) as ctx:
            result = await llm_client.generate(...)
            ctx["tokens_used"] = result.usage.total_tokens
    """
    ctx: dict[str, Any] = {}
    start = time.perf_counter()
    try:
        yield ctx
        duration_ms = round((time.perf_counter() - start) * 1000)
        svc = GenerationLogService(db)
        await svc.record(
            GenerationLogCreate(
                step=step,
                task_name=task_name,
                status="success",
                duration_ms=duration_ms,
                tokens_used=ctx.get("tokens_used"),
                extra=extra or {},
                **log_kwargs,
            )
        )
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000)
        svc = GenerationLogService(db)
        await svc.record(
            GenerationLogCreate(
                step=step,
                task_name=task_name,
                status="failed",
                duration_ms=duration_ms,
                error_message=str(exc),
                extra=extra or {},
                **log_kwargs,
            )
        )
        raise
