"""
Topic service.

Manages topic CRUD within a project.
LLM-driven topic generation is triggered via Celery tasks, not here.
"""
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, set_topic_id
from app.models.content import Topic
from app.schemas.content import TopicCreate

logger = get_logger(__name__)


class TopicNotFoundError(Exception):
    pass


class TopicService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_project(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Topic]:
        offset = (page - 1) * page_size
        result = await self._db.scalars(
            select(Topic)
            .where(Topic.project_id == project_id)
            .order_by(Topic.priority.desc(), Topic.created_at.asc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result)

    async def get_by_id(self, topic_id: uuid.UUID, project_id: uuid.UUID) -> Topic:
        topic = await self._db.scalar(
            select(Topic).where(
                Topic.id == topic_id,
                Topic.project_id == project_id,
            )
        )
        if not topic:
            raise TopicNotFoundError(f"Topic {topic_id} not found.")
        set_topic_id(str(topic_id))
        return topic

    async def create(self, project_id: uuid.UUID, payload: TopicCreate) -> Topic:
        topic = Topic(project_id=project_id, **payload.model_dump())
        self._db.add(topic)
        await self._db.flush()
        logger.info("topic_created", topic_id=str(topic.id), project_id=str(project_id))
        return topic

    async def update(self, topic_id: uuid.UUID, project_id: uuid.UUID, payload: dict) -> Topic:
        topic = await self.get_by_id(topic_id, project_id)
        for key, value in payload.items():
            if value is not None:
                setattr(topic, key, value)
        await self._db.flush()
        logger.info("topic_updated", topic_id=str(topic.id), project_id=str(project_id))
        return topic

    async def bulk_update(self, project_id: uuid.UUID, topic_ids: list[uuid.UUID], payload: dict) -> int:
        if not topic_ids or not payload:
            return 0
        stmt = (
            update(Topic)
            .where(Topic.project_id == project_id, Topic.id.in_(topic_ids))
            .values(**payload)
        )
        result = await self._db.execute(stmt)
        await self._db.flush()
        logger.info("topics_bulk_updated", count=result.rowcount, project_id=str(project_id))
        
        if payload.get("status") == "queued":
            await self.project_future_dates(project_id)
            
        return result.rowcount

    async def project_future_dates(self, project_id: uuid.UUID) -> None:
        """
        Calculates and assigns scheduled_date for all 'queued' topics in the project,
        following the project's active ContentSchedule cron.
        """
        from datetime import datetime, UTC
        from app.models.content import ContentSchedule
        
        schedule = await self._db.scalar(
            select(ContentSchedule)
            .where(
                ContentSchedule.project_id == project_id, 
                ContentSchedule.is_active == True
            )
        )
        if not schedule:
            return

        topics = await self._db.scalars(
            select(Topic)
            .where(Topic.project_id == project_id, Topic.status == "queued")
            .order_by(Topic.priority.desc(), Topic.created_at.asc())
        )
        
        now = datetime.now(UTC)
        try:
            import croniter
            cron = croniter.croniter(schedule.cron_expression, now)
            
            for topic in topics:
                next_run = cron.get_next(datetime)
                topic.scheduled_date = next_run.date()
                
            await self._db.flush()
            logger.info("project_future_dates_assigned", project_id=str(project_id))
        except Exception as e:
            logger.error(f"Failed to project future dates: {e}")

    async def delete(self, topic_id: uuid.UUID, project_id: uuid.UUID) -> None:
        topic = await self.get_by_id(topic_id, project_id)
        await self._db.delete(topic)
        await self._db.flush()
        logger.info("topic_deleted", topic_id=str(topic_id), project_id=str(project_id))
