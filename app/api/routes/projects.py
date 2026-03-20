"""
Project CRUD routes.

Routes own:
  - HTTP verb + path
  - Request/response serialisation
  - Calling services

Routes do NOT own:
  - Business logic
  - DB queries
  - LLM calls
"""
import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DBSession
from app.core.logging import get_logger
from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DBSession
from app.core.logging import get_logger
from app.schemas.common import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate, ProjectAnalysisOut
from app.models.project import ProjectAnalysis
from sqlalchemy import select
from app.services.project_service import (
    ProjectLimitExceededError,
    ProjectNotFoundError,
    ProjectService,
)
from app.tasks.content_tasks import analyse_project

router = APIRouter(prefix="/projects", tags=["projects"])
logger = get_logger(__name__)

@router.get("/{project_id}/analysis", response_model=ProjectAnalysisOut)
async def get_project_analysis(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectAnalysisOut:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    analysis = await db.scalar(
        select(ProjectAnalysis).where(ProjectAnalysis.project_id == project_id)
    )
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    
    return ProjectAnalysisOut.model_validate(analysis)


@router.get("", response_model=PaginatedResponse[ProjectOut])
async def list_projects(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[ProjectOut]:
    projects, total = await ProjectService(db).list_for_user(
        owner_id=current_user.id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[ProjectOut.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        pages=-(-total // page_size),  # ceiling division
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectOut:
    try:
        project = await ProjectService(db).create(
            owner_id=current_user.id,
            payload=payload,
        )
    except ProjectLimitExceededError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectOut:
    try:
        project = await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProjectOut.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> ProjectOut:
    try:
        project = await ProjectService(db).update(project_id, current_user.id, payload)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ProjectOut.model_validate(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> None:
    try:
        await ProjectService(db).delete(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{project_id}/analyse", status_code=status.HTTP_202_ACCEPTED)
async def trigger_analysis(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> dict:
    """
    Dispatch an AI analysis task for this project.
    Returns 202 Accepted – the task runs asynchronously.
    """
    # Verify project ownership before dispatching
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    from app.core.logging import get_request_id
    task = analyse_project.delay(
        project_id=str(project_id),
        user_id=str(current_user.id),
        request_id=get_request_id(),
    )
    logger.info("analysis_task_dispatched", task_id=task.id, project_id=str(project_id))
    return {"task_id": task.id, "status": "queued"}
