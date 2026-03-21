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
from app.services.llm_service import LLMResult, LLMService
from app.services.section_generation_service import SectionGenerationService
from app.services.tavily_service import TavilyService

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
    def __init__(self, db: AsyncSession, llm_service: LLMService | None = None) -> None:
        self._db = db
        self._llm_service = llm_service

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

    def _get_llm(self) -> LLMService:
        if not self._llm_service:
            self._llm_service = LLMService()
        return self._llm_service

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
            model_used=self._get_llm().model_name,
        ) as ctx:
            system_prompt = (
                "You are an expert SEO strategist. "
                "Return strict JSON only."
            )
            user_prompt = (
                "Prepare an SEO article outline.\n"
                f"Topic: {state.topic.title}\n"
                f"Topic slug: {state.topic.slug}\n"
                f"Strategic context: {state.ai_context or 'N/A'}\n\n"
                "Return JSON with keys:\n"
                "- title: string\n"
                "- angle: string\n"
                "- sections: array of 4-8 section titles"
            )
            result = await self._get_llm().generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                max_tokens=900,
            )
            ctx["tokens_used"] = result.tokens_used
            state.total_tokens += result.tokens_used
            state.outline = self._normalize_outline(result, fallback_title=state.topic.title)

    async def _generate_sections(
        self,
        *,
        state: ArticlePipelineState,
        project_id: uuid.UUID,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> None:
        tavily_service = TavilyService()
        section_gen_service = SectionGenerationService(llm_service=self._get_llm())

        sections = []
        outline_sections = state.outline.get("sections", [])
        topic_slug = state.topic.slug or ""
        keyword = topic_slug.replace("-", " ")

        for heading in outline_sections:
            context_text = ""
            async with timed_generation_step(
                self._db,
                step="tavily_fetch",
                task_name=PIPELINE_TASK_NAME,
                user_id=user_id,
                project_id=project_id,
                topic_id=topic_id,
                request_id=request_id,
            ):
                query = f"{state.topic.title} {heading}"
                context_text = await tavily_service.get_context(query)

            async with timed_generation_step(
                self._db,
                step="section_generation",
                task_name=PIPELINE_TASK_NAME,
                user_id=user_id,
                project_id=project_id,
                topic_id=topic_id,
                request_id=request_id,
                model_used=self._get_llm().model_name,
            ) as ctx:
                result = await section_gen_service.generate_section(
                    topic=state.topic.title,
                    section_title=heading,
                    section_description=state.ai_context,
                    keyword=keyword,
                    context=context_text,
                )
                
                tokens_used = result.get("tokens_used", 0)
                ctx["tokens_used"] = tokens_used
                state.total_tokens += tokens_used

                sections.append({
                    "heading": heading,
                    "body": result.get("body", "")
                })

        state.sections = sections

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
                "title": state.outline.get("title") or state.topic.title,
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
            model_used=self._get_llm().model_name,
        ) as ctx:
            system_prompt = (
                "You are an SEO analyst. Return strict JSON only."
            )
            user_prompt = (
                f"Topic: {state.topic.title}\n"
                f"Article body excerpt: {state.merged_content.get('body', '')[:1800]}\n\n"
                "Return JSON:\n"
                "- primary_keyword: string\n"
                "- secondary_keywords: array of 3-6 strings\n"
                "- readability_score: integer 1-100"
            )
            result = await self._get_llm().generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=500,
            )
            ctx["tokens_used"] = result.tokens_used
            state.total_tokens += result.tokens_used
            state.seo_data = self._normalize_seo(result, fallback_slug=state.topic.slug)

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
            model_used=self._get_llm().model_name,
        ) as ctx:
            system_prompt = (
                "You are a technical SEO editor. Return strict JSON only."
            )
            user_prompt = (
                f"Prepare metadata for article '{state.merged_content.get('title')}'.\n"
                f"Primary keyword: {state.seo_data.get('primary_keyword')}\n"
                f"Topic slug: {state.topic.slug}\n\n"
                "Return JSON:\n"
                "- title: string (max 60 chars)\n"
                "- description: string (120-160 chars)\n"
                "- canonical_slug: string"
            )
            result = await self._get_llm().generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=300,
            )
            ctx["tokens_used"] = result.tokens_used
            state.total_tokens += result.tokens_used
            state.metadata = self._normalize_metadata(result, fallback_slug=state.topic.slug)

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
                model_used=self._get_llm().model_name,
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

    @staticmethod
    def _normalize_outline(result: LLMResult, *, fallback_title: str) -> dict[str, Any]:
        data = result.data if isinstance(result.data, dict) else {}
        sections_raw = data.get("sections")
        sections: list[str] = []
        if isinstance(sections_raw, list):
            for item in sections_raw:
                text = str(item).strip()
                if text:
                    sections.append(text)
        if len(sections) < 3:
            sections = ["Introduction", "Core Concepts", "Implementation Steps", "Conclusion"]
        return {
            "title": str(data.get("title") or fallback_title),
            "angle": str(data.get("angle") or ""),
            "sections": sections[:8],
            "context_used": True,
        }

    @staticmethod
    def _normalize_sections(
        result: LLMResult,
        *,
        fallback_sections: list[str],
    ) -> list[dict[str, str]]:
        data = result.data if isinstance(result.data, dict) else {}
        raw_items = data.get("sections")
        sections: list[dict[str, str]] = []

        if isinstance(raw_items, list):
            for idx, item in enumerate(raw_items):
                if not isinstance(item, dict):
                    continue
                heading = str(item.get("heading") or f"Section {idx + 1}").strip()
                body = str(item.get("body") or "").strip()
                if heading and body:
                    sections.append({"heading": heading, "body": body})

        if sections:
            return sections

        fallback: list[dict[str, str]] = []
        for heading in fallback_sections:
            fallback.append(
                {
                    "heading": heading,
                    "body": (
                        f"{heading} for topic content strategy. "
                        "Expand this section with practical guidance and examples."
                    ),
                }
            )
        return fallback

    @staticmethod
    def _normalize_seo(result: LLMResult, *, fallback_slug: str) -> dict[str, Any]:
        data = result.data if isinstance(result.data, dict) else {}
        primary = str(data.get("primary_keyword") or fallback_slug.replace("-", " ")).strip()

        secondary_raw = data.get("secondary_keywords")
        secondary: list[str] = []
        if isinstance(secondary_raw, list):
            for item in secondary_raw:
                text = str(item).strip()
                if text:
                    secondary.append(text)

        readability = data.get("readability_score")
        try:
            readability_int = int(readability)
        except (TypeError, ValueError):
            readability_int = 70

        return {
            "primary_keyword": primary,
            "secondary_keywords": secondary or [f"{primary} guide", f"{primary} checklist"],
            "readability_score": max(1, min(100, readability_int)),
        }

    @staticmethod
    def _normalize_metadata(result: LLMResult, *, fallback_slug: str) -> dict[str, str]:
        data = result.data if isinstance(result.data, dict) else {}
        canonical_slug = str(data.get("canonical_slug") or fallback_slug).strip().strip("/")
        if not canonical_slug:
            canonical_slug = fallback_slug
        return {
            "title": str(data.get("title") or "").strip()[:120],
            "description": str(data.get("description") or "").strip()[:220],
            "canonical_slug": canonical_slug,
        }
