"""Backend ASGI/HTTP middleware (Task A-2)."""

from backend.middleware.request_context import RequestContextMiddleware

__all__ = ["RequestContextMiddleware"]
