"""Request context middleware (Task A-2).

Generates a per-request UUIDv4 ``request_id``, binds it into the
structlog ``contextvars`` context so every log line emitted while
handling the request carries the same correlation id, sets
``X-Request-ID`` on the response, and emits one JSON access-log line per
request at INFO level with method, path, status, ``duration_ms``,
``user_id``, and ``role``.

The middleware is implemented at the raw ASGI level so the
``X-Request-ID`` header is always set, even when downstream code raises
an unhandled exception (the framework's exception handlers still emit a
500 response, and we wrap ``send`` to inject the header on the response
start message).
"""

from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable, MutableMapping

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.logging_config import bind_request_id, get_logger, reset_request_id

# Header name used everywhere — exposed as a constant so tests and
# downstream services can reference it without re-typing the string.
REQUEST_ID_HEADER = "x-request-id"


def _coerce_user_context(scope: Scope) -> tuple[str | None, str | None]:
    """Best-effort lookup of the authenticated user for the access log.

    The middleware runs before FastAPI dependency injection resolves the
    bearer token, so we cannot call ``Depends(get_current_user)`` here.
    We instead check ``scope["state"]`` and a small set of conventional
    request headers (``X-User-Id``/``X-User-Role``) that the legacy
    header-trust auth uses, plus any value downstream auth code chose to
    stash on the scope state. When neither source has data, both fields
    are emitted as ``None`` which serializes to JSON ``null``.
    """
    state = scope.get("state")
    if isinstance(state, MutableMapping):
        user_id = state.get("user_id")
        role = state.get("user_role")
        if user_id or role:
            return user_id, role

    headers = {
        k.decode("latin-1").lower(): v.decode("latin-1")
        for k, v in scope.get("headers", [])
    }
    return headers.get("x-user-id"), headers.get("x-user-role")


class RequestContextMiddleware:
    """ASGI middleware that injects a request id and emits access logs."""

    def __init__(self, app: ASGIApp, *, logger_name: str = "backend.request") -> None:
        self.app = app
        self._logger = get_logger(logger_name)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        # Honour an upstream-provided X-Request-ID (e.g. from a load
        # balancer or smoke runbook) when the value looks well-formed,
        # otherwise mint a fresh uuid4. Validating relaxes to a length
        # cap so callers can use any opaque correlation id format.
        incoming = _extract_header(scope, REQUEST_ID_HEADER)
        request_id = incoming if (incoming and 8 <= len(incoming) <= 200) else uuid.uuid4().hex

        token = bind_request_id(request_id)
        start = time.perf_counter()
        status_code: int = 0

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message.get("status", 0))
                headers = list(message.get("headers", []))
                headers = [
                    (k, v) for k, v in headers if k.decode("latin-1").lower() != REQUEST_ID_HEADER
                ]
                headers.append((REQUEST_ID_HEADER.encode("latin-1"), request_id.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        method = scope.get("method", "")
        path = scope.get("path", "")
        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            self._logger.exception(
                "request.error",
                method=method,
                path=path,
                status=500,
                duration_ms=duration_ms,
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            user_id, role = _coerce_user_context(scope)
            self._logger.info(
                "request",
                method=method,
                path=path,
                status=status_code or 0,
                duration_ms=duration_ms,
                user_id=user_id,
                role=role,
            )
        finally:
            reset_request_id(token)


def _extract_header(scope: Scope, name: str) -> str | None:
    target = name.lower().encode("latin-1")
    for key, value in scope.get("headers", []):
        if key.lower() == target:
            try:
                return value.decode("latin-1")
            except Exception:  # pragma: no cover - defensive
                return None
    return None


__all__ = ["RequestContextMiddleware", "REQUEST_ID_HEADER"]
