"""Health endpoint with real dependency checks (Task A-10).

Reports liveness of the API plus the two infrastructure dependencies the
Phase 1 contract calls out: the database (``SELECT 1``) and the
configured image storage root (writable check). Both checks are bounded
to a small wall-clock budget so the runbook acceptance criterion of
"returns 503 within 2 seconds when the database is stopped" holds even
when the underlying driver would otherwise hang on an OS-level connect
timeout.

Phase 1 deliberately stops here. Prometheus-style ``/metrics`` endpoints,
Sentry integration, and any deeper observability are explicitly deferred
to follow-up work (see ``docs/workplan/PLAN_BACKEND_PHASE1.md`` task
A-10).
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.database.core import engine as default_engine
from backend.logging_config import get_logger
from backend.settings import settings
from backend.versioning import VERSION

logger = get_logger("backend.health")

router = APIRouter(tags=["health"])

# Per-check wall-clock budgets. The acceptance criterion is "returns 503
# within 2 seconds when DB is down"; we stay safely under that by giving
# the DB and storage checks their own slices and letting the route
# overall complete in well under 2s even when both checks time out.
_DB_CHECK_TIMEOUT_SECONDS = 1.2
_STORAGE_CHECK_TIMEOUT_SECONDS = 0.5


def _ping_database(engine: Engine) -> bool:
    """Run ``SELECT 1`` against the configured DB.

    Synchronous on purpose — the caller wraps this in
    :func:`asyncio.wait_for` so a hung TCP connect or an unbounded
    driver timeout cannot blow past the 2-second runbook budget.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar_one()
        return result == 1
    except Exception:
        logger.warning("health.db_unreachable", exc_info=True)
        return False


def _check_storage_writable(root: str) -> bool:
    """Return ``True`` iff a temp file can be created under ``root``.

    The image storage root is configured via ``IMAGE_STORAGE_ROOT``. The
    actual write lives entirely inside ``tempfile.NamedTemporaryFile``
    so we never leave a probe file behind, even on a failed run.
    """
    try:
        path = Path(root)
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".healthcheck_", dir=str(path), delete=True
        ):
            pass
        return True
    except Exception:
        logger.warning("health.storage_not_writable", root=root, exc_info=True)
        return False


@router.get("/health")
async def health() -> JSONResponse:
    """Real dependency check.

    Returns ``200`` when both the database and the storage root are
    reachable; ``503`` otherwise. The body shape is fixed by the
    contract::

        {"status": "ok" | "degraded",
         "db":      bool,
         "storage": bool,
         "version": str}

    The route is ``async`` so each blocking check runs in the default
    threadpool with a per-check :func:`asyncio.wait_for` budget.
    """
    loop = asyncio.get_running_loop()

    db_ok = False
    storage_ok = False

    # The health endpoint must never crash. Each probe is wrapped in a
    # broad ``except Exception`` so a misbehaving driver, a sudden
    # cancellation, or a probe that bypasses its own try/except still
    # surfaces as ``False`` rather than propagating to the global 500
    # handler.
    try:
        db_ok = await asyncio.wait_for(
            loop.run_in_executor(None, _ping_database, default_engine),
            timeout=_DB_CHECK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "health.db_timeout",
            timeout_s=_DB_CHECK_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.warning("health.db_probe_raised", exc_info=True)

    try:
        storage_ok = await asyncio.wait_for(
            loop.run_in_executor(
                None, _check_storage_writable, settings.image_storage_root
            ),
            timeout=_STORAGE_CHECK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "health.storage_timeout",
            timeout_s=_STORAGE_CHECK_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.warning("health.storage_probe_raised", exc_info=True)

    overall_ok = bool(db_ok and storage_ok)
    body: Dict[str, Any] = {
        "status": "ok" if overall_ok else "degraded",
        "db": bool(db_ok),
        "storage": bool(storage_ok),
        "version": VERSION,
    }
    return JSONResponse(
        content=body,
        status_code=200 if overall_ok else 503,
    )


__all__ = ["router"]
