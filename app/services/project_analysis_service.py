"""
Project analysis service.

Responsible for analyzing a project (its name, description, domain) and 
generating an AI context that will be used for topic and article generation.
"""
import uuid
import re
import httpx
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectAnalysis
from app.services.generation_log_service import timed_generation_step
from app.services.llm_service import LLMResult, LLMService


class ProjectAnalysisError(Exception):
    """Raised when project analysis fails."""


class ProjectAnalysisService:
    def __init__(self, db: AsyncSession, llm_service: LLMService | None = None) -> None:
        self._db = db
        self._llm_service = llm_service

    def _get_llm(self) -> LLMService:
        if not self._llm_service:
            self._llm_service = LLMService()
        return self._llm_service

    async def analyze_project(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> dict[str, Any]:
        project = await self._get_project(project_id=project_id, owner_id=user_id)
        analysis = await self._get_or_create_analysis(project_id=project_id)

        try:
            await self._set_analysis_status(analysis, "running")

            async with timed_generation_step(
                self._db,
                step="project_analysis",
                task_name="analyse_project",
                user_id=user_id,
                project_id=project_id,
                request_id=request_id,
                model_used=self._get_llm().model_name,
            ) as ctx:
                system_prompt = (
                    "You are an expert SEO strategist and Content Director. "
                    "Your job is to analyze the user's project details and generate a "
                    "strategic AI context for future content generation. "
                    "Return strict JSON only."
                )
                user_prompt = (
                    f"Analyze the following project:\n"
                    f"Name: {project.name}\n"
                    f"Description: {project.description or 'N/A'}\n"
                    f"Domain: {project.domain or 'N/A'}\n"
                    f"Target Language: {project.language}\n\n"
                    "Return a JSON object with the following keys:\n"
                    "- target_audience: string describing the primary audience\n"
                    "- tone_of_voice: string describing the recommended content tone\n"
                    "- core_topics: array of 3-5 strings with main content pillars\n"
                    "- ai_context: a comprehensive, 150-250 word strategic summary "
                    "combining company background, tone, positioning, and unique advantages. "
                    "This text will be injected into all future AI prompts to guide "
                    "article generation. Make it highly compressed and actionable."
                )

                result = await self._get_llm().generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.3,
                    max_tokens=800,
                )
                ctx["tokens_used"] = result.tokens_used
                
                normalized_result = self._normalize_analysis(result)
                
                scraped_articles = []
                if project.blog_url:
                    scraped_articles = await self._scrape_blog(project.blog_url)
                
                normalized_result["scraped_articles"] = scraped_articles
                analysis.result = normalized_result
                analysis.ai_context = normalized_result.get("ai_context", "")

            await self._set_analysis_status(analysis, "completed")

        except Exception as exc:
            await self._mark_analysis_failed(analysis, str(exc))
            raise

        return {
            "project_id": str(project_id),
            "status": "completed",
            "ai_context_length": len(analysis.ai_context),
        }

    async def analyze_project_from_url(
        self,
        *,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        url: str,
        request_id: str | None,
    ) -> dict[str, Any]:
        """Alternative analysis approach that utilizes Tavily to scrape/search the actual URL
        to build the AI context based on real data."""
        project = await self._get_project(project_id=project_id, owner_id=user_id)
        analysis = await self._get_or_create_analysis(project_id=project_id)

        try:
            await self._set_analysis_status(analysis, "running")

            async with timed_generation_step(
                self._db,
                step="project_analysis",
                task_name="analyse_project_from_url",
                user_id=user_id,
                project_id=project_id,
                request_id=request_id,
                model_used=self._get_llm().model_name,
            ) as ctx:
                # 1. Fetch real-world context using Tavily
                from app.services.tavily_service import TavilyService
                tavily = TavilyService()
                query = f"What is {url}? Provide an overview, target audience, tone of voice, and core topics or products."
                web_context = await tavily.get_context(query)

                system_prompt = (
                    "You are an expert SEO strategist and Content Director. "
                    "Your job is to analyze the user's project details and the provided real web research "
                    "to generate a strategic AI context for future content generation. "
                    "Return strict JSON only."
                )
                user_prompt = (
                    f"Analyze the following project using the provided web research:\n"
                    f"Name: {project.name}\n"
                    f"Provided URL: {url}\n"
                    f"Description: {project.description or 'N/A'}\n"
                    f"Domain: {project.domain or 'N/A'}\n"
                    f"Target Language: {project.language}\n\n"
                    f"--- WEB RESEARCH (Tavily) ---\n"
                    f"{web_context}\n"
                    f"-----------------------------\n\n"
                    "Return a JSON object with the following keys:\n"
                    "- target_audience: string describing the primary audience\n"
                    "- tone_of_voice: string describing the recommended content tone\n"
                    "- core_topics: array of 3-5 strings with main content pillars\n"
                    "- ai_context: a comprehensive, 150-250 word strategic summary "
                    "combining company background, tone, positioning, and unique advantages. "
                    "This text will be injected into all future AI prompts to guide "
                    "article generation. Make it highly compressed and actionable."
                )

                result = await self._get_llm().generate_json(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.3,
                    max_tokens=800,
                )
                ctx["tokens_used"] = result.tokens_used
                
                normalized_result = self._normalize_analysis(result)
                
                # Try to scrape but don't fail if we can't
                scraped_articles = await self._scrape_blog(url)
                
                normalized_result["scraped_articles"] = scraped_articles
                analysis.result = normalized_result
                analysis.ai_context = normalized_result.get("ai_context", "")

            await self._set_analysis_status(analysis, "completed")

        except Exception as exc:
            await self._mark_analysis_failed(analysis, str(exc))
            raise

        return {
            "project_id": str(project_id),
            "status": "completed",
            "ai_context_length": len(analysis.ai_context),
        }

    async def _get_project(self, *, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
        stmt = select(Project).where(
            Project.id == project_id,
            Project.owner_id == owner_id,
        )
        project = await self._db.scalar(stmt)
        if not project:
            raise ProjectAnalysisError(f"Project {project_id} not found.")
        return project

    async def _get_or_create_analysis(self, *, project_id: uuid.UUID) -> ProjectAnalysis:
        stmt = select(ProjectAnalysis).where(ProjectAnalysis.project_id == project_id).with_for_update()
        analysis = await self._db.scalar(stmt)
        if not analysis:
            analysis = ProjectAnalysis(project_id=project_id, status="pending")
            self._db.add(analysis)
            await self._db.flush()
        return analysis

    async def _set_analysis_status(self, analysis: ProjectAnalysis, status: str) -> None:
        analysis.status = status
        analysis.error_message = None
        await self._db.flush()

    async def _mark_analysis_failed(self, analysis: ProjectAnalysis, error_message: str) -> None:
        analysis.status = "failed"
        analysis.error_message = error_message
        await self._db.flush()

    async def _scrape_blog(self, url: str) -> list[str]:
        try:
            from app.core.logging import get_logger
            logger = get_logger(__name__)
            logger.info("scraping_blog_started", url=url)
            
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text
                
                # Simple extraction using regex for <h1/2/3> tags and <title>
                titles = []
                # Extract <title>
                title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
                if title_match:
                    titles.append(title_match.group(1).strip())
                    
                # Extract headers
                header_matches = re.finditer(r'<h[1-3][^>]*>(.*?)</h[1-3]>', html, re.IGNORECASE | re.DOTALL)
                for match in header_matches:
                    text = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    if text and len(text) > 10 and text not in titles:
                        titles.append(text)
                
                logger.info("scraping_blog_completed", urls_found=len(titles))
                return titles[:20]  # Return max 20 headers/titles
        except Exception as e:
            from app.core.logging import get_logger
            get_logger(__name__).warning("scraping_blog_failed", url=url, error=str(e))
            return []

    @staticmethod
    def _normalize_analysis(result: LLMResult) -> dict[str, Any]:
        data = result.data if isinstance(result.data, dict) else {}
        
        core_topics_raw = data.get("core_topics")
        core_topics: list[str] = []
        if isinstance(core_topics_raw, list):
            for item in core_topics_raw:
                text = str(item).strip()
                if text:
                    core_topics.append(text)
                    
        if not core_topics:
            core_topics = ["General topics", "Industry news", "How-to guides"]

        fallback_ai_context = f"Target audience: {data.get('target_audience', 'General')}. Tone: {data.get('tone_of_voice', 'Professional')}."

        return {
            "target_audience": str(data.get("target_audience") or "Broad audience").strip(),
            "tone_of_voice": str(data.get("tone_of_voice") or "Professional and informative").strip(),
            "core_topics": core_topics,
            "ai_context": str(data.get("ai_context") or fallback_ai_context).strip(),
        }
