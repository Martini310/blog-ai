import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.services.subscription_limit_service import ArticleQuotaStatus
from app.tasks import scheduler_tasks


@dataclass
class DummySchedule:
    id: UUID
    project_id: UUID
    config: dict = field(default_factory=dict)
    last_run_at: datetime | None = None


@dataclass
class DummyTopic:
    id: UUID


class FakeSchedulerService:
    def __init__(
        self,
        schedules: list[DummySchedule],
        owner_by_project: dict[UUID, UUID],
        topic_by_project: dict[UUID, DummyTopic | None],
    ) -> None:
        self.schedules = schedules
        self.owner_by_project = owner_by_project
        self.topic_by_project = topic_by_project
        self.reserve_calls = 0

    async def list_due_schedules(self, _now: datetime) -> list[DummySchedule]:
        return self.schedules

    async def get_project_owner_id(self, project_id: UUID) -> UUID | None:
        return self.owner_by_project.get(project_id)

    async def reserve_next_eligible_topic(self, project_id: UUID, _run_date):
        self.reserve_calls += 1
        return self.topic_by_project.get(project_id)

    async def has_topic_backlog(self, _project_id: UUID) -> bool:
        return False

    def should_request_topic_generation(self, _schedule: DummySchedule, _now: datetime) -> bool:
        return True

    def mark_topic_generation_requested(self, schedule: DummySchedule, now: datetime) -> None:
        schedule.config["topic_generation_requested_at"] = now.isoformat()

    def clear_topic_generation_marker(self, schedule: DummySchedule) -> None:
        schedule.config.pop("topic_generation_requested_at", None)

    def mark_schedule_run(self, schedule: DummySchedule, now: datetime) -> None:
        schedule.last_run_at = now


class FakeLimitService:
    def __init__(self, quota_by_user_id: dict[UUID, ArticleQuotaStatus]) -> None:
        self.quota_by_user_id = quota_by_user_id

    async def get_article_quota_status(self, user_id: UUID, *, now=None) -> ArticleQuotaStatus:
        return self.quota_by_user_id[user_id]


class FakeGenerationLogService:
    def __init__(self) -> None:
        self.entries = []

    async def record(self, entry) -> None:
        self.entries.append(entry)


def test_run_due_schedules_blocks_when_quota_exceeded(monkeypatch) -> None:
    user_id = uuid4()
    project_id = uuid4()
    schedule = DummySchedule(id=uuid4(), project_id=project_id)
    topic = DummyTopic(id=uuid4())

    scheduler_service = FakeSchedulerService(
        schedules=[schedule],
        owner_by_project={project_id: user_id},
        topic_by_project={project_id: topic},
    )
    limit_service = FakeLimitService(
        quota_by_user_id={
            user_id: ArticleQuotaStatus(
                allowed=False,
                plan_slug="free",
                used_articles=20,
                max_articles=20,
                remaining_articles=0,
                tokens_used=1000,
                period_start=datetime(2026, 3, 1, tzinfo=UTC),
                period_end=datetime(2026, 4, 1, tzinfo=UTC),
            )
        }
    )
    generation_logs = FakeGenerationLogService()
    article_delay_calls: list[dict] = []
    topic_delay_calls: list[dict] = []

    @asynccontextmanager
    async def fake_get_db():
        yield object()

    monkeypatch.setattr(scheduler_tasks, "get_db", fake_get_db)
    monkeypatch.setattr(scheduler_tasks, "SchedulerService", lambda _db: scheduler_service)
    monkeypatch.setattr(scheduler_tasks, "SubscriptionLimitService", lambda _db: limit_service)
    monkeypatch.setattr(scheduler_tasks, "GenerationLogService", lambda _db: generation_logs)
    monkeypatch.setattr(scheduler_tasks, "get_request_id", lambda: "req-1")
    monkeypatch.setattr(
        scheduler_tasks,
        "generate_article",
        SimpleNamespace(
            delay=lambda **kwargs: (
                article_delay_calls.append(kwargs) or SimpleNamespace(id="article-task")
            )
        ),
    )
    monkeypatch.setattr(
        scheduler_tasks,
        "generate_topics",
        SimpleNamespace(
            delay=lambda **kwargs: (topic_delay_calls.append(kwargs) or SimpleNamespace(id="topic-task"))
        ),
    )

    asyncio.run(scheduler_tasks._run_due_schedules_async())

    assert len(article_delay_calls) == 0
    assert len(topic_delay_calls) == 0
    assert len(generation_logs.entries) == 1
    assert generation_logs.entries[0].step == "subscription_limit_check"
    assert schedule.last_run_at is not None
    assert scheduler_service.reserve_calls == 0


def test_run_due_schedules_quota_cache_prevents_second_dispatch(monkeypatch) -> None:
    user_id = uuid4()
    project_a = uuid4()
    project_b = uuid4()
    schedule_a = DummySchedule(id=uuid4(), project_id=project_a)
    schedule_b = DummySchedule(id=uuid4(), project_id=project_b)
    topic_a = DummyTopic(id=uuid4())
    topic_b = DummyTopic(id=uuid4())

    scheduler_service = FakeSchedulerService(
        schedules=[schedule_a, schedule_b],
        owner_by_project={project_a: user_id, project_b: user_id},
        topic_by_project={project_a: topic_a, project_b: topic_b},
    )
    limit_service = FakeLimitService(
        quota_by_user_id={
            user_id: ArticleQuotaStatus(
                allowed=True,
                plan_slug="starter",
                used_articles=0,
                max_articles=1,
                remaining_articles=1,
                tokens_used=500,
                period_start=datetime(2026, 3, 1, tzinfo=UTC),
                period_end=datetime(2026, 4, 1, tzinfo=UTC),
            )
        }
    )
    generation_logs = FakeGenerationLogService()
    article_delay_calls: list[dict] = []

    @asynccontextmanager
    async def fake_get_db():
        yield object()

    monkeypatch.setattr(scheduler_tasks, "get_db", fake_get_db)
    monkeypatch.setattr(scheduler_tasks, "SchedulerService", lambda _db: scheduler_service)
    monkeypatch.setattr(scheduler_tasks, "SubscriptionLimitService", lambda _db: limit_service)
    monkeypatch.setattr(scheduler_tasks, "GenerationLogService", lambda _db: generation_logs)
    monkeypatch.setattr(scheduler_tasks, "get_request_id", lambda: "req-2")
    monkeypatch.setattr(
        scheduler_tasks,
        "generate_article",
        SimpleNamespace(
            delay=lambda **kwargs: (
                article_delay_calls.append(kwargs) or SimpleNamespace(id="article-task")
            )
        ),
    )
    monkeypatch.setattr(
        scheduler_tasks,
        "generate_topics",
        SimpleNamespace(delay=lambda **_kwargs: SimpleNamespace(id="topic-task")),
    )

    asyncio.run(scheduler_tasks._run_due_schedules_async())

    assert len(article_delay_calls) == 1
    assert article_delay_calls[0]["project_id"] == str(project_a)
    assert len(generation_logs.entries) == 1
    assert generation_logs.entries[0].project_id == project_b
    assert scheduler_service.reserve_calls == 1
    assert schedule_a.last_run_at is not None
    assert schedule_b.last_run_at is not None
