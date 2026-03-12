import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.services.subscription_limit_service import (
    MonthlyUsage,
    SubscriptionLimitExceededError,
    SubscriptionLimitService,
)


class DummyDB:
    def __init__(self, scalar_results: list[int | None]) -> None:
        self._scalar_results = list(scalar_results)

    async def scalar(self, _stmt):
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)


def test_month_bounds_handles_december_rollover() -> None:
    now = datetime(2026, 12, 21, 11, 0, tzinfo=UTC)
    start, end = SubscriptionLimitService._month_bounds(now)
    assert start == datetime(2026, 12, 1, 0, 0, tzinfo=UTC)
    assert end == datetime(2027, 1, 1, 0, 0, tzinfo=UTC)


def test_month_bounds_handles_naive_datetime() -> None:
    now = datetime(2026, 3, 12, 8, 0)
    start, end = SubscriptionLimitService._month_bounds(now)
    assert start == datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 4, 1, 0, 0, tzinfo=UTC)


def test_ensure_project_creation_allowed_raises_when_limit_exceeded() -> None:
    user_id = uuid4()
    service = SubscriptionLimitService(DummyDB([3]))
    service.get_effective_limits = AsyncMock(
        return_value=SimpleNamespace(plan_slug="free", max_projects=3)
    )

    async def runner() -> None:
        try:
            await service.ensure_project_creation_allowed(user_id)
            assert False, "Expected limit exception."
        except SubscriptionLimitExceededError as exc:
            assert "max 3 active projects" in str(exc)

    asyncio.run(runner())


def test_get_article_quota_status_uses_usage_and_plan_limits() -> None:
    user_id = uuid4()
    service = SubscriptionLimitService(DummyDB([]))
    service.get_effective_limits = AsyncMock(
        return_value=SimpleNamespace(plan_slug="pro", max_articles_per_month=50)
    )
    service.get_monthly_usage = AsyncMock(
        return_value=MonthlyUsage(
            period_start=datetime(2026, 3, 1, tzinfo=UTC),
            period_end=datetime(2026, 4, 1, tzinfo=UTC),
            articles_generated=20,
            tokens_used=12345,
        )
    )

    quota = asyncio.run(service.get_article_quota_status(user_id))
    assert quota.allowed is True
    assert quota.plan_slug == "pro"
    assert quota.used_articles == 20
    assert quota.max_articles == 50
    assert quota.remaining_articles == 30
    assert quota.tokens_used == 12345
