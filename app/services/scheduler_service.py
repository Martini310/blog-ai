"""
Scheduler service.

Owns scheduler business logic:
- finding due schedules,
- selecting the highest-priority eligible topic,
- reserving the topic atomically for processing.
"""
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import ContentSchedule, Topic
from app.models.project import Project

ELIGIBLE_TOPIC_STATUSES = ("queued", "scheduled", "pending")
TOPIC_GENERATION_MARKER_KEY = "topic_generation_requested_at"
TOPIC_GENERATION_COOLDOWN = timedelta(hours=6)


class SchedulerService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_due_schedules(self, now: datetime) -> list[ContentSchedule]:
        stmt = (
            select(ContentSchedule)
            .join(Project, Project.id == ContentSchedule.project_id)
            .where(
                ContentSchedule.is_active.is_(True),
                ContentSchedule.next_run_at.is_not(None),
                ContentSchedule.next_run_at <= now,
                Project.status == "active",
            )
            .order_by(ContentSchedule.next_run_at.asc())
        )
        rows = await self._db.scalars(stmt)
        return list(rows)

    async def reserve_next_eligible_topic(
        self,
        project_id: uuid.UUID,
        run_date: date,
    ) -> Topic | None:
        stmt = (
            select(Topic)
            .where(
                Topic.project_id == project_id,
                Topic.status.in_(ELIGIBLE_TOPIC_STATUSES),
                or_(Topic.scheduled_date.is_(None), Topic.scheduled_date <= run_date),
            )
            .order_by(Topic.priority.desc(), Topic.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        topic = await self._db.scalar(stmt)
        if not topic:
            return None

        topic.status = "in_progress"
        await self._db.flush()
        return topic

    async def has_topic_backlog(self, project_id: uuid.UUID) -> bool:
        stmt = (
            select(Topic.id)
            .where(
                Topic.project_id == project_id,
                Topic.status.in_(ELIGIBLE_TOPIC_STATUSES),
            )
            .limit(1)
        )
        return (await self._db.scalar(stmt)) is not None

    async def get_project_owner_id(self, project_id: uuid.UUID) -> uuid.UUID | None:
        stmt = select(Project.owner_id).where(Project.id == project_id)
        return await self._db.scalar(stmt)

    @staticmethod
    def mark_schedule_run(schedule: ContentSchedule, now: datetime) -> None:
        schedule.last_run_at = now

    @staticmethod
    def should_request_topic_generation(schedule: ContentSchedule, now: datetime) -> bool:
        raw_value = (schedule.config or {}).get(TOPIC_GENERATION_MARKER_KEY)
        if not raw_value:
            return True

        try:
            requested_at = datetime.fromisoformat(raw_value)
        except ValueError:
            return True

        if requested_at.tzinfo is None:
            requested_at = requested_at.replace(tzinfo=UTC)

        return now - requested_at >= TOPIC_GENERATION_COOLDOWN

    @staticmethod
    def mark_topic_generation_requested(schedule: ContentSchedule, now: datetime) -> None:
        config = dict(schedule.config or {})
        config[TOPIC_GENERATION_MARKER_KEY] = now.isoformat()
        schedule.config = config

    @staticmethod
    def clear_topic_generation_marker(schedule: ContentSchedule) -> None:
        config = dict(schedule.config or {})
        if TOPIC_GENERATION_MARKER_KEY in config:
            config.pop(TOPIC_GENERATION_MARKER_KEY, None)
            schedule.config = config
