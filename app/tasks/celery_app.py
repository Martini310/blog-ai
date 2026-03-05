"""
Celery application factory.

Celery is configured with Redis as both broker and result backend.
Sentry is initialised here so it captures task exceptions automatically.
"""
import sentry_sdk
from celery import Celery
from celery.signals import worker_init
from sentry_sdk.integrations.celery import CeleryIntegration

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Create the Celery app
# ---------------------------------------------------------------------------
celery_app = Celery(
    "blog_ai",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.content_tasks",
        "app.tasks.scheduler_tasks",
    ],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Worker
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,

    # Results
    result_expires=86400,  # 24h
    result_backend_transport_options={"visibility_timeout": 3600},

    # Task routing (add more queues as the system scales)
    task_default_queue="default",
    task_queues={
        "default": {},
        "generation": {},    # LLM generation tasks
        "scheduler": {},     # Beat-triggered tasks
    },

    # Retry defaults (tasks override per-task via autoretry_for)
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# ---------------------------------------------------------------------------
# Beat schedule (periodic tasks)
# See scheduler_tasks.py for the actual task implementations.
# ---------------------------------------------------------------------------
celery_app.conf.beat_schedule = {
    "run-due-content-schedules": {
        "task": "app.tasks.scheduler_tasks.run_due_content_schedules",
        "schedule": 60.0,    # every 60 seconds
        "options": {"queue": "scheduler"},
    },
    "cleanup-stale-generation-logs": {
        "task": "app.tasks.scheduler_tasks.cleanup_stale_logs",
        "schedule": 3600.0,  # every hour
        "options": {"queue": "scheduler"},
    },
}


# ---------------------------------------------------------------------------
# Worker startup: configure logging + Sentry inside the worker process
# ---------------------------------------------------------------------------
@worker_init.connect
def on_worker_init(**_kwargs) -> None:
    configure_logging()

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[CeleryIntegration()],
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            environment=settings.ENVIRONMENT,
        )

    logger.info("celery_worker_started", environment=settings.ENVIRONMENT)
