"""
TRS-805 & TRS-806: Metrics dashboard and dependency health checks.

Provides:
- Rich metrics endpoint for dashboards
- Dependency health checks (database, file system, etc.)
- System resource metrics

Usage:
    from backend.app.dashboard import router as dashboard_router
    app.include_router(dashboard_router)
"""

from __future__ import annotations
import os
import platform
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from .settings import REGISTRY_DIR
from .db import get_db
from .metrics import metrics
from .auth import require_auth, require_role, optional_auth, APIKey


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ============================================================================
# Dependency Health Checks
# ============================================================================

class DependencyChecker:
    """Checks health of external dependencies."""
    
    @staticmethod
    def check_database() -> dict:
        """Check database connectivity."""
        start = time.time()
        try:
            db = get_db()
            # Simple query to verify connection
            with db._connect() as conn:
                conn.execute("SELECT 1").fetchone()
            
            latency_ms = (time.time() - start) * 1000
            
            return {
                "name": "database",
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "details": {
                    "path": str(db.db_path),
                    "size_bytes": db.db_path.stat().st_size if db.db_path.exists() else 0,
                },
            }
        except Exception as e:
            return {
                "name": "database",
                "healthy": False,
                "error": str(e),
            }
    
    @staticmethod
    def check_registry() -> dict:
        """Check registry file accessibility."""
        start = time.time()
        try:
            if not REGISTRY_DIR.exists():
                return {
                    "name": "registry",
                    "healthy": False,
                    "error": f"Registry directory not found: {REGISTRY_DIR}",
                }
            
            # Find registry files
            yamls = list(REGISTRY_DIR.glob("*.yaml")) + list(REGISTRY_DIR.glob("*.yml"))
            
            if not yamls:
                return {
                    "name": "registry",
                    "healthy": False,
                    "error": "No registry YAML files found",
                }
            
            # Check file is readable
            reg_file = yamls[0]
            size = reg_file.stat().st_size
            
            latency_ms = (time.time() - start) * 1000
            
            return {
                "name": "registry",
                "healthy": True,
                "latency_ms": round(latency_ms, 2),
                "details": {
                    "path": str(reg_file),
                    "size_bytes": size,
                    "files": len(yamls),
                },
            }
        except Exception as e:
            return {
                "name": "registry",
                "healthy": False,
                "error": str(e),
            }
    
    @staticmethod
    def check_disk_space() -> dict:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            free_percent = (free / total) * 100
            
            # Warn if less than 10% free
            healthy = free_percent > 10
            
            return {
                "name": "disk",
                "healthy": healthy,
                "details": {
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                    "free_percent": round(free_percent, 1),
                },
            }
        except Exception as e:
            return {
                "name": "disk",
                "healthy": False,
                "error": str(e),
            }
    
    @staticmethod
    def check_memory() -> dict:
        """Check memory usage (if psutil available)."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            
            return {
                "name": "memory",
                "healthy": mem.percent < 90,
                "details": {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "available_gb": round(mem.available / (1024**3), 2),
                    "percent_used": mem.percent,
                },
            }
        except ImportError:
            return {
                "name": "memory",
                "healthy": True,
                "details": {"note": "psutil not installed"},
            }
        except Exception as e:
            return {
                "name": "memory",
                "healthy": False,
                "error": str(e),
            }
    
    @classmethod
    def check_all(cls) -> list[dict]:
        """Run all dependency checks."""
        return [
            cls.check_database(),
            cls.check_registry(),
            cls.check_disk_space(),
            cls.check_memory(),
        ]


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/health")
async def dashboard_health(api_key: APIKey = Depends(require_auth)):
    """
    Comprehensive health check with all dependencies.
    Requires authentication.
    """
    checks = DependencyChecker.check_all()
    
    overall_healthy = all(c.get("healthy", False) for c in checks)
    
    return {
        "healthy": overall_healthy,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": checks,
    }


@router.get("/metrics")
async def dashboard_metrics(api_key: APIKey = Depends(require_auth)):
    """
    Rich metrics for dashboard display.
    Requires authentication.
    """
    m = metrics.get_metrics()
    
    # Add business context
    try:
        db = get_db()
        m["proposals"] = {
            "pending": db.count_proposals("pending"),
            "approved": db.count_proposals("approved"),
            "rejected": db.count_proposals("rejected"),
            "merged": db.count_proposals("merged"),
        }
        
        latest_release = db.get_latest_release()
        if latest_release:
            m["latest_release"] = {
                "version": latest_release.version,
                "released_at": latest_release.created_at,
                "released_by": latest_release.released_by,
            }
    except Exception:
        pass
    
    return m


@router.get("/metrics/prometheus")
async def prometheus_metrics(api_key: APIKey = Depends(require_auth)):
    """
    Metrics in Prometheus format.
    Requires authentication.
    """
    from fastapi import Response
    content = metrics.get_prometheus_metrics()
    return Response(content=content, media_type="text/plain")


@router.get("/system")
async def system_info(api_key: APIKey = Depends(require_role("admin"))):
    """
    System information for debugging.
    Requires admin role.
    """
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "cpu_count": os.cpu_count(),
        "pid": os.getpid(),
        "cwd": os.getcwd(),
        "environment": {
            "TRS_CORE_VER": os.getenv("TRS_CORE_VER", "not set"),
            "TRS_DB_PATH": os.getenv("TRS_DB_PATH", "not set"),
        },
    }


@router.get("/requests")
async def request_stats(api_key: APIKey = Depends(require_auth)):
    """
    Detailed request statistics.
    Requires authentication.
    """
    m = metrics.get_metrics()
    
    # Calculate top endpoints
    counts = m.get("requests", {}).get("counts", {})
    latencies = m.get("requests", {}).get("latencies", {})
    
    # Aggregate by endpoint
    endpoint_stats = {}
    for key, count in counts.items():
        parts = key.rsplit("_", 2)  # method_path_status
        if len(parts) >= 3:
            method, path, status = parts[0], "_".join(parts[1:-1]), parts[-1]
            endpoint_key = f"{method} {path}"
            
            if endpoint_key not in endpoint_stats:
                endpoint_stats[endpoint_key] = {
                    "method": method,
                    "path": path,
                    "total_requests": 0,
                    "status_codes": {},
                }
            
            endpoint_stats[endpoint_key]["total_requests"] += count
            endpoint_stats[endpoint_key]["status_codes"][status] = count
    
    # Add latency info
    for key, latency in latencies.items():
        parts = key.split("_", 1)
        if len(parts) == 2:
            endpoint_key = f"{parts[0]} {parts[1]}"
            if endpoint_key in endpoint_stats:
                endpoint_stats[endpoint_key]["latency"] = latency
    
    # Sort by total requests
    top_endpoints = sorted(
        endpoint_stats.values(),
        key=lambda x: x["total_requests"],
        reverse=True,
    )[:20]
    
    return {
        "top_endpoints": top_endpoints,
        "active_requests": m.get("requests", {}).get("active", 0),
    }


@router.get("/errors")
async def error_stats(api_key: APIKey = Depends(require_auth)):
    """
    Error statistics and recent errors.
    Requires authentication.
    """
    m = metrics.get_metrics()
    
    errors = m.get("errors", {})
    
    # Calculate error rate
    total_requests = sum(
        v for v in m.get("requests", {}).get("counts", {}).values()
    )
    total_errors = sum(errors.values())
    error_rate = total_errors / total_requests if total_requests > 0 else 0
    
    return {
        "total_errors": total_errors,
        "error_rate": round(error_rate, 4),
        "by_type": errors,
    }


@router.get("/database")
async def database_stats(api_key: APIKey = Depends(require_auth)):
    """
    Database statistics.
    Requires authentication.
    """
    try:
        db = get_db()
        
        stats = {
            "path": str(db.db_path),
            "size_bytes": db.db_path.stat().st_size if db.db_path.exists() else 0,
        }
        
        with db._connect() as conn:
            # Table sizes
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            stats["tables"] = {}
            for table in tables:
                name = table["name"]
                count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                stats["tables"][name] = count
            
            # SQLite stats
            page_count = conn.execute("PRAGMA page_count").fetchone()[0]
            page_size = conn.execute("PRAGMA page_size").fetchone()[0]
            stats["sqlite"] = {
                "page_count": page_count,
                "page_size": page_size,
                "total_pages_bytes": page_count * page_size,
            }
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}


@router.get("/cache")
async def cache_stats(api_key: APIKey = Depends(require_auth)):
    """
    Cache statistics.
    Requires authentication.
    """
    m = metrics.get_metrics()
    
    cache = m.get("cache", {})
    
    return {
        "hits": cache.get("hits", 0),
        "misses": cache.get("misses", 0),
        "hit_rate": cache.get("hit_rate", 0),
        "effectiveness": "good" if cache.get("hit_rate", 0) > 0.8 else "needs_improvement",
    }
