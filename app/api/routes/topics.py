"""
Topic routes (scoped under a project).
"""
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DBSession
from app.core.logging import get_logger, get_request_id
from app.schemas.content import TopicCreate, TopicOut
from app.services.project_service import ProjectNotFoundError, ProjectService
from app.services.topic_service import TopicNotFoundError, TopicService
from app.tasks.content_tasks import generate_article

router = APIRouter(prefix="/projects/{project_id}/topics", tags=["topics"])
logger = get_logger(__name__)


@router.get("", response_model=list[TopicOut])
async def list_topics(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> list[TopicOut]:
    # Verify project ownership
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    topics = await TopicService(db).list_for_project(project_id, page=page, page_size=page_size)
    return [TopicOut.model_validate(t) for t in topics]


@router.get("/{topic_id}", response_model=TopicOut)
async def get_topic(
    project_id: uuid.UUID,
    topic_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> TopicOut:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
        topic = await TopicService(db).get_by_id(topic_id, project_id)
    except (ProjectNotFoundError, TopicNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return TopicOut.model_validate(topic)


@router.post("", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
async def create_topic(
    project_id: uuid.UUID,
    payload: TopicCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> TopicOut:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    topic = await TopicService(db).create(project_id, payload)
    return TopicOut.model_validate(topic)


@router.post("/{topic_id}/generate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_article_generation(
    project_id: uuid.UUID,
    topic_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Dispatch article generation for a specific topic.
    Returns immediately with a task ID; generation runs asynchronously.
    """
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
        await TopicService(db).get_by_id(topic_id, project_id)
    except (ProjectNotFoundError, TopicNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    task = generate_article.delay(
        topic_id=str(topic_id),
        project_id=str(project_id),
        user_id=str(current_user.id),
        request_id=get_request_id(),
    )
    logger.info(
        "generation_task_dispatched",
        task_id=task.id,
        topic_id=str(topic_id),
        project_id=str(project_id),
    )
    return {"task_id": task.id, "status": "queued"}
