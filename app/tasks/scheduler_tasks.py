"""
Celery Beat periodic tasks.

These tasks are called on a schedule by Celery Beat.
They query the DB for work to do and dispatch content_tasks as needed.
"""
import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import get_db
from app.core.logging import get_logger, set_task_name
from app.models.content import ContentSchedule
from app.tasks.celery_app import celery_app
from app.tasks.content_tasks import generate_article

logger = get_logger(__name__)


@celery_app.task(
    name="app.tasks.scheduler_tasks.run_due_content_schedules",
    queue="scheduler",
    ignore_result=True,
)
def run_due_content_schedules() -> None:
    """
    Scans ContentSchedule rows where next_run_at <= now() and is_active=True,
    then dispatches generate_article tasks for due queued/scheduled topics.
    """
    set_task_name("run_due_content_schedules")
    asyncio.get_event_loop().run_until_complete(_run_due_schedules_async())


async def _run_due_schedules_async() -> None:
    now = datetime.now(UTC)
    async with get_db() as db:
        schedules = await db.scalars(
            select(ContentSchedule).where(
                ContentSchedule.is_active.is_(True),
                ContentSchedule.next_run_at <= now,
            )
        )

        dispatched = 0
        for schedule in schedules:
            # TODO: fetch due queued/scheduled topics and dispatch per topic
            # For now, log that we would dispatch
            logger.info(
                "schedule_due",
                schedule_id=str(schedule.id),
                project_id=str(schedule.project_id),
            )

            # Update last_run_at (next_run_at computation belongs in a service)
            schedule.last_run_at = now
            dispatched += 1

    logger.info("schedules_processed", count=dispatched)


@celery_app.task(
    name="app.tasks.scheduler_tasks.cleanup_stale_logs",
    queue="scheduler",
    ignore_result=True,
)
def cleanup_stale_logs() -> None:
    """
    Placeholder for periodic maintenance: archive or delete old generation logs.
    Implement retention policy based on business requirements.
    """
    set_task_name("cleanup_stale_logs")
    logger.info("cleanup_stale_logs_started")
    # TODO: implement log archival / deletion
