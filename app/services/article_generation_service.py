"""
Article generation service.

Owns the full article pipeline business logic. Celery tasks only orchestrate
execution and retries.
"""
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Article, Topic
from app.models.project import ProjectAnalysis
from app.services.generation_log_service import timed_generation_step


PIPELINE_MODEL_NAME = "mock-gpt-4o-mini"
PIPELINE_TASK_NAME = "generate_article"


class ArticleGenerationError(Exception):
    """Raised when article generation cannot proceed."""


@dataclass(slots=True)
class ArticlePipelineState:
    topic: Topic
    ai_context: str = ""
    outline: dict[str, Any] = field(default_factory=dict)
    sections: list[dict[str, Any]] = field(default_factory=list)
    merged_content: dict[str, Any] = field(default_factory=dict)
    seo_data: dict[str, Any] = field(default_factory=dict)
    internal_links: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    article: Article | None = None
    total_tokens: int = 0


class ArticleGenerationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def generate_for_topic(
        self,
        *,
        topic_id: uuid.UUID,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> dict[str, Any]:
        topic = await self._get_topic(topic_id=topic_id, project_id=project_id)
        state = ArticlePipelineState(topic=topic)

        try:
            await self._set_topic_in_progress(state)
            await self._load_ai_context(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._generate_outline(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._generate_sections(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._merge_content(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._optimize_seo(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._apply_internal_linking(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._generate_metadata(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._compute_metrics(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._save_article(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
            await self._set_topic_completed(
                state=state,
                project_id=project_id,
                topic_id=topic_id,
                user_id=user_id,
                request_id=request_id,
            )
        except Exception:
            await self._mark_topic_failed(state.topic)
            raise

        article = state.article
        if not article:
            raise ArticleGenerationError("Article was not created by the pipeline.")

        return {
            "topic_id": str(topic_id),
            "project_id": str(project_id),
            "article_id": str(article.id),
            "status": "completed",
            "word_count": article.word_count,
            "link_count": state.metrics.get("link_count"),
            "total_tokens": article.total_tokens,
        }

    async def _get_topic(self, *, topic_id: uuid.UUID, project_id: uuid.UUID) -> Topic:
        topic = await self._db.scalar(
            select(Topic)
            .where(
                Topic.id == topic_id,
                Topic.project_id == project_id,
            )
            .with_for_update()
        )
        if not topic:
            raise ArticleGenerationError(f"Topic {topic_id} not found for project {project_id}.")
        return topic

    async def _set_topic_in_progress(self, state: ArticlePipelineState) -> None:
        state.topic.status = "in_progress"
        await self._db.flush()

    async def _load_ai_context(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="load_ai_context",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
        ):
            analysis = await self._db.scalar(
                select(ProjectAnalysis).where(ProjectAnalysis.project_id == project_id)
            )
            state.ai_context = analysis.ai_context if analysis else ""

    async def _generate_outline(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="generate_outline",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
            model_used=PIPELINE_MODEL_NAME,
        ) as ctx:
            state.outline = {
                "title": state.topic.title,
                "sections": [
                    "Introduction",
                    "Main Insights",
                    "Actionable Checklist",
                    "Conclusion",
                ],
                "context_used": bool(state.ai_context),
            }
            ctx["tokens_used"] = 220
            state.total_tokens += 220

    async def _generate_sections(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="generate_sections",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
            model_used=PIPELINE_MODEL_NAME,
        ) as ctx:
            state.sections = [
                {
                    "heading": heading,
                    "body": f"{heading} for topic '{state.topic.title}'.",
                }
                for heading in state.outline.get("sections", [])
            ]
            ctx["tokens_used"] = 1200
            state.total_tokens += 1200

    async def _merge_content(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="merge_content",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
        ):
            body = "\n\n".join(
                f"## {section['heading']}\n{section['body']}" for section in state.sections
            )
            state.merged_content = {
                "title": state.topic.title,
                "body": body,
                "sections": state.sections,
            }

    async def _optimize_seo(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="seo_optimization",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
            model_used=PIPELINE_MODEL_NAME,
        ) as ctx:
            keyword = state.topic.slug.replace("-", " ")
            state.seo_data = {
                "primary_keyword": keyword,
                "secondary_keywords": [f"{keyword} guide", f"{keyword} tips"],
                "readability_score": 70,
            }
            ctx["tokens_used"] = 260
            state.total_tokens += 260

    async def _apply_internal_linking(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="internal_linking",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
        ):
            state.internal_links = [
                {"anchor": "related topic", "url": "/blog/related-topic"},
                {"anchor": "service page", "url": "/services"},
            ]
            links_markdown = "\n".join(
                f"- [{link['anchor']}]({link['url']})" for link in state.internal_links
            )
            state.merged_content["body"] = (
                f"{state.merged_content.get('body', '')}\n\nInternal links:\n{links_markdown}"
            )

    async def _generate_metadata(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="generate_metadata",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
            model_used=PIPELINE_MODEL_NAME,
        ) as ctx:
            state.metadata = {
                "title": state.topic.title,
                "description": f"Practical guide about {state.topic.title.lower()}",
                "canonical_slug": state.topic.slug,
            }
            ctx["tokens_used"] = 140
            state.total_tokens += 140

    async def _compute_metrics(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="compute_metrics",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
        ):
            body = state.merged_content.get("body", "")
            word_count = len(body.split())
            link_count = body.count("](")
            state.metrics = {
                "word_count": word_count,
                "link_count": link_count,
                "total_tokens": state.total_tokens,
            }

    async def _save_article(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="save_article",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            request_id=request_id,
        ):
            article = Article(
                topic_id=state.topic.id,
                title=state.metadata.get("title") or state.topic.title,
                slug=state.metadata.get("canonical_slug") or state.topic.slug,
                status="draft",
                word_count=state.metrics.get("word_count"),
                content_json={
                    "outline": state.outline,
                    "sections": state.sections,
                    "body": state.merged_content.get("body", ""),
                    "internal_links": state.internal_links,
                },
                seo_data={
                    **state.seo_data,
                    **{
                        "meta_title": state.metadata.get("title"),
                        "meta_description": state.metadata.get("description"),
                    },
                },
                model_used=PIPELINE_MODEL_NAME,
                total_tokens=state.metrics.get("total_tokens"),
            )
            self._db.add(article)
            await self._db.flush()
            state.article = article

    async def _set_topic_completed(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        async with timed_generation_step(
            self._db,
            step="update_topic_status",
            task_name=PIPELINE_TASK_NAME,
            user_id=user_id,
            project_id=project_id,
            topic_id=topic_id,
            article_id=state.article.id if state.article else None,
            request_id=request_id,
        ):
            state.topic.status = "completed"
            await self._db.flush()

    async def _mark_topic_failed(self, topic: Topic) -> None:
        if topic.status != "completed":
            topic.status = "failed"
            await self._db.flush()
