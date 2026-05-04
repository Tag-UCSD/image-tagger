"""Global FastAPI exception handlers (Task A-4).

Every error response returned by the backend is shaped to the contract
envelope ``{ error: { code, message, request_id, details? } }`` (see
``/docs/CONTRACT.md``). Handlers cover three sources of failure:

1. ``RequestValidationError`` — Pydantic-level validation of the
   query string, path parameters, request body, headers, or multipart
   form. Always emitted with ``code="VALIDATION_ERROR"`` and the
   canonical ``message="Request validation failed"`` regardless of the
   underlying field, with per-field ``details``.
2. Starlette ``HTTPException`` — application-level errors raised by
   route or dependency code (e.g. 401 from auth, 404 from a missing
   resource). Mapped to the contract's ``code`` taxonomy.
3. Any other ``Exception`` — unexpected failure. Logged at ERROR with a
   stack trace and returned as a 500 ``INTERNAL_ERROR``. The
   underlying exception message is never echoed to the client to avoid
   leaking implementation details.

The handlers read the current request id from the ``contextvars``
context bound by ``backend/middleware/request_context.py`` (Task A-2),
so the same id appears in the response body, the ``X-Request-ID``
response header, and every structured log line emitted while the
request was in flight.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.logging_config import get_logger, request_id_var

logger = get_logger("backend.errors")


# Mapping from HTTP status code to the contract error-code taxonomy
# documented in /docs/CONTRACT.md ("Error code guidance").
_STATUS_TO_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "AUTH_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


def _current_request_id() -> str:
    """Return the request id bound by the middleware, or mint a fallback.

    A fallback is needed because FastAPI's startup-time validation can
    produce errors before any middleware has run (rare, but possible
    with malformed requests during boot).
    """
    rid = request_id_var.get()
    if rid:
        return rid
    return uuid.uuid4().hex


def _envelope(
    *,
    code: str,
    message: str,
    status_code: int,
    details: Iterable[dict[str, Any]] | None = None,
) -> JSONResponse:
    request_id = _current_request_id()
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details is not None:
        body["error"]["details"] = list(details)

    headers = {"X-Request-ID": request_id}
    return JSONResponse(
        content=jsonable_encoder(body),
        status_code=status_code,
        headers=headers,
    )


def _strip_loc_section(loc: tuple[Any, ...]) -> tuple[Any, ...]:
    """Drop the leading section name (``query``/``body``/...) from ``loc``.

    Pydantic's ``loc`` always starts with the request section. The
    contract's ``field`` value is the dotted path relative to that
    section, so e.g. ``("query", "page")`` becomes ``"page"`` and
    ``("body", "image_ids", 0)`` becomes ``"image_ids.0"``.
    """
    if not loc:
        return loc
    head = loc[0]
    if isinstance(head, str) and head in {
        "query",
        "body",
        "path",
        "header",
        "cookie",
        "form",
        "file",
    }:
        return loc[1:]
    return loc


def _format_details(errors: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    formatted: list[dict[str, Any]] = []
    for err in errors:
        loc = _strip_loc_section(tuple(err.get("loc", ())))
        field = ".".join(str(part) for part in loc) if loc else "<root>"
        formatted.append(
            {
                "field": field,
                "message": str(err.get("msg", "")),
                "type": str(err.get("type", "")),
            }
        )
    return formatted


# --------------------------------------------------------------------------
# Individual handlers
# --------------------------------------------------------------------------
async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic-level request validation failures (422).

    All such failures share ``code="VALIDATION_ERROR"`` and the
    canonical message regardless of which input section failed, per
    Task A-4.
    """
    details = _format_details(exc.errors())
    logger.info(
        "request.validation_error",
        method=request.method,
        path=request.url.path,
        error_count=len(details),
    )
    return _envelope(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
    )


async def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Reshape ``HTTPException``-style errors into the contract envelope."""
    code = _STATUS_TO_CODE.get(exc.status_code, "ERROR")
    # Some upstream code raises HTTPException with a structured detail
    # (dict / list); fall back to a stable default message in that case
    # because the contract's ``message`` is a string.
    if isinstance(exc.detail, str) and exc.detail:
        message = exc.detail
    else:
        message = _default_message_for_status(exc.status_code)

    logger.info(
        "request.http_error",
        method=request.method,
        path=request.url.path,
        status=exc.status_code,
        code=code,
    )
    return _envelope(
        code=code,
        message=message,
        status_code=exc.status_code,
    )


def _default_message_for_status(status_code: int) -> str:
    return {
        400: "Bad request",
        401: "Bearer token required or invalid",
        403: "Insufficient role for this resource",
        404: "Resource not found",
        405: "Method not allowed",
        409: "Conflict",
        413: "Payload too large",
        415: "Unsupported media type",
        422: "Request validation failed",
        429: "Rate limit exceeded",
    }.get(status_code, "Request failed")


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for runtime failures (500 INTERNAL_ERROR).

    The exception type and stack trace are logged at ERROR. The client
    response carries the request id but never the underlying message,
    to avoid leaking server-side detail.
    """
    logger.error(
        "request.unhandled_exception",
        method=request.method,
        path=request.url.path,
        exc_type=type(exc).__name__,
        exc_info=exc,
    )
    return _envelope(
        code="INTERNAL_ERROR",
        message="Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the contract-shaped handlers to a FastAPI app."""
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


__all__ = ["register_exception_handlers"]
