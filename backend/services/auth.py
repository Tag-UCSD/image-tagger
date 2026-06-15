"""Authentication and authorization (Task A-3).

Replaces the legacy header-trust scheme with bearer-JWT validation
against a Supabase Auth-issued token. Implementation contract (see
``/docs/CONTRACT.md`` and ``/docs/workplan/PLAN_BACKEND_PHASE1.md`` task
A-3):

- Tokens are HS256-signed with ``SUPABASE_JWT_SECRET``.
- Identity comes from JWT claims only: ``sub`` is user id, top-level
  ``role`` is the authorization role.
- Roles ∈ ``{"tagger", "scientist", "supervisor", "admin"}``.
- Missing/invalid bearer token → 401. Mismatched role → 403.
- Explorer routes are public and do not invoke any of these
  dependencies.
- A single ``dev_bypass_<role>`` token shape is accepted but only when
  ``ENVIRONMENT=development``, to keep local development frictionless.

The legacy ``X-User-Id`` / ``X-User-Role`` / ``X-Auth-Token`` headers are
no longer trusted. Per the contract, "Client-supplied X-User-Id and
X-User-Role headers are not part of the auth contract and must not be
trusted for authorization."
"""

from __future__ import annotations

from typing import Iterable, Literal, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.logging_config import get_logger
from backend.settings import settings

logger = get_logger("backend.auth")

Role = Literal["tagger", "scientist", "supervisor", "admin"]
ALLOWED_ROLES: tuple[str, ...] = ("tagger", "scientist", "supervisor", "admin")
JWT_ALGORITHM = "HS256"
DEV_BYPASS_PREFIX = "dev_bypass_"

# ``auto_error=False`` so we can shape our own 401 response (matching the
# contract's ``AUTH_REQUIRED`` error code via the global exception
# handler installed in Task A-4) instead of FastAPI's default
# "Not authenticated" body.
_bearer_scheme = HTTPBearer(auto_error=False, bearerFormat="JWT")


class CurrentUser(BaseModel):
    id: str
    role: Role


def _unauthorized(detail: str = "Bearer token required or invalid") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": 'Bearer realm="image-tagger"'},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _decode_jwt(token: str) -> dict:
    """Verify and decode an HS256-signed Supabase JWT.

    Raises 401 for any verification failure (invalid signature, expired,
    malformed, missing secret).
    """
    secret = settings.supabase_jwt_secret
    if not secret:
        # In production this is caught by ``Settings.assert_production_ready``
        # at lifespan startup. In dev/staging it just means JWT verification
        # is unconfigured — every protected route should fail closed.
        logger.warning("auth.jwt_secret_unset")
        raise _unauthorized()

    try:
        # Supabase tokens carry an ``aud`` claim ("authenticated") which
        # we do not need to verify in Phase 1. ``verify_signature`` and
        # ``verify_exp`` remain on by default.
        return jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        logger.warning("auth.jwt_invalid", reason=str(exc))
        raise _unauthorized() from exc


def _maybe_demo_token(token: str) -> Optional[CurrentUser]:
    """Accept the configured DEMO_TOKEN as a permanent admin credential.

    Activates only when ``DEMO_TOKEN`` is set in the environment. Returns
    ``None`` when unset so the caller falls through to JWT verification.
    """
    demo = settings.demo_token
    if not demo:
        return None
    if token != demo:
        return None
    logger.info("auth.demo_token_used")
    return CurrentUser(id="demo:admin", role="admin")  # type: ignore[arg-type]


def _maybe_dev_bypass(token: str) -> Optional[CurrentUser]:
    """Return a ``CurrentUser`` when the dev-bypass token convention applies.

    Activates only when ``ENVIRONMENT=development`` and the token matches
    ``dev_bypass_<role>``. Returns ``None`` otherwise so the caller can
    fall through to JWT verification.
    """
    if settings.environment != "development":
        return None
    if not token.startswith(DEV_BYPASS_PREFIX):
        return None

    role = token[len(DEV_BYPASS_PREFIX):]
    if role not in ALLOWED_ROLES:
        # A ``dev_bypass_*`` token with an unknown role should not silently
        # fall through to JWT verification — that would let a malformed
        # bypass attempt accidentally hit the JWT decoder. Reject it
        # explicitly with 401.
        logger.warning("auth.dev_bypass_invalid_role", role=role)
        raise _unauthorized()

    logger.info("auth.dev_bypass_used", role=role)
    return CurrentUser(id=f"dev:{role}", role=role)  # type: ignore[arg-type]


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> CurrentUser:
    """FastAPI dependency that resolves the authenticated user.

    Reads the ``Authorization: Bearer <token>`` header, supports a
    development-only ``dev_bypass_<role>`` shortcut, and otherwise
    HS256-verifies the token against ``SUPABASE_JWT_SECRET``.
    """
    if creds is None or not creds.credentials:
        raise _unauthorized()

    token = creds.credentials.strip()
    if not token:
        raise _unauthorized()

    demo = _maybe_demo_token(token)
    if demo is not None:
        return demo

    bypass = _maybe_dev_bypass(token)
    if bypass is not None:
        return bypass

    claims = _decode_jwt(token)
    user_id = claims.get("sub")
    role = claims.get("role")

    if not isinstance(user_id, str) or not user_id:
        logger.warning("auth.jwt_missing_sub")
        raise _unauthorized()
    if role not in ALLOWED_ROLES:
        logger.warning("auth.jwt_role_invalid", role_claim=role)
        raise _unauthorized()

    return CurrentUser(id=user_id, role=role)  # type: ignore[arg-type]


def _enforce_role(user: CurrentUser, allowed: Iterable[str], detail: str) -> CurrentUser:
    if user.role not in set(allowed):
        logger.warning(
            "auth.role_mismatch",
            user_id=user.id,
            user_role=user.role,
            required=tuple(allowed),
        )
        raise _forbidden(detail)
    return user


def require_tagger(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Any authenticated role can perform tagger work (workbench)."""
    return _enforce_role(user, ALLOWED_ROLES, "Tagger role required")


def require_scientist(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return _enforce_role(
        user,
        ("scientist", "supervisor", "admin"),
        "Scientist role required",
    )


def require_supervisor(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return _enforce_role(
        user,
        ("supervisor", "admin"),
        "Supervisor role required",
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    return _enforce_role(user, ("admin",), "Admin role required")


def require_admin_or_supervisor(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Backwards-compat alias used by some pre-A-3 routers."""
    return _enforce_role(
        user,
        ("supervisor", "admin"),
        "Admin or Supervisor role required",
    )


__all__ = [
    "ALLOWED_ROLES",
    "CurrentUser",
    "JWT_ALGORITHM",
    "Role",
    "get_current_user",
    "require_admin",
    "require_admin_or_supervisor",
    "require_scientist",
    "require_supervisor",
    "require_tagger",
]
