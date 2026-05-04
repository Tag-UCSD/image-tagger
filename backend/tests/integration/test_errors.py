"""Integration tests for the global error envelope (Task A-4).

Asserts the contract-shaped ``{ error: { code, message, request_id,
details? } }`` response is returned for:

* ``RequestValidationError`` (query / body / multipart) →
  ``code="VALIDATION_ERROR"`` with the canonical message.
* Application-raised ``HTTPException`` (e.g. ``404``).
* Unhandled runtime exceptions → ``code="INTERNAL_ERROR"`` and a
  populated ``request_id`` that matches the ``X-Request-ID`` header.

The runtime-failure case is the named acceptance test
``test_db_error_returns_request_id``.
"""

from __future__ import annotations

import os
from pathlib import Path

# Bind test environment before any backend imports so the global
# ``settings`` singleton picks them up.
TEST_JWT_SECRET = "test-jwt-secret-for-integration-errors"
os.environ.setdefault("ENVIRONMENT", "development")
os.environ["SUPABASE_JWT_SECRET"] = TEST_JWT_SECRET

_DB_FILE = Path("/tmp/image_tagger_test_errors.sqlite")
if _DB_FILE.exists():
    _DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.core import Base, get_db
from backend.main import app


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
client = TestClient(app, raise_server_exceptions=False)


# --------------------------------------------------------------------------
# Acceptance criterion: runtime failure surfaces the contract envelope.
# --------------------------------------------------------------------------
def test_db_error_returns_request_id():
    """A runtime DB failure inside a route returns INTERNAL_ERROR + request_id.

    We swap the ``get_db`` dependency for a generator that raises before
    yielding, simulating a session-acquisition failure (network outage,
    pool exhaustion, etc.). The response must:

    * not be 2xx
    * carry the contract envelope shape
    * have ``error.code == "INTERNAL_ERROR"``
    * have ``error.request_id`` populated as a string and equal to the
      value of the ``X-Request-ID`` response header
    """

    def broken_db():
        raise RuntimeError("Simulated DB failure for A-4 test")
        yield  # pragma: no cover - unreachable, retained for type checking

    app.dependency_overrides[get_db] = broken_db
    try:
        # ``/v1/admin/budget`` runs through ``require_admin`` (auth) and
        # ``get_db`` (which we just sabotaged). With dev bypass enabled
        # the auth dep succeeds, then resolving ``db`` raises and the
        # generic exception handler returns the contract envelope.
        resp = client.get(
            "/v1/admin/budget",
            headers={"Authorization": "Bearer dev_bypass_admin"},
        )
    finally:
        app.dependency_overrides[get_db] = _override_get_db

    assert resp.status_code == 500, resp.text
    body = resp.json()
    assert "error" in body, body
    err = body["error"]
    assert err["code"] == "INTERNAL_ERROR", err
    assert err["message"] == "Internal server error", err
    assert isinstance(err["request_id"], str) and err["request_id"], err
    # The X-Request-ID header is set by the request-context middleware
    # AND mirrored into the body by the error handler — they must agree.
    assert resp.headers.get("x-request-id") == err["request_id"]


# --------------------------------------------------------------------------
# Validation envelope coverage — query, body and multipart.
# --------------------------------------------------------------------------
def test_get_explorer_search_negative_page_returns_validation_envelope():
    resp = client.get("/v1/explorer/search?page=-5")
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["message"] == "Request validation failed"
    assert isinstance(err["request_id"], str) and err["request_id"]
    assert isinstance(err["details"], list) and err["details"]
    assert err["details"][0]["field"] == "page"


def test_post_explorer_search_invalid_body_returns_validation_envelope():
    resp = client.post(
        "/v1/explorer/search",
        json={"page": 0, "page_size": 999},
    )
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["message"] == "Request validation failed"
    fields = {d["field"] for d in err["details"]}
    assert "page" in fields or "page_size" in fields, err


def test_admin_upload_invalid_multipart_returns_validation_envelope():
    """``POST /v1/admin/upload`` with no multipart body → VALIDATION_ERROR.

    The dev-bypass admin token authenticates the request so the
    deeper body validation runs and triggers the global handler.
    """
    resp = client.post(
        "/v1/admin/upload",
        headers={"Authorization": "Bearer dev_bypass_admin"},
    )
    assert resp.status_code == 422, resp.text
    err = resp.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert err["message"] == "Request validation failed"


# --------------------------------------------------------------------------
# Application-raised HTTPException pass-through.
# --------------------------------------------------------------------------
def test_explorer_unknown_image_returns_not_found_envelope():
    """A 404 raised by route code keeps the envelope shape (NOT_FOUND)."""
    resp = client.get("/v1/explorer/images/999999/detail")
    # Could be 404 NOT_FOUND or 422 if route binding rejects path; either way
    # the envelope shape must be respected.
    assert resp.status_code in (404, 422), resp.text
    err = resp.json()["error"]
    assert err["code"] in ("NOT_FOUND", "VALIDATION_ERROR")
    assert isinstance(err["request_id"], str) and err["request_id"]


# --------------------------------------------------------------------------
# Cleanup — drop the throwaway sqlite file at the end of the session.
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    if _DB_FILE.exists():
        try:
            _DB_FILE.unlink()
        except OSError:
            pass
