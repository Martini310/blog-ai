"""
Content generation Celery tasks.

Architecture rule:
  Tasks are thin orchestrators. All business logic lives in services.
  Tasks handle: retry policy, error capture, logging context, DB session lifecycle.

LLM calls belong in a dedicated LLM service (not yet implemented here –
stub shows the correct pattern without inventing dependencies).
"""
import asyncio
import uuid

import sentry_sdk
from celery import Task

from app.core.database import get_db
from app.core.logging import get_logger, set_project_id, set_task_name, set_topic_id
from app.services.generation_log_service import timed_generation_step
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Base task class – propagates request_id into logging context
# ---------------------------------------------------------------------------
class LoggedTask(Task):
    """Celery base task that injects task name into the logging context."""

    def __call__(self, *args, **kwargs):
        set_task_name(self.name)
        return super().__call__(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "task_failed",
            task_id=task_id,
            exc=str(exc),
        )
        sentry_sdk.capture_exception(exc)


# ---------------------------------------------------------------------------
# Article generation task
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    base=LoggedTask,
    name="app.tasks.content_tasks.generate_article",
    queue="generation",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,          # exponential backoff
    retry_backoff_max=600,       # cap at 10 minutes
    retry_jitter=True,
)
def generate_article(
    self: Task,
    topic_id: str,
    project_id: str,
    user_id: str,
    request_id: str | None = None,
) -> dict:
    """
    Orchestrates article generation for a single topic.

    This task is intentionally synchronous at the Celery layer but runs
    an asyncio event loop internally so services can use async SQLAlchemy.
    """
    set_project_id(project_id)
    set_topic_id(topic_id)

    logger.info(
        "generate_article_started",
        topic_id=topic_id,
        project_id=project_id,
    )

    return asyncio.get_event_loop().run_until_complete(
        _generate_article_async(
            topic_id=uuid.UUID(topic_id),
            project_id=uuid.UUID(project_id),
            user_id=uuid.UUID(user_id),
            request_id=request_id,
        )
    )


async def _generate_article_async(
    topic_id: uuid.UUID,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    request_id: str | None,
) -> dict:
    """
    Async implementation – uses get_db() context manager so it works
    outside of a FastAPI request context (no dependency injection).
    """
    async with get_db() as db:
        # Step 1: Generate outline
        async with timed_generation_step(
            db,
            step="outline",
            task_name="generate_article",
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
        ) as ctx:
            # TODO: call LLM service here
            # outline = await llm_service.generate_outline(topic)
            outline = {"sections": ["Introduction", "Main", "Conclusion"]}  # stub
            ctx["tokens_used"] = 150  # stub – replace with real usage

        # Step 2: Generate article body
        async with timed_generation_step(
            db,
            step="article_body",
            task_name="generate_article",
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
        ) as ctx:
            # TODO: call LLM service here
            article_content = {"body": "...", "word_count": 0}  # stub
            ctx["tokens_used"] = 2000  # stub

        logger.info(
            "generate_article_completed",
            topic_id=str(topic_id),
            project_id=str(project_id),
        )
        return {"topic_id": str(topic_id), "status": "completed", "outline": outline}


# ---------------------------------------------------------------------------
# Topic generation task
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    base=LoggedTask,
    name="app.tasks.content_tasks.generate_topics",
    queue="generation",
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def generate_topics(
    self: Task,
    project_id: str,
    user_id: str,
    request_id: str | None = None,
) -> dict:
    """
    Generates new topic ideas for a project when the queue is exhausted.
    """
    set_project_id(project_id)
    logger.info("generate_topics_started", project_id=project_id)

    return asyncio.get_event_loop().run_until_complete(
        _generate_topics_async(
            project_id=uuid.UUID(project_id),
            user_id=uuid.UUID(user_id),
            request_id=request_id,
        )
    )


async def _generate_topics_async(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    request_id: str | None,
) -> dict:
    async with get_db() as db:
        async with timed_generation_step(
            db,
            step="topic_generation",
            task_name="generate_topics",
            user_id=user_id,
            project_id=project_id,
            request_id=request_id,
        ) as ctx:
            # TODO: call LLM service + persist generated topics through TopicService.
            topics: list[dict] = []
            ctx["tokens_used"] = 300  # stub

    logger.info(
        "generate_topics_completed",
        project_id=str(project_id),
        topics_generated=len(topics),
    )
    return {
        "project_id": str(project_id),
        "status": "completed",
        "topics_generated": len(topics),
    }


# ---------------------------------------------------------------------------
# Project analysis task
# ---------------------------------------------------------------------------
@celery_app.task(
    bind=True,
    base=LoggedTask,
    name="app.tasks.content_tasks.analyse_project",
    queue="generation",
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def analyse_project(
    self: Task,
    project_id: str,
    user_id: str,
    request_id: str | None = None,
) -> dict:
    """Trigger AI analysis of a project's content strategy."""
    set_project_id(project_id)
    logger.info("analyse_project_started", project_id=project_id)

    return asyncio.get_event_loop().run_until_complete(
        _analyse_project_async(
            project_id=uuid.UUID(project_id),
            user_id=uuid.UUID(user_id),
            request_id=request_id,
        )
    )


async def _analyse_project_async(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    request_id: str | None,
) -> dict:
    async with get_db() as db:
        async with timed_generation_step(
            db,
            step="project_analysis",
            task_name="analyse_project",
            user_id=user_id,
            project_id=project_id,
            request_id=request_id,
        ) as ctx:
            # TODO: call LLM service / SEO analysis service
            result = {"keywords": [], "recommendations": []}  # stub
            ctx["tokens_used"] = 500

    return {"project_id": str(project_id), "status": "completed"}
