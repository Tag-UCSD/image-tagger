"""
TRS-803 & TRS-804: Error tracking and request tracing middleware.

Provides:
- Automatic error tracking and logging
- Request correlation IDs for distributed tracing
- Request/response logging

Usage:
    from backend.app.middleware import (
        ErrorTrackingMiddleware,
        RequestTracingMiddleware,
        setup_middleware,
    )
    
    setup_middleware(app)
"""

from __future__ import annotations
import time
import traceback
import uuid
from typing import Callable, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_config import (
    get_logger,
    log_request,
    log_error,
    RequestContextFilter,
)
from .metrics import metrics


logger = get_logger(__name__)


# ============================================================================
# Request Tracing Middleware
# ============================================================================

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Adds correlation IDs to requests for distributed tracing.
    
    - Generates unique request ID if not provided
    - Adds request ID to response headers
    - Sets up logging context
    """
    
    REQUEST_ID_HEADER = "X-Request-ID"
    CORRELATION_ID_HEADER = "X-Correlation-ID"
    
    async def dispatch(self, request: Request, call_next):
        # Get or generate request ID
        request_id = request.headers.get(self.REQUEST_ID_HEADER)
        if not request_id:
            request_id = str(uuid.uuid4())[:8]
        
        # Get correlation ID (for tracing across services)
        correlation_id = request.headers.get(self.CORRELATION_ID_HEADER, request_id)
        
        # Set logging context
        RequestContextFilter.set_context(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=self._get_client_ip(request),
        )
        
        # Store in request state for handlers
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        
        # Track timing
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Add trace headers to response
            response.headers[self.REQUEST_ID_HEADER] = request_id
            response.headers[self.CORRELATION_ID_HEADER] = correlation_id
            
            # Log request
            duration_ms = (time.time() - start_time) * 1000
            log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_id=request_id,
            )
            
            return response
            
        finally:
            RequestContextFilter.clear_context()
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


# ============================================================================
# Error Tracking Middleware
# ============================================================================

class ErrorTrackingMiddleware(BaseHTTPMiddleware):
    """
    Catches and logs unhandled exceptions.
    
    - Logs full stack traces
    - Records error metrics
    - Returns consistent error responses
    """
    
    def __init__(
        self,
        app,
        include_traceback: bool = False,
        notify_on_error: Optional[Callable] = None,
    ):
        super().__init__(app)
        self.include_traceback = include_traceback
        self.notify_on_error = notify_on_error
    
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
            
        except Exception as exc:
            # Get request ID if available
            request_id = getattr(request.state, "request_id", None)
            
            # Log the error
            log_error(
                f"Unhandled exception: {exc}",
                exception=exc,
                request_id=request_id,
                path=request.url.path,
                method=request.method,
            )
            
            # Record metric
            error_type = type(exc).__name__
            metrics.record_error(error_type)
            
            # Notify if configured
            if self.notify_on_error:
                try:
                    await self.notify_on_error(exc, request)
                except Exception:
                    logger.exception("Error in notification handler")
            
            # Build error response
            error_body = {
                "detail": "Internal server error",
                "request_id": request_id,
            }
            
            if self.include_traceback:
                error_body["traceback"] = traceback.format_exc()
            
            import json
            return Response(
                content=json.dumps(error_body),
                status_code=500,
                media_type="application/json",
            )


# ============================================================================
# Metrics Middleware
# ============================================================================

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Records request metrics.
    """
    
    SKIP_PATHS = {"/health", "/ready", "/live", "/metrics"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoints
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        start_time = time.time()
        metrics.active_requests.inc()
        
        try:
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration,
            )
            
            return response
            
        finally:
            metrics.active_requests.dec()


# ============================================================================
# Request Logging Middleware
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs request and response details.
    """
    
    def __init__(
        self,
        app,
        log_body: bool = False,
        max_body_size: int = 1000,
    ):
        super().__init__(app)
        self.log_body = log_body
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next):
        # Log request
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "user_agent": request.headers.get("User-Agent", ""),
        }
        
        # Optionally log body
        if self.log_body and request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    request_info["body"] = body.decode("utf-8", errors="replace")
                else:
                    request_info["body_size"] = len(body)
            except Exception:
                pass
        
        logger.debug("Request received", extra=request_info)
        
        # Process request
        response = await call_next(request)
        
        # Log response
        logger.debug(
            "Response sent",
            extra={
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type"),
            },
        )
        
        return response


# ============================================================================
# Slow Request Middleware
# ============================================================================

class SlowRequestMiddleware(BaseHTTPMiddleware):
    """
    Logs warnings for slow requests.
    """
    
    def __init__(self, app, threshold_seconds: float = 1.0):
        super().__init__(app)
        self.threshold = threshold_seconds
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        if duration >= self.threshold:
            logger.warning(
                f"Slow request: {request.method} {request.url.path}",
                extra={
                    "duration_seconds": round(duration, 3),
                    "threshold_seconds": self.threshold,
                    "status_code": response.status_code,
                },
            )
        
        return response


# ============================================================================
# Setup Helper
# ============================================================================

def setup_middleware(
    app: FastAPI,
    enable_tracing: bool = True,
    enable_error_tracking: bool = True,
    enable_metrics: bool = True,
    enable_slow_request_logging: bool = True,
    slow_request_threshold: float = 1.0,
    include_traceback_in_errors: bool = False,
) -> None:
    """
    Configure all middleware for the application.
    
    Order matters! Middleware is executed in reverse order.
    """
    # Slow request logging (innermost)
    if enable_slow_request_logging:
        app.add_middleware(
            SlowRequestMiddleware,
            threshold_seconds=slow_request_threshold,
        )
    
    # Metrics
    if enable_metrics:
        app.add_middleware(MetricsMiddleware)
    
    # Error tracking
    if enable_error_tracking:
        app.add_middleware(
            ErrorTrackingMiddleware,
            include_traceback=include_traceback_in_errors,
        )
    
    # Request tracing (outermost)
    if enable_tracing:
        app.add_middleware(RequestTracingMiddleware)
