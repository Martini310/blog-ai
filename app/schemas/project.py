"""
Project and ProjectAnalysis schemas.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


class ProjectCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = None
    domain: str | None = Field(default=None, max_length=255)
    language: str = Field(default="en", max_length=10)
    settings: dict = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    domain: str | None = None
    language: str | None = None
    status: str | None = None
    settings: dict | None = None


class ProjectOut(ORMBase):
    id: UUID
    owner_id: UUID
    name: str
    description: str | None
    domain: str | None
    language: str
    status: str
    settings: dict
    created_at: datetime
    updated_at: datetime


class ProjectAnalysisOut(ORMBase):
    id: UUID
    project_id: UUID
    status: str
    ai_context: str
    result: dict
    error_message: str | None
    created_at: datetime
    updated_at: datetime
