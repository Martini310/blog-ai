"""
Celery Beat periodic tasks.

These tasks are called on a schedule by Celery Beat.
They query the DB for work to do and dispatch content_tasks as needed.
"""
import asyncio
from datetime import UTC, datetime

from app.core.database import get_db
from app.core.logging import get_logger, get_request_id, set_project_id, set_task_name
from app.services.scheduler_service import SchedulerService
from app.tasks.celery_app import celery_app
from app.tasks.content_tasks import generate_article, generate_topics

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
    run_date = now.date()

    async with get_db() as db:
        scheduler_service = SchedulerService(db)
        schedules = await scheduler_service.list_due_schedules(now)

        article_dispatched = 0
        topic_generation_dispatched = 0
        skipped = 0

        for schedule in schedules:
            set_project_id(str(schedule.project_id))
            logger.info(
                "schedule_due",
                schedule_id=str(schedule.id),
                project_id=str(schedule.project_id),
            )

            owner_id = await scheduler_service.get_project_owner_id(schedule.project_id)
            if not owner_id:
                logger.warning(
                    "schedule_owner_not_found",
                    schedule_id=str(schedule.id),
                    project_id=str(schedule.project_id),
                )
                scheduler_service.mark_schedule_run(schedule, now)
                skipped += 1
                continue

            topic = await scheduler_service.reserve_next_eligible_topic(
                schedule.project_id,
                run_date,
            )
            if topic:
                scheduler_service.clear_topic_generation_marker(schedule)
                task = generate_article.delay(
                    topic_id=str(topic.id),
                    project_id=str(schedule.project_id),
                    user_id=str(owner_id),
                    request_id=get_request_id() or None,
                )
                logger.info(
                    "article_generation_task_dispatched",
                    task_id=task.id,
                    schedule_id=str(schedule.id),
                    topic_id=str(topic.id),
                    project_id=str(schedule.project_id),
                )
                article_dispatched += 1
            else:
                has_backlog = await scheduler_service.has_topic_backlog(schedule.project_id)
                if has_backlog:
                    logger.info(
                        "no_due_topics_available",
                        schedule_id=str(schedule.id),
                        project_id=str(schedule.project_id),
                    )
                    skipped += 1
                elif scheduler_service.should_request_topic_generation(schedule, now):
                    task = generate_topics.delay(
                        project_id=str(schedule.project_id),
                        user_id=str(owner_id),
                        request_id=get_request_id() or None,
                    )
                    scheduler_service.mark_topic_generation_requested(schedule, now)
                    logger.info(
                        "topic_generation_task_dispatched",
                        task_id=task.id,
                        schedule_id=str(schedule.id),
                        project_id=str(schedule.project_id),
                    )
                    topic_generation_dispatched += 1
                else:
                    logger.info(
                        "topic_generation_cooldown_active",
                        schedule_id=str(schedule.id),
                        project_id=str(schedule.project_id),
                    )
                    skipped += 1

            scheduler_service.mark_schedule_run(schedule, now)

    logger.info(
        "schedules_processed",
        schedules_count=len(schedules),
        article_dispatched=article_dispatched,
        topic_generation_dispatched=topic_generation_dispatched,
        skipped=skipped,
    )


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
