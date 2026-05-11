"""Shared pytest fixtures for backend tests (Task A-11).

Environment variables are set **before** any ``backend.*`` import. The
global :mod:`backend.database` engine is then rebound to a dedicated
temporary **file-backed** SQLite database using :class:`~sqlalchemy.pool.StaticPool`
so all connections share one schema. (Plain ``sqlite:///:memory:`` was
discarded: connection recycling from ASGI clients and thread-pool sync
routes left HTTP handlers talking to an empty database.)

When running the Phase 1 smoke command::

    pytest backend/tests/integration/test_explorer.py \\
        backend/tests/integration/test_workbench.py \\
        ...

only this conftest and the integration modules need to be collected.

For ``httpx.AsyncClient`` + ASGI, each test that uses :func:`async_client`
temporarily installs the shared ``get_db`` override and restores the
previous override (if any) afterward.
"""

from __future__ import annotations

import os
import tempfile
import time
import uuid
from typing import AsyncIterator, Iterator

# ---------------------------------------------------------------------------
# Environment — before backend imports ``database.core`` (eager engine).
# ---------------------------------------------------------------------------
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault(
    "SUPABASE_JWT_SECRET",
    "phase1-a11-smoke-critical-integration-secret",
)
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("VLM_HARD_LIMIT_USD", "10.0")

# Writable SQLite file — ``:memory:`` is unsafe with StaticPool + TestClient/async
# thread-pool traffic because connection recycling can leave requests against an empty DB.
_SQLITE_FILE = tempfile.NamedTemporaryFile(
    prefix="image_tagger_a11_", suffix=".sqlite", delete=False
)
_SQLITE_FILE.close()
_SQLITE_PATH = _SQLITE_FILE.name
os.environ["DATABASE_URL"] = f"sqlite:///{_SQLITE_PATH}"

_TEST_IMAGE_ROOT = tempfile.mkdtemp(prefix="image_tagger_a11_storage_")
os.environ["IMAGE_STORAGE_ROOT"] = _TEST_IMAGE_ROOT

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.database.core as db_core

_shared_engine = sa.create_engine(
    f"sqlite:///{_SQLITE_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
try:
    db_core.engine.dispose(close=False)
except Exception:
    pass
db_core.engine = _shared_engine
db_core.SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=_shared_engine
)

from backend.database.core import Base, get_db
import backend.models  # noqa: F401 — register mapped tables on Base.metadata

Base.metadata.create_all(bind=_shared_engine)

_TestSessionLocal = db_core.SessionLocal
integration_session_factory = db_core.SessionLocal

from backend.main import app  # noqa: E402 — after DB engine patch
from backend.services.auth import JWT_ALGORITHM  # noqa: E402


def _override_get_db() -> Iterator[Session]:
    db = _TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


def mint_jwt(role: str, *, sub: str = "a11-test-subject-0001") -> str:
    """HS256 token minted with the same secret as the running app."""
    now = int(time.time())
    return jwt.encode(
        {
            "sub": sub,
            "role": role,
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        os.environ["SUPABASE_JWT_SECRET"],
        algorithm=JWT_ALGORITHM,
    )


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """Async HTTP client against the FastAPI app."""
    prev = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client
    if prev is not None:
        app.dependency_overrides[get_db] = prev
    else:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def a11_db_session() -> Iterator[Session]:
    """Direct SQLAlchemy session bound to the integration test engine."""
    s = _TestSessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def seed_smoke_image_and_attribute(a11_db_session: Session) -> tuple[int, str]:
    """Insert a registry Attribute + Image row for workbench validation flows."""
    from backend.models.attribute import Attribute
    from backend.models.assets import Image

    attr_key = f"a11.smoke.{uuid.uuid4().hex[:10]}"
    a11_db_session.add(
        Attribute(
            key=attr_key,
            name="A11 Smoke Attribute",
            category="test",
        )
    )
    img = Image(
        filename="smoke.jpg",
        storage_path="smoke_path.jpg",
        meta_data={},
    )
    a11_db_session.add(img)
    a11_db_session.commit()
    a11_db_session.refresh(img)
    return img.id, attr_key


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Remove the temp SQLite file (best-effort)."""
    try:
        os.unlink(_SQLITE_PATH)
    except OSError:
        pass
