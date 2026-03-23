"""
Content pipeline models: ContentSchedule, Topic, Article.

Flow:  Project → Topic → Article
       Project → ContentSchedule (when to trigger generation)
"""
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class ContentSchedule(UUIDMixin, TimestampMixin, Base):
    """
    Defines when automatic article generation should run for a project.
    cron_expression follows standard cron syntax (handled by Celery Beat).
    """

    __tablename__ = "content_schedules"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    project: Mapped["Project"] = relationship("Project", back_populates="schedules")

    __table_args__ = (
        Index("ix_content_schedules_project_id", "project_id"),
        Index("ix_content_schedules_is_active", "is_active"),
        Index("ix_content_schedules_next_run_at", "next_run_at"),
    )

    def __repr__(self) -> str:
        return f"<ContentSchedule project_id={self.project_id} cron={self.cron_expression!r}>"


class Topic(UUIDMixin, TimestampMixin, Base):
    """
    A topic (keyword cluster) within a Project.
    Articles are generated from topics.
    'metadata' stores SEO data, search volume estimates, etc.
    """

    __tablename__ = "topics"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="queued"
    )  # queued | scheduled | in_progress | completed | failed | skipped
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    topic_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    project: Mapped["Project"] = relationship("Project", back_populates="topics")
    articles: Mapped[list["Article"]] = relationship(
        "Article", back_populates="topic", lazy="select", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_topics_project_id", "project_id"),
        Index("ix_topics_status", "status"),
        Index("ix_topics_scheduled_date", "scheduled_date"),
        Index("ix_topics_priority", "priority"),
    )

    def __repr__(self) -> str:
        return f"<Topic id={self.id} title={self.title!r} status={self.status}>"


class Article(UUIDMixin, TimestampMixin, Base):
    """
    The generated article entity.
    'content_json' stores structured content (sections, headings, metadata).
    'seo_data' stores title, description, keywords etc.
    """

    __tablename__ = "articles"

    topic_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(500))
    slug: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft"
    )  # draft | review | published | failed
    word_count: Mapped[int | None] = mapped_column(Integer)
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    seo_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model_used: Mapped[str | None] = mapped_column(String(100))
    total_tokens: Mapped[int | None] = mapped_column(Integer)

    topic: Mapped[Topic] = relationship("Topic", back_populates="articles")

    __table_args__ = (
        Index("ix_articles_topic_id", "topic_id"),
        Index("ix_articles_status", "status"),
        Index("ix_articles_published_at", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<Article id={self.id} title={self.title!r} status={self.status}>"
