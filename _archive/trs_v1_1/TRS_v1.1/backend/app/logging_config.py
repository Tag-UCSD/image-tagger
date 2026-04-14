"""
TRS-801: Structured JSON logging.

Provides consistent, machine-parseable logging for all TRS components.

Usage:
    from backend.app.logging_config import get_logger, setup_logging
    
    setup_logging(level="INFO", json_format=True)
    logger = get_logger(__name__)
    
    logger.info("Processing request", extra={"tag_id": "env.test", "user": "alice"})
"""

from __future__ import annotations
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Optional
import uuid


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Output format:
    {
        "timestamp": "2024-12-21T12:00:00.000Z",
        "level": "INFO",
        "logger": "backend.app.routes",
        "message": "Request processed",
        "request_id": "abc123",
        "duration_ms": 45,
        ...extra fields
    }
    """
    
    def __init__(self, include_traceback: bool = True):
        super().__init__()
        self.include_traceback = include_traceback
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add location info for errors
        if record.levelno >= logging.WARNING:
            log_entry["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        # Add exception info
        if record.exc_info and self.include_traceback:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        # Add extra fields
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "asctime",
            }
        }
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """
    Colored console formatter for development.
    """
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format timestamp
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Build message
        msg = f"{color}{timestamp} [{record.levelname:7}]{self.RESET} {record.name}: {record.getMessage()}"
        
        # Add extra fields inline
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "asctime",
            }
        }
        
        if extra_fields:
            extras = " ".join(f"{k}={v}" for k, v in extra_fields.items())
            msg += f" | {extras}"
        
        # Add exception
        if record.exc_info:
            msg += "\n" + "".join(traceback.format_exception(*record.exc_info))
        
        return msg


class RequestContextFilter(logging.Filter):
    """
    Filter that adds request context to log records.
    """
    
    _context: dict = {}
    
    @classmethod
    def set_context(cls, **kwargs):
        """Set context for current request."""
        cls._context = kwargs
    
    @classmethod
    def clear_context(cls):
        """Clear request context."""
        cls._context = {}
    
    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """Get current request ID."""
        return cls._context.get("request_id")
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add context to record
        for key, value in self._context.items():
            setattr(record, key, value)
        return True


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format (for production)
        log_file: Optional file to write logs to
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Add context filter
    context_filter = RequestContextFilter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.addFilter(context_filter)
    
    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.addFilter(context_filter)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    return logging.getLogger(name)


# ============================================================================
# Convenience functions
# ============================================================================

def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **extra,
) -> None:
    """Log an HTTP request."""
    logger = get_logger("trs.request")
    
    level = logging.INFO
    if status_code >= 500:
        level = logging.ERROR
    elif status_code >= 400:
        level = logging.WARNING
    
    logger.log(
        level,
        f"{method} {path} {status_code}",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            **extra,
        },
    )


def log_event(
    event: str,
    **data,
) -> None:
    """Log an application event."""
    logger = get_logger("trs.event")
    logger.info(event, extra={"event": event, **data})


def log_error(
    message: str,
    exception: Optional[Exception] = None,
    **extra,
) -> None:
    """Log an error."""
    logger = get_logger("trs.error")
    logger.error(message, exc_info=exception, extra=extra)
