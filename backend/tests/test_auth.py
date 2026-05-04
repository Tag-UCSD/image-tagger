"""Auth tests (Task A-3).

Covers the acceptance criteria for Supabase JWT verification:

* ``test_valid_admin_jwt_returns_200_on_admin_budget`` — a token signed
  with the configured ``SUPABASE_JWT_SECRET`` whose claims include
  ``role="admin"`` succeeds against ``GET /v1/admin/budget``.
* ``test_valid_admin_jwt_with_tampered_signature_returns_401`` — the
  same admin token with a single signature byte flipped is rejected
  with ``401``.
* ``test_valid_tagger_jwt_returns_403_on_admin_budget`` — a valid token
  whose ``role`` claim is ``tagger`` is rejected with ``403`` against
  the admin-only route.

Plus a few sanity checks (missing-bearer 401, dev-bypass token in
development, malformed token shape) so regressions in the auth
dependency don't go unnoticed.

The test file deliberately sets environment variables BEFORE importing
the FastAPI app so ``backend.settings.Settings`` (a module-level
singleton) and the SQLAlchemy engine in ``backend.database.core`` both
see the test configuration. Importing the app at module top would
otherwise lock in the developer's real ``.env``.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

# --------------------------------------------------------------------------
# Test environment — must be set before any ``backend.*`` import.
# --------------------------------------------------------------------------
TEST_JWT_SECRET = "test-jwt-secret-for-unit-tests-only"

os.environ.setdefault("ENVIRONMENT", "development")
os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET

# Use an on-disk sqlite file so SessionLocal-scoped helpers
# (e.g. ``backend.services.costs.get_total_spent``) and the request
# session both see the same database. ``:memory:`` is per-connection in
# SQLite, which would yield empty tables for the SessionLocal helper.
_DB_FILE = Path("/tmp/image_tagger_test_auth.sqlite")
if _DB_FILE.exists():
    _DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.core import Base, get_db
from backend.main import app
from backend.services.auth import JWT_ALGORITHM
from backend.settings import settings as _app_settings


# --------------------------------------------------------------------------
# DB scaffolding — share one engine with the app.
# --------------------------------------------------------------------------
_engine = create_engine(
    os.environ["DATABASE_URL"],
    connect_args={"check_same_thread": False},
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base.metadata.create_all(bind=_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _server_secret() -> str:
    """Return the secret the running app actually has bound on its settings.

    ``backend.settings`` resolves the secret once at import time. When
    this module is collected after another test module that already set
    its own ``SUPABASE_JWT_SECRET`` env var, the live ``settings``
    singleton is bound to the *first* secret seen. Minting against
    ``settings.supabase_jwt_secret`` keeps these tests deterministic
    regardless of collection order.
    """
    return _app_settings.supabase_jwt_secret or TEST_JWT_SECRET


def _mint_jwt(role: str, *, sub: str | None = None, secret: str | None = None) -> str:
    """Mint a Supabase-shaped JWT with the role claim required by A-3."""
    now = int(time.time())
    claims = {
        "sub": sub or f"test-user-{uuid.uuid4().hex[:8]}",
        "role": role,
        "aud": "authenticated",
        "iss": "test-supabase",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(claims, secret or _server_secret(), algorithm=JWT_ALGORITHM)


def _tamper_signature(token: str) -> str:
    """Return a copy of ``token`` with the signature segment corrupted.

    JWTs are ``header.payload.signature`` triples. Flipping the last
    character of the signature is sufficient to fail HS256 verification
    while keeping the overall token structurally valid.
    """
    head, payload, signature = token.split(".")
    if not signature:
        raise AssertionError("token has empty signature segment")
    last = signature[-1]
    swapped = "A" if last != "A" else "B"
    return f"{head}.{payload}.{signature[:-1]}{swapped}"


# --------------------------------------------------------------------------
# Acceptance-criterion tests (selected by ``-k 'valid_admin_jwt'``).
# --------------------------------------------------------------------------
def test_valid_admin_jwt_returns_200_on_admin_budget():
    """A valid admin JWT lets us reach an admin-only endpoint."""
    token = _mint_jwt("admin")
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {"total_spent", "hard_limit", "is_kill_switched"} <= set(body.keys())


def test_valid_admin_jwt_with_tampered_signature_returns_401():
    """Same shape as the above, but a flipped signature byte → 401."""
    token = _mint_jwt("admin")
    tampered = _tamper_signature(token)
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert resp.status_code == 401, resp.text


# --------------------------------------------------------------------------
# Acceptance-criterion test — role mismatch.
# --------------------------------------------------------------------------
def test_valid_tagger_jwt_returns_403_on_admin_budget():
    """A valid JWT whose role is `tagger` cannot reach admin routes."""
    token = _mint_jwt("tagger")
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, resp.text


# --------------------------------------------------------------------------
# Additional regressions / contract sanity checks.
# --------------------------------------------------------------------------
def test_admin_budget_without_authorization_header_returns_401():
    resp = client.get("/v1/admin/budget")
    assert resp.status_code == 401


def test_admin_budget_with_non_bearer_scheme_returns_401():
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": "Basic abcdef"},
    )
    assert resp.status_code == 401


def test_admin_budget_with_token_signed_by_wrong_secret_returns_401():
    token = _mint_jwt("admin", secret="not-the-server-secret")
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_admin_budget_with_unknown_role_claim_returns_401():
    token = _mint_jwt("kingdom_overlord")
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_dev_bypass_token_works_in_development_for_admin():
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": "Bearer dev_bypass_admin"},
    )
    assert resp.status_code == 200, resp.text


def test_dev_bypass_token_with_tagger_role_returns_403_for_admin_route():
    resp = client.get(
        "/v1/admin/budget",
        headers={"Authorization": "Bearer dev_bypass_tagger"},
    )
    assert resp.status_code == 403


def test_explorer_search_is_public_and_does_not_require_auth():
    """Per CONTRACT.md, explorer endpoints are anonymous public-read."""
    resp = client.post("/v1/explorer/search", json={"text": "", "page": 1, "page_size": 5})
    # We don't care about the body shape here, only that the auth layer
    # did not block the request.
    assert resp.status_code != 401, resp.text
    assert resp.status_code != 403, resp.text


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    if _DB_FILE.exists():
        try:
            _DB_FILE.unlink()
        except OSError:
            pass
