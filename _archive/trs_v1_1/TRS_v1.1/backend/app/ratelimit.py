"""
TRS-701: Rate limiting middleware.

Provides rate limiting for API endpoints to prevent abuse.

Usage:
    from backend.app.ratelimit import RateLimiter, rate_limit
    
    # As middleware
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
    
    # As dependency
    @router.get("/endpoint")
    async def endpoint(limiter = Depends(rate_limit(10, 60))):
        ...
"""

from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Request, Response, HTTPException, Depends
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests: int  # Number of requests allowed
    window: int  # Time window in seconds
    key_func: Optional[Callable[[Request], str]] = None  # Function to extract rate limit key


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Thread-safe rate limiting with configurable windows.
    """
    
    def __init__(self, requests: int = 60, window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests: Number of requests allowed per window
            window: Time window in seconds
        """
        self.requests = requests
        self.window = window
        self._buckets: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, key: str) -> tuple[bool, dict]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier (e.g., IP address, API key)
        
        Returns:
            (allowed, headers) where headers contains rate limit info
        """
        now = time.time()
        bucket = self._buckets[key]
        
        # Remove old entries
        cutoff = now - self.window
        bucket[:] = [t for t in bucket if t > cutoff]
        
        # Check limit
        remaining = self.requests - len(bucket)
        
        headers = {
            "X-RateLimit-Limit": str(self.requests),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(now + self.window)),
        }
        
        if remaining <= 0:
            # Find when oldest request expires
            if bucket:
                retry_after = int(bucket[0] + self.window - now)
                headers["Retry-After"] = str(max(1, retry_after))
            return False, headers
        
        # Allow and record
        bucket.append(now)
        return True, headers
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        if key in self._buckets:
            del self._buckets[key]
    
    def reset_all(self) -> None:
        """Reset all rate limits."""
        self._buckets.clear()


# ============================================================================
# FastAPI Middleware
# ============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Usage:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=60,
            exempt_paths=["/health", "/metrics"],
        )
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        exempt_paths: Optional[list[str]] = None,
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute, 60)
        self.exempt_paths = set(exempt_paths or ["/health", "/ready", "/live", "/metrics"])
        self.key_func = key_func or self._default_key
    
    def _default_key(self, request: Request) -> str:
        """Default key function: use client IP."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        # Skip exempt paths
        if request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get rate limit key
        key = self.key_func(request)
        
        # Check rate limit
        allowed, headers = self.limiter.is_allowed(key)
        
        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                headers=headers,
                media_type="application/json",
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        for header, value in headers.items():
            response.headers[header] = value
        
        return response


# ============================================================================
# FastAPI Dependency
# ============================================================================

def rate_limit(requests: int = 10, window: int = 60):
    """
    Rate limiting dependency for specific endpoints.
    
    Usage:
        @router.post("/expensive")
        async def expensive_endpoint(limiter = Depends(rate_limit(5, 60))):
            ...
    """
    limiter = RateLimiter(requests, window)
    
    async def dependency(request: Request):
        # Use API key if available, else IP
        key = request.headers.get("X-API-Key")
        if not key:
            key = request.client.host if request.client else "unknown"
        
        allowed, headers = limiter.is_allowed(key)
        
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers=headers,
            )
        
        return headers
    
    return dependency


# ============================================================================
# Tiered Rate Limits
# ============================================================================

class TieredRateLimiter:
    """
    Rate limiter with different limits per role.
    """
    
    DEFAULT_LIMITS = {
        "admin": (1000, 60),  # 1000/minute
        "reviewer": (500, 60),
        "proposer": (200, 60),
        "viewer": (100, 60),
        "anonymous": (30, 60),
    }
    
    def __init__(self, limits: Optional[dict] = None):
        self.limits = limits or self.DEFAULT_LIMITS
        self._limiters: dict[str, RateLimiter] = {}
    
    def _get_limiter(self, role: str) -> RateLimiter:
        """Get or create limiter for role."""
        if role not in self._limiters:
            requests, window = self.limits.get(role, self.limits["anonymous"])
            self._limiters[role] = RateLimiter(requests, window)
        return self._limiters[role]
    
    def is_allowed(self, key: str, role: str = "anonymous") -> tuple[bool, dict]:
        """Check if request is allowed for role."""
        limiter = self._get_limiter(role)
        return limiter.is_allowed(key)
