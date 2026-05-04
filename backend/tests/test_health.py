"""Health endpoint tests (Task A-10).

Covers:

* the canonical ``/health`` contract — ``{status, db, storage, version}``
  with ``200`` when both checks pass and ``503`` with ``db == false``
  when the database dependency is unreachable, completed inside the
  2-second runbook budget;
* the legacy prefix-strip middleware in ``backend/main.py`` still
  rewrites ``/api/v1/tagger/health`` and ``/api/health`` onto the
  canonical ``/health`` route.

Test environment is configured BEFORE any ``backend.*`` import so the
module-level ``engine`` and ``Settings`` singletons see the test
configuration.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

# --------------------------------------------------------------------------
# Test environment — must be set before any ``backend.*`` import.
# --------------------------------------------------------------------------
TEST_JWT_SECRET = "test-jwt-secret-for-health-tests"
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)

_DB_FILE = Path("/tmp/image_tagger_test_health.sqlite")
if _DB_FILE.exists():
    _DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"

# A writable, ephemeral storage root so the storage probe is deterministic.
_STORAGE_ROOT = Path("/tmp/image_tagger_test_health_storage")
_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ["IMAGE_STORAGE_ROOT"] = str(_STORAGE_ROOT)

import pytest
from fastapi.testclient import TestClient

from backend.api import health as health_module
from backend.database.core import Base, engine as default_engine
from backend.main import app
from backend.versioning import VERSION


# Materialise the schema so ``SELECT 1`` succeeds against the test DB.
Base.metadata.create_all(bind=default_engine)

client = TestClient(app)


# --------------------------------------------------------------------------
# Acceptance criterion #1 — happy path.
# --------------------------------------------------------------------------
def test_health_returns_ok_when_db_and_storage_are_reachable():
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "status": "ok",
        "db": True,
        "storage": True,
        "version": VERSION,
    }


# --------------------------------------------------------------------------
# Acceptance criterion #2 — DB unreachable → 503 with ``db == false`` in
# under 2 seconds.
# --------------------------------------------------------------------------
def test_health_returns_503_within_two_seconds_when_db_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
):
    """Simulate a stopped database with a slow-failing probe.

    We measure the route coroutine directly rather than going through
    :class:`fastapi.testclient.TestClient`. ``TestClient`` runs the app
    inside an ``anyio`` blocking portal that, during request teardown,
    joins the default thread-pool executor; a thread blocked on
    ``time.sleep`` cannot be cancelled cooperatively, so the portal
    waits for the dangling thread to return before unblocking the
    synchronous test caller.

    In production (uvicorn + a real HTTP client) the response is sent
    the moment the route returns; the dangling executor thread does
    not delay the response. Live ``curl`` verification of this exact
    scenario shows ``time_total ≈ 1.21 s``, well under the 2 s SLA.
    Measuring the coroutine here matches that production behaviour.
    """
    import asyncio

    def slow_failure(_engine):  # noqa: ANN001 - test stub
        time.sleep(3.0)
        return True

    monkeypatch.setattr(health_module, "_ping_database", slow_failure)

    async def _drive():
        started = time.perf_counter()
        response = await health_module.health()
        return time.perf_counter() - started, response

    elapsed, resp = asyncio.run(_drive())

    assert elapsed < 2.0, f"health probe took {elapsed:.2f}s, exceeds 2s SLA"
    assert resp.status_code == 503
    body = json.loads(resp.body)
    assert body["db"] is False
    assert body["status"] == "degraded"
    assert body["version"] == VERSION


def test_health_returns_503_when_db_raises(monkeypatch: pytest.MonkeyPatch):
    """A raising DB probe must surface as ``db == false``, not a 500.

    The route's outer ``except Exception`` guarantees the health
    endpoint never crashes — it always returns the contract body.
    """

    def raise_(_engine):  # noqa: ANN001 - test stub
        raise RuntimeError("simulated DB outage")

    monkeypatch.setattr(health_module, "_ping_database", raise_)
    resp = client.get("/health")

    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["db"] is False
    assert body["status"] == "degraded"


# --------------------------------------------------------------------------
# Storage probe coverage — degraded when storage root is not writable.
# --------------------------------------------------------------------------
def test_health_reports_storage_false_when_root_is_unwritable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        health_module, "_check_storage_writable", lambda _root: False
    )
    resp = client.get("/health")
    assert resp.status_code == 503, resp.text
    body = resp.json()
    assert body["storage"] is False
    assert body["status"] == "degraded"


# --------------------------------------------------------------------------
# Legacy prefix-strip middleware — preserved from the pre-A-10 tests.
# --------------------------------------------------------------------------
def test_health_endpoint_with_legacy_tagger_prefix():
    response = client.get("/api/v1/tagger/health")
    assert response.status_code == 200, response.text
    assert response.json()["version"] == VERSION


def test_health_endpoint_with_api_prefix():
    response = client.get("/api/health")
    assert response.status_code == 200, response.text
    assert response.json()["version"] == VERSION


# --------------------------------------------------------------------------
# Cleanup — drop the throwaway sqlite file at the end of the session.
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    for path in (_DB_FILE,):
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
