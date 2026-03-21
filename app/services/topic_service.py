"""
Topic service.

Manages topic CRUD within a project.
LLM-driven topic generation is triggered via Celery tasks, not here.
"""
import uuid

from sqlalchemy import select
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
