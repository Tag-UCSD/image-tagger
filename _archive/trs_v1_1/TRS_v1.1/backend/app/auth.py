"""
TRS-203: API Key Authentication for TRS.

Provides FastAPI dependencies for role-based access control.

Roles (hierarchical):
    - admin: Full access, can manage keys, release, approve
    - reviewer: Can approve/reject proposals
    - proposer: Can submit proposals
    - viewer: Read-only access

Usage:
    from backend.app.auth import require_auth, require_role
    
    @router.get("/protected")
    async def protected_route(user: APIKey = Depends(require_auth)):
        return {"user": user.name}
    
    @router.post("/admin-only")
    async def admin_only(user: APIKey = Depends(require_role("admin"))):
        return {"admin": user.name}
"""

from __future__ import annotations
from functools import lru_cache
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import APIKeyHeader

from .db import get_db, APIKey


# Role hierarchy: higher roles include permissions of lower roles
ROLE_HIERARCHY = {
    "admin": {"admin", "reviewer", "proposer", "viewer"},
    "reviewer": {"reviewer", "proposer", "viewer"},
    "proposer": {"proposer", "viewer"},
    "viewer": {"viewer"},
}

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[APIKey]:
    """
    Extract and validate API key from request.
    Returns None if no key provided or invalid.
    """
    if not api_key:
        return None
    
    db = get_db()
    key_info = db.validate_api_key(api_key)
    
    if key_info:
        # Log the access
        db.log_action(
            action="api_access",
            user_id=key_info.name,
            details={"endpoint": str(request.url.path), "method": request.method},
            ip_address=request.client.host if request.client else None,
        )
    
    return key_info


async def require_auth(
    api_key: Optional[APIKey] = Depends(get_api_key),
) -> APIKey:
    """
    Require valid API key authentication.
    Raises 401 if no valid key provided.
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


def require_role(required_role: str):
    """
    Factory for role-based access control dependencies.
    
    Usage:
        @router.post("/proposals")
        async def create_proposal(user = Depends(require_role("proposer"))):
            ...
    """
    async def checker(api_key: APIKey = Depends(require_auth)) -> APIKey:
        # Check if user's role includes the required role
        user_roles = ROLE_HIERARCHY.get(api_key.role, set())
        
        if required_role not in user_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Requires '{required_role}' role, you have '{api_key.role}'.",
            )
        
        return api_key
    
    return checker


async def optional_auth(
    api_key: Optional[APIKey] = Depends(get_api_key),
) -> Optional[APIKey]:
    """
    Optional authentication - returns None if no valid key.
    Useful for endpoints that behave differently for authenticated users.
    """
    return api_key


def check_role(api_key: APIKey, required_role: str) -> bool:
    """Utility function to check if a key has a required role."""
    user_roles = ROLE_HIERARCHY.get(api_key.role, set())
    return required_role in user_roles


# ============================================================================
# CLI Key Management
# ============================================================================

def create_key_cli(name: str, role: str, created_by: str = "cli") -> tuple[int, str]:
    """
    Create an API key from CLI.
    Returns (key_id, raw_key).
    """
    if role not in ROLE_HIERARCHY:
        raise ValueError(f"Invalid role: {role}. Must be one of: {list(ROLE_HIERARCHY.keys())}")
    
    db = get_db()
    key_id, raw_key = db.create_api_key(name=name, role=role, created_by=created_by)
    
    db.log_action(
        action="api_key_created",
        user_id=created_by,
        target_type="api_key",
        target_id=str(key_id),
        details={"name": name, "role": role},
    )
    
    return key_id, raw_key


def list_keys_cli() -> list[APIKey]:
    """List all active API keys."""
    db = get_db()
    return db.list_api_keys(include_revoked=False)


def revoke_key_cli(key_id: int, revoked_by: str = "cli") -> bool:
    """Revoke an API key. Returns True if revoked."""
    db = get_db()
    success = db.revoke_api_key(key_id)
    
    if success:
        db.log_action(
            action="api_key_revoked",
            user_id=revoked_by,
            target_type="api_key",
            target_id=str(key_id),
        )
    
    return success
