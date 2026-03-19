"""
Article routes (scoped under a project).
"""
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.core.logging import get_logger
from app.models.content import Article, Topic
from app.schemas.content import ArticleOut
from app.services.project_service import ProjectNotFoundError, ProjectService

router = APIRouter(prefix="/projects/{project_id}/articles", tags=["articles"])
logger = get_logger(__name__)


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> list[ArticleOut]:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    offset = (page - 1) * page_size
    stmt = (
        select(Article)
        .join(Topic, Topic.id == Article.topic_id)
        .where(Topic.project_id == project_id)
        .order_by(Article.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    articles = await db.scalars(stmt)
    return [ArticleOut.model_validate(a) for a in articles]


@router.get("/{article_id}", response_model=ArticleOut)
async def get_article(
    project_id: uuid.UUID,
    article_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ArticleOut:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    stmt = (
        select(Article)
        .join(Topic, Topic.id == Article.topic_id)
        .where(Topic.project_id == project_id, Article.id == article_id)
    )
    article = await db.scalar(stmt)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")
    
    return ArticleOut.model_validate(article)


@router.patch("/{article_id}/publish", response_model=ArticleOut)
async def publish_article(
    project_id: uuid.UUID,
    article_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBSession,
) -> ArticleOut:
    try:
        await ProjectService(db).get_by_id(project_id, current_user.id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    stmt = (
        select(Article)
        .join(Topic, Topic.id == Article.topic_id)
        .where(Topic.project_id == project_id, Article.id == article_id)
        .with_for_update()
    )
    article = await db.scalar(stmt)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found.")
    
    from datetime import datetime, UTC
    article.status = "published"
    article.published_at = datetime.now(UTC)
    await db.flush()
    
    logger.info("article_published", article_id=str(article_id), project_id=str(project_id))
    return ArticleOut.model_validate(article)
