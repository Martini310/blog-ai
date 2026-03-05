"""
GenerationLog schema used internally to record LLM operations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class GenerationLogCreate(BaseModel):
    """Passed to the logging service – all fields optional except status."""

    user_id: UUID | None = None
    project_id: UUID | None = None
    topic_id: UUID | None = None
    article_id: UUID | None = None
    request_id: str | None = None
    task_name: str | None = None
    step: str | None = None
    model_used: str | None = None
    status: str = "success"
    tokens_used: int | None = None
    duration_ms: int | None = None
    error_message: str | None = None
    extra: dict = Field(default_factory=dict)


class GenerationLogOut(BaseModel):
    id: UUID
    created_at: datetime
    user_id: UUID | None
    project_id: UUID | None
    topic_id: UUID | None
    step: str | None
    status: str
    tokens_used: int | None
    duration_ms: int | None
    model_config = {"from_attributes": True}
