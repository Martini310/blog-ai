"""
Topic generation service.

Responsible for generating a batch of actionable topics based on the
AI context of a project.
"""
import uuid
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectAnalysis
from app.schemas.content import TopicCreate
from app.services.generation_log_service import timed_generation_step
from app.services.llm_service import LLMResult, LLMService
from app.services.topic_service import TopicService


class TopicGenerationError(Exception):
    """Raised when topic generation fails."""


class TopicGenerationService:
    def __init__(self, db: AsyncSession, llm_service: LLMService | None = None) -> None:
        self._db = db
        self._llm_service = llm_service
        self._topic_service = TopicService(db)

    def _get_llm(self) -> LLMService:
        if not self._llm_service:
            self._llm_service = LLMService()
        return self._llm_service

    async def generate_batch(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
        batch_size: int = 5,
        status: str = "queued",
    ) -> list[TopicCreate]:
        
        analysis = await self._get_project_analysis(project_id=project_id)
        if not analysis or not analysis.ai_context:
            raise TopicGenerationError(f"Project {project_id} analysis/context not found or incomplete.")

        try:
            async with timed_generation_step(
                self._db,
                step="topic_generation",
                task_name="generate_topics",
                user_id=user_id,
                project_id=project_id,
                request_id=request_id,
                model_used=self._get_llm().model_name,
            ) as ctx:
                
                scraped_articles = analysis.result.get("scraped_articles", [])
                scraped_context = ""
                if scraped_articles:
                    articles_list = "\n".join(f"- {title}" for title in scraped_articles)
                    scraped_context = f"\nExisting blog topics (DO NOT DUPLICATE THESE):\n{articles_list}\n"

                system_prompt = (
                    "You are an expert SEO Content Strategist. "
                    "Your job is to ideate a batch of article topics based on the project's strategic context. "
                    "Return strict JSON only."
                )
                user_prompt = (
                    f"Generate {batch_size} unique, SEO-optimized article topics for a project with the following context:\n\n"
                    f"{analysis.ai_context}\n{scraped_context}\n"
                    "Return a JSON object with a 'topics' array. Each item in the array must be an object with:\n"
                    "- title: string (the article title)\n"
                    "- slug: string (URL friendly slug, lowercase, separated by hyphens)\n"
                    "- priority: integer (1 to 100, where higher means more important/higher search intent)\n"
                )

                result = await self._get_llm().generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.6,
                    max_tokens=1000,
                )
                ctx["tokens_used"] = result.tokens_used
                
                topics_data = self._normalize_topics(result, batch_size=batch_size)
                
                created_topics = []
                for t in topics_data:
                    # Validate and clean slug
                    clean_slug = self._clean_slug(t["slug"], t["title"])
                    topic_in = TopicCreate(
                        title=t["title"],
                        slug=clean_slug,
                        status=status,
                        priority=t["priority"],
                    )
                    await self._topic_service.create(project_id=project_id, payload=topic_in)
                    created_topics.append(topic_in)

            return created_topics
            
        except Exception as exc:
            raise TopicGenerationError(f"Failed to generate topics: {exc}") from exc

    async def _get_project_analysis(self, *, project_id: uuid.UUID) -> ProjectAnalysis | None:
        stmt = select(ProjectAnalysis).where(ProjectAnalysis.project_id == project_id)
        return await self._db.scalar(stmt)

    @staticmethod
    def _normalize_topics(result: LLMResult, *, batch_size: int) -> list[dict]:
        data = result.data if isinstance(result.data, dict) else {}
        topics_raw = data.get("topics", [])
        
        normalized = []
        if isinstance(topics_raw, list):
            for i, item in enumerate(topics_raw):
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title") or f"Generated Topic {i+1}").strip()
                slug = str(item.get("slug") or title.lower().replace(" ", "-")).strip()
                
                try:
                    priority = int(item.get("priority", 50))
                except (ValueError, TypeError):
                    priority = 50
                    
                priority = max(0, min(100, priority))
                
                normalized.append({
                    "title": title[:500],
                    "slug": slug[:500],
                    "priority": priority,
                })
                
        # Fallback if empty or fewer than 1
        if not normalized:
            for i in range(batch_size):
                normalized.append({
                    "title": f"Fallback Strategy Topic {i+1}",
                    "slug": f"fallback-strategy-topic-{i+1}",
                    "priority": 50,
                })
                
        return normalized

    @staticmethod
    def _clean_slug(slug: str, title: str) -> str:
        s = slug or title
        s = s.lower().strip()
        s = re.sub(r'[^\w\s-]', '', s)
        s = re.sub(r'[-\s]+', '-', s)
        s = s.strip('-')
        if not s:
            import random
            s = f"topic-{random.randint(1000, 9999)}"
        return s
