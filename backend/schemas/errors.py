"""Shared error-response envelope (Task A-4).

Mirrors the canonical ``ErrorResponse`` shape defined in
``/docs/CONTRACT.md``::

    {
      "error": {
        "code":       "VALIDATION_ERROR" | "AUTH_REQUIRED" | ...,
        "message":    "Request validation failed",
        "request_id": "uuid-string",
        "details":    [ { "field": "page", "message": ..., "type": ... } ]?
      }
    }

The Pydantic models here are used both by the global exception handlers
(see ``backend/error_handlers.py``) and by tests so that everyone agrees
on the field names.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """A single validation problem.

    ``field`` is dotted-path relative to the request body / query.
    ``type`` is the underlying pydantic error code (e.g.
    ``greater_than_equal``) so frontends can branch deterministically
    without parsing English messages.
    """

    field: str = Field(description="Dotted-path location of the failing field.")
    message: str = Field(description="Human-readable description of the problem.")
    type: str = Field(description="Underlying pydantic/error type identifier.")


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str
    details: Optional[List[ErrorDetail]] = None


class ErrorResponse(BaseModel):
    """Top-level error envelope returned by the global handlers."""

    error: ErrorBody


__all__ = ["ErrorDetail", "ErrorBody", "ErrorResponse"]
