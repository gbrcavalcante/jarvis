"""Structured JSON audit logger.

Every action taken by the pipeline is recorded here.
Log level, format, and destination are runtime-configurable.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog


def configure_logging(
    level: str = "INFO",
    fmt: str = "json",
    file: str = "",
) -> None:
    """Configure structlog. Call once at application startup."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if file:
        log_path = Path(file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5,
        ))

    logging.basicConfig(level=log_level, handlers=handlers, format="%(message)s")

    renderer = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a bound logger for the given component name."""
    return structlog.get_logger(component=name)


import logging.handlers  # noqa: E402 — placed after configure_logging definition
