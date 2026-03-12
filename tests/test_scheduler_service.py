from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.services.scheduler_service import (
    SchedulerService,
    TOPIC_GENERATION_MARKER_KEY,
)


def test_should_request_topic_generation_when_marker_missing() -> None:
    schedule = SimpleNamespace(config={})
    assert SchedulerService.should_request_topic_generation(
        schedule,
        datetime.now(UTC),
    )


def test_should_request_topic_generation_respects_cooldown() -> None:
    now = datetime.now(UTC)
    schedule = SimpleNamespace(
        config={TOPIC_GENERATION_MARKER_KEY: (now - timedelta(minutes=10)).isoformat()}
    )
    assert SchedulerService.should_request_topic_generation(schedule, now) is False


def test_should_request_topic_generation_after_cooldown() -> None:
    now = datetime.now(UTC)
    schedule = SimpleNamespace(
        config={TOPIC_GENERATION_MARKER_KEY: (now - timedelta(hours=7)).isoformat()}
    )
    assert SchedulerService.should_request_topic_generation(schedule, now) is True


def test_mark_and_clear_topic_generation_marker() -> None:
    now = datetime.now(UTC)
    schedule = SimpleNamespace(config={})
    SchedulerService.mark_topic_generation_requested(schedule, now)
    assert TOPIC_GENERATION_MARKER_KEY in schedule.config

    SchedulerService.clear_topic_generation_marker(schedule)
    assert TOPIC_GENERATION_MARKER_KEY not in schedule.config
