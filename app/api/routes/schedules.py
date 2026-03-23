"""
Content Schedule routes (scoped under a project).
"""
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.core.logging import get_logger
from app.models.content import ContentSchedule
from app.schemas.content import ContentScheduleCreate, ContentScheduleOut
from app.services.project_service import ProjectNotFoundError, ProjectService

router = APIRouter(prefix="/projects/{project_id}/schedules", tags=["schedules"])
logger = get_logger(__name__)


@router.get("", response_model=list[ContentScheduleOut])
async def list_schedules(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> list[ContentScheduleOut]:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    stmt = (
        select(ContentSchedule)
        .where(ContentSchedule.project_id == project_id)
        .order_by(ContentSchedule.created_at.desc())
    )
    schedules = await db.scalars(stmt)
    return [ContentScheduleOut.model_validate(s) for s in schedules]


@router.post("", response_model=ContentScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    project_id: uuid.UUID,
    payload: ContentScheduleCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> ContentScheduleOut:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        from app.services.scheduler_service import SchedulerService
        next_run = SchedulerService.calculate_next_run(payload.cron_expression)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid CRON expression: {exc}")

    schedule = ContentSchedule(
        project_id=project_id,
        cron_expression=payload.cron_expression,
        config=payload.config,
        next_run_at=next_run
    )
    db.add(schedule)
    await db.flush()
    logger.info("schedule_created", schedule_id=str(schedule.id), project_id=str(project_id))
    
    from app.services.topic_service import TopicService
    await TopicService(db).project_future_dates(project_id)
    
    return ContentScheduleOut.model_validate(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    project_id: uuid.UUID,
    schedule_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    stmt = select(ContentSchedule).where(
        ContentSchedule.id == schedule_id,
        ContentSchedule.project_id == project_id
    )
    schedule = await db.scalar(stmt)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")

    await db.delete(schedule)
    await db.flush()
    
    from sqlalchemy import update
    from app.models.content import Topic
    stmt2 = update(Topic).where(Topic.project_id == project_id, Topic.status == "queued").values(scheduled_date=None)
    await db.execute(stmt2)
    await db.flush()
    
    logger.info("schedule_deleted_and_dates_cleared", schedule_id=str(schedule_id), project_id=str(project_id))
