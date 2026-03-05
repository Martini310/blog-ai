"""
Subscription models.

SubscriptionPlan – catalogue of available plans (free, pro, enterprise).
UserSubscription  – a user's active subscription instance.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


class SubscriptionPlan(UUIDMixin, TimestampMixin, Base):
    """
    Defines limits and pricing for each tier.
    'features' stores arbitrary JSON capability flags (e.g. {"gpt4": true}).
    """

    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    price_monthly_usd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_projects: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_topics: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    max_articles_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    features: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    subscriptions: Mapped[list["UserSubscription"]] = relationship(
        "UserSubscription", back_populates="plan", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<SubscriptionPlan slug={self.slug}>"


class UserSubscription(UUIDMixin, TimestampMixin, Base):
    """
    Tracks a user's current subscription status.
    One active subscription per user (enforced at service layer).
    """

    __tablename__ = "user_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subscription_plans.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="active"
    )  # active | trialing | past_due | cancelled
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    user: Mapped["User"] = relationship("User", back_populates="subscription")
    plan: Mapped[SubscriptionPlan] = relationship("SubscriptionPlan", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_user_subscriptions_status", "status"),
        Index("ix_user_subscriptions_period_end", "current_period_end"),
    )

    def __repr__(self) -> str:
        return f"<UserSubscription user_id={self.user_id} status={self.status}>"
