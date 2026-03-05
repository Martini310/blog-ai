"""
GenerationLog – append-only audit trail for every LLM generation step.

Each row represents one atomic generation operation (e.g. outline generation,
article section, SEO meta). This table is write-heavy; avoid UPDATE/DELETE.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GenerationLog(Base):
    """
    Immutable log entry. No updated_at – logs are never modified after insert.
    Use for billing, debugging, and analytics.
    """

    __tablename__ = "generation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Reference context (nullable – log may be created before DB objects exist)
    # -------------------------------------------------------------------------
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    topic_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    article_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"), nullable=True
    )

    # -------------------------------------------------------------------------
    # Execution context
    # -------------------------------------------------------------------------
    request_id: Mapped[str | None] = mapped_column(String(36))  # correlation ID
    task_name: Mapped[str | None] = mapped_column(String(255))   # Celery task name
    step: Mapped[str | None] = mapped_column(String(100))        # e.g. "outline", "section_1"
    model_used: Mapped[str | None] = mapped_column(String(100))

    # -------------------------------------------------------------------------
    # Outcome
    # -------------------------------------------------------------------------
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="success"
    )  # success | failed | partial
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)

    # Flexible blob for prompt/response excerpts, cost data, etc.
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_generation_logs_user_id", "user_id"),
        Index("ix_generation_logs_project_id", "project_id"),
        Index("ix_generation_logs_topic_id", "topic_id"),
        Index("ix_generation_logs_task_name", "task_name"),
        Index("ix_generation_logs_created_at", "created_at"),
        Index("ix_generation_logs_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<GenerationLog id={self.id} step={self.step!r} "
            f"status={self.status} tokens={self.tokens_used}>"
        )
