"""
TRS-702 & TRS-703: Security middleware.

Provides:
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Input sanitization for common injection attacks

Usage:
    from backend.app.security import SecurityHeadersMiddleware, sanitize_input
    
    app.add_middleware(SecurityHeadersMiddleware)
"""

from __future__ import annotations
import html
import re
from typing import Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# Security Headers Middleware
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Content-Security-Policy: default-src 'self'
    - Strict-Transport-Security: max-age=31536000
    - Referrer-Policy: strict-origin-when-cross-origin
    """
    
    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,
        frame_options: str = "DENY",
        content_security_policy: Optional[str] = None,
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.frame_options = frame_options
        self.csp = content_security_policy or "default-src 'self'"
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = self.frame_options
        
        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS (only on HTTPS)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains"
            )
        
        # Prevent caching of sensitive responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        
        return response


# ============================================================================
# Input Sanitization
# ============================================================================

# Dangerous patterns
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b)",
    r"(--.*)$",
    r"(/\*.*\*/)",
    r"(;.*--)",
]

XSS_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",
    r"<iframe.*?>",
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",
    r"\.\.\\",
    r"%2e%2e%2f",
    r"%2e%2e/",
]


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize a string input.
    
    - Truncates to max_length
    - Escapes HTML entities
    - Strips null bytes
    """
    if not isinstance(value, str):
        return str(value)[:max_length]
    
    # Truncate
    value = value[:max_length]
    
    # Remove null bytes
    value = value.replace("\x00", "")
    
    # Escape HTML
    value = html.escape(value)
    
    return value


def check_sql_injection(value: str) -> bool:
    """Check if value contains SQL injection patterns."""
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False


def check_xss(value: str) -> bool:
    """Check if value contains XSS patterns."""
    for pattern in XSS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False


def check_path_traversal(value: str) -> bool:
    """Check if value contains path traversal patterns."""
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False


def sanitize_input(
    value: Any,
    max_length: int = 10000,
    check_injection: bool = True,
) -> tuple[Any, list[str]]:
    """
    Sanitize input value and check for injection attempts.
    
    Returns:
        (sanitized_value, warnings)
    """
    warnings = []
    
    if value is None:
        return None, warnings
    
    if isinstance(value, str):
        if check_injection:
            if check_sql_injection(value):
                warnings.append("Potential SQL injection detected")
            if check_xss(value):
                warnings.append("Potential XSS detected")
            if check_path_traversal(value):
                warnings.append("Potential path traversal detected")
        
        return sanitize_string(value, max_length), warnings
    
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            sanitized_key, key_warnings = sanitize_input(k, max_length, check_injection)
            sanitized_val, val_warnings = sanitize_input(v, max_length, check_injection)
            result[sanitized_key] = sanitized_val
            warnings.extend(key_warnings + val_warnings)
        return result, warnings
    
    if isinstance(value, list):
        result = []
        for item in value:
            sanitized, item_warnings = sanitize_input(item, max_length, check_injection)
            result.append(sanitized)
            warnings.extend(item_warnings)
        return result, warnings
    
    return value, warnings


def validate_tag_id(tag_id: str) -> tuple[bool, Optional[str]]:
    """
    Validate a tag ID format.
    
    Returns:
        (is_valid, error_message)
    """
    if not tag_id:
        return False, "Tag ID cannot be empty"
    
    if len(tag_id) > 200:
        return False, "Tag ID too long (max 200 characters)"
    
    # Check for dangerous characters
    if check_path_traversal(tag_id):
        return False, "Invalid characters in tag ID"
    
    # Check format
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z0-9_/()+-]+){1,5}$', tag_id):
        return False, "Invalid tag ID format"
    
    return True, None


def validate_version(version: str) -> tuple[bool, Optional[str]]:
    """
    Validate a version string.
    
    Returns:
        (is_valid, error_message)
    """
    if not version:
        return False, "Version cannot be empty"
    
    if not re.match(r'^v[0-9]+\.[0-9]+\.[0-9]+$', version):
        return False, "Invalid version format (expected vX.Y.Z)"
    
    return True, None


# ============================================================================
# Request Sanitization Middleware
# ============================================================================

class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to detect potentially malicious input.
    
    Note: This logs warnings but doesn't block requests.
    Blocking would require more sophisticated analysis.
    """
    
    def __init__(self, app, log_warnings: bool = True):
        super().__init__(app)
        self.log_warnings = log_warnings
    
    async def dispatch(self, request: Request, call_next):
        # Check query parameters
        for key, value in request.query_params.items():
            _, warnings = sanitize_input(value)
            if warnings and self.log_warnings:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Suspicious input in query param '{key}': {warnings}"
                )
        
        return await call_next(request)
