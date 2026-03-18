"""
Project analysis service.

Responsible for analyzing a project (its name, description, domain) and 
generating an AI context that will be used for topic and article generation.
"""
import uuid
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
