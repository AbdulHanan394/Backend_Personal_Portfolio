"""Structured logging configuration helpers."""

import logging
import sys

import structlog


def configure_logging(json_logs: bool = False) -> None:
    """Configure standard and structlog logging."""

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    structlog.configure(
        processors=[*processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger."""

    return structlog.get_logger(name)

