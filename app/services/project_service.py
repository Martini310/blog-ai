"""
Project service.

All project CRUD operations live here.
Routes only call this service – no DB access in routes.
"""
import uuid

import sentry_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, set_project_id
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.subscription_limit_service import (
    SubscriptionLimitExceededError,
    SubscriptionLimitService,
)

logger = get_logger(__name__)


class ProjectNotFoundError(Exception):
    pass


class ProjectLimitExceededError(Exception):
    pass


class ProjectService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
        project = await self._db.scalar(
            select(Project).where(
                Project.id == project_id,
                Project.owner_id == owner_id,
            )
        )
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found.")
        set_project_id(str(project_id))
        return project

    async def list_for_user(
        self,
        owner_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Project], int]:
        offset = (page - 1) * page_size
        stmt = select(Project).where(Project.owner_id == owner_id)
        results = await self._db.scalars(stmt.offset(offset).limit(page_size))
        total = await self._db.scalar(
            select(Project).where(Project.owner_id == owner_id).with_only_columns(
                # count via subquery to avoid N+1
                __import__("sqlalchemy").func.count()
            )
        ) or 0
        return list(results), total

    async def create(self, owner_id: uuid.UUID, payload: ProjectCreate) -> Project:
        """
        Enforce plan-based project limit before creating.
        Actual LLM operations are triggered as Celery tasks – not here.
        """
        try:
            try:
                await SubscriptionLimitService(self._db).ensure_project_creation_allowed(owner_id)
            except SubscriptionLimitExceededError as exc:
                raise ProjectLimitExceededError(str(exc)) from exc

            project = Project(
                owner_id=owner_id,
                **payload.model_dump(),
            )
            self._db.add(project)
            await self._db.flush()

            logger.info(
                "project_created",
                project_id=str(project.id),
                owner_id=str(owner_id),
            )
            
            from app.core.logging import get_request_id
            from app.tasks.content_tasks import analyse_project
            
            analyse_project.delay(
                project_id=str(project.id),
                user_id=str(owner_id),
                request_id=get_request_id(),
            )
            
            return project

        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            raise

    async def update(
        self,
        project_id: uuid.UUID,
        owner_id: uuid.UUID,
        payload: ProjectUpdate,
    ) -> Project:
        project = await self.get_by_id(project_id, owner_id)
        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)
        await self._db.flush()
        logger.info("project_updated", project_id=str(project_id))
        return project

    async def delete(self, project_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        project = await self.get_by_id(project_id, owner_id)
        await self._db.delete(project)
        logger.info("project_deleted", project_id=str(project_id))
