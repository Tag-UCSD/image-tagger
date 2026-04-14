"""
TRS-606: Health and metrics endpoints.

Provides comprehensive health checks and metrics for monitoring.
"""

from __future__ import annotations
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from .settings import REGISTRY_DIR
from .registry_loader import load_registry
from .cache import get_cache_stats
from .db import get_db


router = APIRouter(tags=["health"])

# Track startup time
_start_time = time.time()


@router.get("/health")
async def health():
    """Basic health check."""
    return {"ok": True, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with component status."""
    checks = {}
    overall_healthy = True
    
    # Registry check
    try:
        reg = load_registry(REGISTRY_DIR)
        tag_count = len(reg.get("tags", {}))
        checks["registry"] = {
            "healthy": True,
            "tag_count": tag_count,
            "path": str(REGISTRY_DIR),
        }
    except Exception as e:
        checks["registry"] = {"healthy": False, "error": str(e)}
        overall_healthy = False
    
    # Database check
    try:
        db = get_db()
        proposal_count = db.count_proposals()
        checks["database"] = {
            "healthy": True,
            "proposal_count": proposal_count,
        }
    except Exception as e:
        checks["database"] = {"healthy": False, "error": str(e)}
        overall_healthy = False
    
    # Cache check
    try:
        cache_stats = get_cache_stats()
        checks["cache"] = {
            "healthy": True,
            **cache_stats,
        }
    except Exception as e:
        checks["cache"] = {"healthy": False, "error": str(e)}
    
    # Uptime
    uptime_seconds = time.time() - _start_time
    
    return {
        "healthy": overall_healthy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(uptime_seconds),
        "checks": checks,
    }


@router.get("/metrics")
async def metrics():
    """
    Get service metrics.
    
    Returns Prometheus-compatible metrics.
    """
    lines = []
    
    # Uptime
    uptime = time.time() - _start_time
    lines.append(f"# HELP trs_uptime_seconds Service uptime in seconds")
    lines.append(f"# TYPE trs_uptime_seconds gauge")
    lines.append(f"trs_uptime_seconds {uptime:.2f}")
    
    # Registry stats
    try:
        reg = load_registry(REGISTRY_DIR)
        tag_count = len(reg.get("tags", {}))
        lines.append(f"# HELP trs_registry_tags_total Total tags in registry")
        lines.append(f"# TYPE trs_registry_tags_total gauge")
        lines.append(f"trs_registry_tags_total {tag_count}")
    except Exception:
        pass
    
    # Proposal stats
    try:
        db = get_db()
        for status in ["pending", "approved", "rejected", "merged"]:
            count = db.count_proposals(status)
            lines.append(f"trs_proposals_total{{status=\"{status}\"}} {count}")
    except Exception:
        pass
    
    # Cache stats
    try:
        cache = get_cache_stats()
        lines.append(f"# HELP trs_cache_hits_total Cache hit count")
        lines.append(f"# TYPE trs_cache_hits_total counter")
        lines.append(f"trs_cache_hits_total {cache.get('hits', 0)}")
        lines.append(f"trs_cache_misses_total {cache.get('misses', 0)}")
        lines.append(f"trs_cache_entries {cache.get('entries', 0)}")
    except Exception:
        pass
    
    return "\n".join(lines) + "\n"


@router.get("/version")
async def version():
    """Get service version info."""
    return {
        "service": "TRS",
        "version": "0.0.5",
        "api_version": "v1",
        "registry_version": str(REGISTRY_DIR.parent.name) if REGISTRY_DIR.exists() else "unknown",
    }


@router.get("/ready")
async def readiness():
    """
    Kubernetes readiness probe.
    
    Returns 200 if ready to serve traffic.
    """
    try:
        # Check registry is loadable
        reg = load_registry(REGISTRY_DIR)
        if not reg.get("tags"):
            return {"ready": False, "reason": "Empty registry"}
        
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "reason": str(e)}


@router.get("/live")
async def liveness():
    """
    Kubernetes liveness probe.
    
    Returns 200 if service is alive.
    """
    return {"alive": True}
