"""
Project and ProjectAnalysis models.

A Project is the top-level container owned by a User.
ProjectAnalysis stores the AI-generated analysis results for a project.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.content import ContentSchedule, Topic


class Project(UUIDMixin, TimestampMixin, Base):
    """
    Core organisational unit. A user can have multiple projects,
    each targeting a different niche or domain.
    """

    __tablename__ = "projects"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String(255))   # e.g. "tech", "finance"
    blog_url: Mapped[str | None] = mapped_column(String(500)) # URL to scrape for existing topics
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active"
    )  # active | paused | archived
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    owner: Mapped["User"] = relationship("User", back_populates="projects")
    analysis: Mapped["ProjectAnalysis | None"] = relationship(
        "ProjectAnalysis", back_populates="project", uselist=False, lazy="select", cascade="all, delete-orphan"
    )
    topics: Mapped[list["Topic"]] = relationship(
        "Topic", back_populates="project", lazy="select", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["ContentSchedule"]] = relationship(
        "ContentSchedule", back_populates="project", lazy="select", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


class ProjectAnalysis(UUIDMixin, TimestampMixin, Base):
    """
    Stores the latest AI analysis snapshot for a project.
    'ai_context' stores compact strategic memory reused by downstream
    generation tasks to avoid resending full project description.
    'result' is JSONB to accommodate variable LLM output structure.
    """

    __tablename__ = "project_analyses"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )  # pending | running | completed | failed
    ai_context: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship("Project", back_populates="analysis")

    __table_args__ = (Index("ix_project_analyses_status", "status"),)

    def __repr__(self) -> str:
        return f"<ProjectAnalysis project_id={self.project_id} status={self.status}>"
