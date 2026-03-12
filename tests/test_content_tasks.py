import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.services.subscription_limit_service import ArticleQuotaStatus
from app.tasks import content_tasks


@dataclass
class DummyTopic:
    status: str


class DummyDB:
    def __init__(self, topic: DummyTopic | None = None) -> None:
        self.topic = topic
        self.flush_count = 0

    async def scalar(self, _stmt):
        return self.topic

    async def flush(self) -> None:
        self.flush_count += 1


class FakeLimitService:
    def __init__(self, quota: ArticleQuotaStatus) -> None:
        self.quota = quota

    async def get_article_quota_status(self, _user_id, *, now=None) -> ArticleQuotaStatus:
        return self.quota


class FakeGenerationLogService:
    def __init__(self) -> None:
        self.entries = []

    async def record(self, entry) -> None:
        self.entries.append(entry)


def test_generate_article_returns_blocked_limit_and_requeues_topic(monkeypatch) -> None:
    topic = DummyTopic(status="in_progress")
    db = DummyDB(topic=topic)
    quota = ArticleQuotaStatus(
        allowed=False,
        plan_slug="free",
        used_articles=20,
        max_articles=20,
        remaining_articles=0,
        tokens_used=0,
        period_start=datetime(2026, 3, 1, tzinfo=UTC),
        period_end=datetime(2026, 4, 1, tzinfo=UTC),
    )
    log_service = FakeGenerationLogService()

    @asynccontextmanager
    async def fake_get_db():
        yield db

    monkeypatch.setattr(content_tasks, "get_db", fake_get_db)
    monkeypatch.setattr(content_tasks, "SubscriptionLimitService", lambda _db: FakeLimitService(quota))
    monkeypatch.setattr(content_tasks, "GenerationLogService", lambda _db: log_service)

    result = asyncio.run(
        content_tasks._generate_article_async(
            topic_id=uuid4(),
            project_id=uuid4(),
            user_id=uuid4(),
            request_id="req-123",
        )
    )

    assert result["status"] == "blocked_limit"
    assert result["reason"] == "monthly_article_limit_exceeded"
    assert topic.status == "queued"
    assert db.flush_count == 1
    assert len(log_service.entries) == 1
    assert log_service.entries[0].step == "subscription_limit_check"


def test_generate_article_calls_pipeline_when_quota_allows(monkeypatch) -> None:
    db = DummyDB()
    quota = ArticleQuotaStatus(
        allowed=True,
        plan_slug="pro",
        used_articles=1,
        max_articles=20,
        remaining_articles=19,
        tokens_used=1200,
        period_start=datetime(2026, 3, 1, tzinfo=UTC),
        period_end=datetime(2026, 4, 1, tzinfo=UTC),
    )
    expected = {"status": "completed", "article_id": str(uuid4())}
    pipeline_calls = []

    class FakeArticleGenerationService:
        def __init__(self, _db) -> None:
            pass

        async def generate_for_topic(self, **kwargs):
            pipeline_calls.append(kwargs)
            return expected

    @asynccontextmanager
    async def fake_get_db():
        yield db

    monkeypatch.setattr(content_tasks, "get_db", fake_get_db)
    monkeypatch.setattr(content_tasks, "SubscriptionLimitService", lambda _db: FakeLimitService(quota))
    monkeypatch.setattr(content_tasks, "ArticleGenerationService", FakeArticleGenerationService)

    result = asyncio.run(
        content_tasks._generate_article_async(
            topic_id=uuid4(),
            project_id=uuid4(),
            user_id=uuid4(),
            request_id="req-234",
        )
    )

    assert result == expected
    assert len(pipeline_calls) == 1
