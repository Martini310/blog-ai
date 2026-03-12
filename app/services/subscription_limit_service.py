"""
Subscription limit service.

Enforces plan-based limits for project creation and monthly article generation.
"""
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as app_settings
from app.models.content import Article, Topic
from app.models.generation_log import GenerationLog
from app.models.project import Project
from app.models.subscription import SubscriptionPlan, UserSubscription

ACTIVE_SUBSCRIPTION_STATUSES = ("active", "trialing")


@dataclass(slots=True)
class EffectivePlanLimits:
    plan_slug: str
    max_projects: int
    max_articles_per_month: int


@dataclass(slots=True)
class MonthlyUsage:
    period_start: datetime
    period_end: datetime
    articles_generated: int
    tokens_used: int


@dataclass(slots=True)
class ArticleQuotaStatus:
    allowed: bool
    plan_slug: str
    used_articles: int
    max_articles: int
    remaining_articles: int
    tokens_used: int
    period_start: datetime
    period_end: datetime


class SubscriptionLimitExceededError(Exception):
    pass


class SubscriptionLimitService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_effective_limits(self, user_id: uuid.UUID) -> EffectivePlanLimits:
        plan = await self._db.scalar(
            select(SubscriptionPlan)
            .join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id)
            .where(
                UserSubscription.user_id == user_id,
                UserSubscription.status.in_(ACTIVE_SUBSCRIPTION_STATUSES),
                SubscriptionPlan.is_active.is_(True),
            )
            .order_by(UserSubscription.updated_at.desc())
            .limit(1)
        )
        if not plan:
            return EffectivePlanLimits(
                plan_slug="free",
                max_projects=app_settings.MAX_PROJECTS_FREE_TIER,
                max_articles_per_month=app_settings.MAX_ARTICLES_PER_MONTH_FREE_TIER,
            )

        return EffectivePlanLimits(
            plan_slug=plan.slug,
            max_projects=plan.max_projects,
            max_articles_per_month=plan.max_articles_per_month,
        )

    async def ensure_project_creation_allowed(self, user_id: uuid.UUID) -> None:
        limits = await self.get_effective_limits(user_id)
        active_projects_count = await self._db.scalar(
            select(func.count(Project.id)).where(
                Project.owner_id == user_id,
                Project.status != "archived",
            )
        ) or 0
        if active_projects_count >= limits.max_projects:
            raise SubscriptionLimitExceededError(
                f"Plan '{limits.plan_slug}' allows max {limits.max_projects} active projects."
            )

    async def get_article_quota_status(
        self,
        user_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> ArticleQuotaStatus:
        limits = await self.get_effective_limits(user_id)
        usage = await self.get_monthly_usage(user_id, now=now)
        remaining_articles = max(0, limits.max_articles_per_month - usage.articles_generated)
        return ArticleQuotaStatus(
            allowed=usage.articles_generated < limits.max_articles_per_month,
            plan_slug=limits.plan_slug,
            used_articles=usage.articles_generated,
            max_articles=limits.max_articles_per_month,
            remaining_articles=remaining_articles,
            tokens_used=usage.tokens_used,
            period_start=usage.period_start,
            period_end=usage.period_end,
        )

    async def ensure_article_generation_allowed(
        self,
        user_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> ArticleQuotaStatus:
        quota = await self.get_article_quota_status(user_id, now=now)
        if quota.allowed:
            return quota
        raise SubscriptionLimitExceededError(
            f"Monthly article limit reached ({quota.used_articles}/{quota.max_articles}) "
            f"for plan '{quota.plan_slug}'."
        )

    async def get_monthly_usage(
        self,
        user_id: uuid.UUID,
        *,
        now: datetime | None = None,
    ) -> MonthlyUsage:
        current = now or datetime.now(UTC)
        period_start, period_end = self._month_bounds(current)

        articles_generated = await self._db.scalar(
            select(func.count(Article.id))
            .select_from(Article)
            .join(Topic, Article.topic_id == Topic.id)
            .join(Project, Topic.project_id == Project.id)
            .where(
                Project.owner_id == user_id,
                Article.created_at >= period_start,
                Article.created_at < period_end,
            )
        ) or 0

        tokens_used = await self._db.scalar(
            select(func.coalesce(func.sum(GenerationLog.tokens_used), 0)).where(
                GenerationLog.user_id == user_id,
                GenerationLog.created_at >= period_start,
                GenerationLog.created_at < period_end,
            )
        ) or 0

        return MonthlyUsage(
            period_start=period_start,
            period_end=period_end,
            articles_generated=int(articles_generated),
            tokens_used=int(tokens_used),
        )

    @staticmethod
    def _month_bounds(now: datetime) -> tuple[datetime, datetime]:
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        period_start = datetime(now.year, now.month, 1, tzinfo=UTC)
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
        else:
            period_end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

        return period_start, period_end
