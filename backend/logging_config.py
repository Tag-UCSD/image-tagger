"""Structured JSON logging configuration (Task A-2).

Configures ``structlog`` to emit JSON log lines to stdout. The
``request_id`` carried through ``contextvars`` (see
``backend/middleware/request_context.py``) is automatically merged into
every log record via ``structlog.contextvars.merge_contextvars`` so all
logs emitted within a request share the same correlation id.

Call :func:`configure_logging` once at process startup. Importing the
module also installs a one-time idempotent guard so repeated imports do
not stack processors.
"""

from __future__ import annotations

import contextvars
import logging
import sys
from typing import Optional

import structlog

# Context variable holding the current request id. The middleware sets
# this at the start of each request; ``structlog.contextvars`` reads it
# automatically when ``merge_contextvars`` is in the processor chain.
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure stdlib logging + structlog to emit JSON to stdout.

    Idempotent: subsequent calls with the same level are no-ops. The
    level is parsed via :func:`logging.getLevelName` so callers can pass
    either a string ("INFO") or an int.
    """
    global _CONFIGURED

    numeric_level = (
        logging.getLevelName(level.upper()) if isinstance(level, str) else int(level)
    )
    if not isinstance(numeric_level, int):  # pragma: no cover - defensive
        numeric_level = logging.INFO

    root_logger = logging.getLogger()
    if not _CONFIGURED:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)

    root_logger.setLevel(numeric_level)
    for noisy in ("uvicorn.access", "uvicorn.error", "uvicorn"):
        logging.getLogger(noisy).setLevel(max(numeric_level, logging.INFO))

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger.

    Importing modules can call this at module load time; the returned
    logger picks up the global configuration even if
    :func:`configure_logging` runs later (``cache_logger_on_first_use``
    is keyed on the first ``info``/``warning`` call).
    """
    return structlog.get_logger(name)


def bind_request_id(request_id: str) -> contextvars.Token:
    """Bind ``request_id`` into the structlog context for the current task.

    Returns the :class:`contextvars.Token` so callers can reset the
    binding when the request completes. Mirrors the value into
    :data:`request_id_var` for non-structlog code paths that want to read
    the current request id directly (e.g. error handlers).
    """
    structlog.contextvars.bind_contextvars(request_id=request_id)
    return request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    """Undo a previous :func:`bind_request_id` binding."""
    structlog.contextvars.unbind_contextvars("request_id")
    try:
        request_id_var.reset(token)
    except (LookupError, ValueError):  # pragma: no cover - defensive
        pass


__all__ = [
    "configure_logging",
    "get_logger",
    "bind_request_id",
    "reset_request_id",
    "request_id_var",
]
