"""align_topic_queue_and_ai_context

Revision ID: 8f3c1a6b2d44
Revises: 6e530ad89a95
Create Date: 2026-03-12 12:00:00.000000+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8f3c1a6b2d44"
down_revision: Union[str, None] = "6e530ad89a95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_analyses",
        sa.Column("ai_context", sa.Text(), server_default=sa.text("''"), nullable=False),
    )

    op.add_column("topics", sa.Column("scheduled_date", sa.Date(), nullable=True))
    op.create_index("ix_topics_scheduled_date", "topics", ["scheduled_date"], unique=False)

    op.execute("UPDATE topics SET status = 'queued' WHERE status = 'pending'")
    op.alter_column(
        "topics",
        "status",
        existing_type=sa.String(length=30),
        server_default=sa.text("'queued'"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("UPDATE topics SET status = 'pending' WHERE status = 'queued'")
    op.alter_column(
        "topics",
        "status",
        existing_type=sa.String(length=30),
        server_default=sa.text("'pending'"),
        existing_nullable=False,
    )

    op.drop_index("ix_topics_scheduled_date", table_name="topics")
    op.drop_column("topics", "scheduled_date")
    op.drop_column("project_analyses", "ai_context")
