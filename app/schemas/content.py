"""
Content pipeline schemas: Topic, Article, ContentSchedule.
"""
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMBase


# ---------------------------------------------------------------------------
# Topic
# ---------------------------------------------------------------------------

class TopicCreate(BaseModel):
    title: str = Field(max_length=500)
    slug: str = Field(max_length=500)
    status: Literal["proposed", "queued", "scheduled", "rejected"] = "queued"
    scheduled_date: date | None = None
    priority: int = Field(default=0, ge=0, le=100)
    topic_metadata: dict = Field(default_factory=dict)


class TopicUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(default=None, max_length=500)
    status: Literal["proposed", "queued", "scheduled", "in_progress", "completed", "failed", "skipped", "rejected"] | None = None
    scheduled_date: date | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    topic_metadata: dict | None = None


class TopicBulkUpdate(BaseModel):
    topic_ids: list[UUID]
    update_data: TopicUpdate


class TopicOut(ORMBase):
    id: UUID
    project_id: UUID
    title: str
    slug: str
    status: Literal["proposed", "queued", "scheduled", "in_progress", "completed", "failed", "skipped", "rejected"]
    scheduled_date: date | None
    priority: int
    topic_metadata: dict
    created_at: datetime


# ---------------------------------------------------------------------------
# Article
# ---------------------------------------------------------------------------

class ArticleOut(ORMBase):
    id: UUID
    topic_id: UUID
    title: str | None
    slug: str | None
    status: str
    word_count: int | None
    content_json: dict
    seo_data: dict
    published_at: datetime | None
    model_used: str | None
    total_tokens: int | None
    created_at: datetime


# ---------------------------------------------------------------------------
# ContentSchedule
# ---------------------------------------------------------------------------

class ContentScheduleCreate(BaseModel):
    cron_expression: str = Field(max_length=100)
    config: dict = Field(default_factory=dict)


class ContentScheduleOut(ORMBase):
    id: UUID
    project_id: UUID
    cron_expression: str
    is_active: bool
    last_run_at: datetime | None
    next_run_at: datetime | None
    config: dict
    created_at: datetime
