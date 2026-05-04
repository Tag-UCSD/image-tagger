"""RBAC enforcement tests for Admin endpoints (Task A-3 update).

These tests originally relied on the legacy ``X-User-Role`` header trust
scheme. Under Task A-3 the backend reads identity exclusively from a
Supabase-issued JWT, so the same scenarios are now exercised with bearer
tokens minted against the test ``SUPABASE_JWT_SECRET``.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

# Configure the auth secret + sqlite DB before any backend imports so
# the global ``Settings`` singleton and SQLAlchemy engine see them.
TEST_JWT_SECRET = "test-jwt-secret-for-rbac-tests"
os.environ.setdefault("ENVIRONMENT", "development")
os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET

_DB_FILE = Path("/tmp/image_tagger_test_rbac.sqlite")
if _DB_FILE.exists():
    _DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.core import Base, get_db
from backend.main import app
from backend.settings import settings


_engine = create_engine(
    os.environ["DATABASE_URL"],
    connect_args={"check_same_thread": False},
)
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base.metadata.create_all(bind=_engine)


def override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _mint(role: str) -> str:
    # Use the secret that the running app actually has bound on its
    # ``settings`` singleton. ``backend.settings`` resolves the secret
    # once at import time, so when this test module is collected after
    # ``test_auth.py`` (which sets a different secret) we still mint
    # tokens that match the live server.
    secret = settings.supabase_jwt_secret or TEST_JWT_SECRET
    now = int(time.time())
    return jwt.encode(
        {
            "sub": f"rbac-test-{role}",
            "role": role,
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        secret,
        algorithm="HS256",
    )


def test_admin_endpoint_forbidden_without_admin_header():
    # No bearer token → require_admin should reject with 401 (no auth).
    r = client.get("/v1/admin/models")
    assert r.status_code in (401, 403)


def test_admin_endpoint_allows_admin_jwt():
    r = client.get(
        "/v1/admin/models",
        headers={"Authorization": f"Bearer {_mint('admin')}"},
    )
    assert r.status_code == 200, r.text


def test_admin_endpoint_rejects_tagger_jwt_with_403():
    r = client.get(
        "/v1/admin/models",
        headers={"Authorization": f"Bearer {_mint('tagger')}"},
    )
    assert r.status_code == 403, r.text
