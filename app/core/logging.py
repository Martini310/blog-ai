"""
Structured JSON logging configuration.

All log records are emitted as JSON objects containing at minimum:
  timestamp, level, logger, message

Optional contextual fields are injected via contextvars:
  request_id, project_id, topic_id, task_name, step, duration_ms, tokens_used

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("article generated", extra={"tokens_used": 1234, "step": "llm_call"})
"""
import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

from app.core.config import settings

# ---------------------------------------------------------------------------
# Context variables – set per-request or per-task, read by the processor.
# ---------------------------------------------------------------------------
_request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_project_id_var: ContextVar[str] = ContextVar("project_id", default="")
_topic_id_var: ContextVar[str] = ContextVar("topic_id", default="")
_task_name_var: ContextVar[str] = ContextVar("task_name", default="")


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def set_project_id(project_id: str) -> None:
    _project_id_var.set(project_id)


def set_topic_id(topic_id: str) -> None:
    _topic_id_var.set(topic_id)


def set_task_name(task_name: str) -> None:
    _task_name_var.set(task_name)


def get_request_id() -> str:
    return _request_id_var.get()


# ---------------------------------------------------------------------------
# Custom structlog processor – injects context vars into every log event.
# ---------------------------------------------------------------------------
def _inject_context_vars(
    logger: Any,  # noqa: ARG001
    method: str,  # noqa: ARG001
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    if request_id := _request_id_var.get():
        event_dict["request_id"] = request_id
    if project_id := _project_id_var.get():
        event_dict["project_id"] = project_id
    if topic_id := _topic_id_var.get():
        event_dict["topic_id"] = topic_id
    if task_name := _task_name_var.get():
        event_dict["task_name"] = task_name
    return event_dict


# ---------------------------------------------------------------------------
# Configure structlog + stdlib logging bridge
# ---------------------------------------------------------------------------
def configure_logging() -> None:
    """
    Call once at application startup (in main.py lifespan).

    Structlog wraps stdlib logging so that third-party libraries that use
    stdlib logging also emit structured JSON.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _inject_context_vars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.LOG_JSON:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)  # type: ignore[assignment]

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    # Quiet noisy libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to *name*."""
    return structlog.get_logger(name)
