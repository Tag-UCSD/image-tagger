"""
TRS-802: Performance metrics collection.

Collects and exposes metrics for monitoring:
- Request latency histograms
- Request counts by endpoint/status
- Active connections
- Business metrics (proposals, releases)

Usage:
    from backend.app.metrics import metrics, track_request
    
    # Track a request
    with track_request("GET", "/api/search"):
        result = do_work()
    
    # Get metrics
    data = metrics.get_metrics()
"""

from __future__ import annotations
import statistics
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Histogram:
    """Simple histogram for tracking latencies."""
    
    buckets: list[float] = field(default_factory=lambda: [
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
    ])
    counts: dict[float, int] = field(default_factory=dict)
    total: float = 0.0
    count: int = 0
    
    def __post_init__(self):
        self.counts = {b: 0 for b in self.buckets}
        self.counts[float("inf")] = 0
    
    def observe(self, value: float) -> None:
        """Record an observation."""
        self.total += value
        self.count += 1
        
        for bucket in self.buckets:
            if value <= bucket:
                self.counts[bucket] += 1
                return
        
        self.counts[float("inf")] += 1
    
    def get_percentile(self, p: float) -> Optional[float]:
        """Estimate percentile (approximate)."""
        if self.count == 0:
            return None
        
        target = self.count * p
        cumulative = 0
        
        for bucket in sorted(self.counts.keys()):
            cumulative += self.counts[bucket]
            if cumulative >= target:
                return bucket
        
        return None


@dataclass
class Counter:
    """Thread-safe counter."""
    
    value: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def inc(self, amount: int = 1) -> None:
        with self._lock:
            self.value += amount
    
    def get(self) -> int:
        return self.value


@dataclass
class Gauge:
    """Thread-safe gauge for current values."""
    
    value: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def set(self, value: float) -> None:
        with self._lock:
            self.value = value
    
    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self.value += amount
    
    def dec(self, amount: float = 1.0) -> None:
        with self._lock:
            self.value -= amount
    
    def get(self) -> float:
        return self.value


class MetricsCollector:
    """
    Central metrics collector.
    
    Tracks:
    - HTTP request metrics
    - Database operation metrics
    - Business metrics
    - System metrics
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        
        # Request metrics
        self.request_count = defaultdict(Counter)  # {(method, path, status): Counter}
        self.request_latency = defaultdict(Histogram)  # {(method, path): Histogram}
        self.active_requests = Gauge()
        
        # Database metrics
        self.db_query_count = Counter()
        self.db_query_latency = Histogram()
        self.db_error_count = Counter()
        
        # Business metrics
        self.proposals_created = Counter()
        self.proposals_approved = Counter()
        self.proposals_rejected = Counter()
        self.releases_created = Counter()
        self.searches_performed = Counter()
        
        # Cache metrics
        self.cache_hits = Counter()
        self.cache_misses = Counter()
        
        # Error metrics
        self.error_count = defaultdict(Counter)  # {error_type: Counter}
        
        # Start time for uptime calculation
        self._start_time = time.time()
    
    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record an HTTP request."""
        # Normalize path (remove IDs)
        normalized_path = self._normalize_path(path)
        
        self.request_count[(method, normalized_path, status_code)].inc()
        self.request_latency[(method, normalized_path)].observe(duration_seconds)
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing dynamic segments."""
        import re
        # Replace numeric IDs
        path = re.sub(r'/\d+', '/{id}', path)
        # Replace UUIDs
        path = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', path)
        return path
    
    def record_db_query(self, duration_seconds: float, error: bool = False) -> None:
        """Record a database query."""
        self.db_query_count.inc()
        self.db_query_latency.observe(duration_seconds)
        if error:
            self.db_error_count.inc()
    
    def record_error(self, error_type: str) -> None:
        """Record an error."""
        self.error_count[error_type].inc()
    
    def record_cache_access(self, hit: bool) -> None:
        """Record a cache access."""
        if hit:
            self.cache_hits.inc()
        else:
            self.cache_misses.inc()
    
    def get_metrics(self) -> dict[str, Any]:
        """Get all metrics as a dictionary."""
        uptime = time.time() - self._start_time
        
        # Request metrics
        request_counts = {}
        for (method, path, status), counter in self.request_count.items():
            key = f"{method}_{path}_{status}"
            request_counts[key] = counter.get()
        
        request_latencies = {}
        for (method, path), histogram in self.request_latency.items():
            key = f"{method}_{path}"
            if histogram.count > 0:
                request_latencies[key] = {
                    "count": histogram.count,
                    "avg_ms": round(histogram.total / histogram.count * 1000, 2),
                    "p50_ms": round((histogram.get_percentile(0.5) or 0) * 1000, 2),
                    "p95_ms": round((histogram.get_percentile(0.95) or 0) * 1000, 2),
                    "p99_ms": round((histogram.get_percentile(0.99) or 0) * 1000, 2),
                }
        
        # Cache hit rate
        cache_total = self.cache_hits.get() + self.cache_misses.get()
        cache_hit_rate = self.cache_hits.get() / cache_total if cache_total > 0 else 0
        
        return {
            "uptime_seconds": round(uptime, 2),
            "requests": {
                "counts": request_counts,
                "latencies": request_latencies,
                "active": self.active_requests.get(),
            },
            "database": {
                "query_count": self.db_query_count.get(),
                "error_count": self.db_error_count.get(),
                "avg_latency_ms": round(
                    self.db_query_latency.total / self.db_query_latency.count * 1000, 2
                ) if self.db_query_latency.count > 0 else 0,
            },
            "business": {
                "proposals_created": self.proposals_created.get(),
                "proposals_approved": self.proposals_approved.get(),
                "proposals_rejected": self.proposals_rejected.get(),
                "releases_created": self.releases_created.get(),
                "searches_performed": self.searches_performed.get(),
            },
            "cache": {
                "hits": self.cache_hits.get(),
                "misses": self.cache_misses.get(),
                "hit_rate": round(cache_hit_rate, 3),
            },
            "errors": {k: v.get() for k, v in self.error_count.items()},
        }
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        lines = []
        
        # Uptime
        uptime = time.time() - self._start_time
        lines.append("# HELP trs_uptime_seconds Total uptime in seconds")
        lines.append("# TYPE trs_uptime_seconds gauge")
        lines.append(f"trs_uptime_seconds {uptime:.2f}")
        
        # Request counts
        lines.append("# HELP trs_http_requests_total Total HTTP requests")
        lines.append("# TYPE trs_http_requests_total counter")
        for (method, path, status), counter in self.request_count.items():
            lines.append(
                f'trs_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {counter.get()}'
            )
        
        # Request latency
        lines.append("# HELP trs_http_request_duration_seconds HTTP request latency")
        lines.append("# TYPE trs_http_request_duration_seconds histogram")
        for (method, path), histogram in self.request_latency.items():
            for bucket, count in sorted(histogram.counts.items()):
                le = "+Inf" if bucket == float("inf") else str(bucket)
                lines.append(
                    f'trs_http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{le}"}} {count}'
                )
            lines.append(
                f'trs_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {histogram.total}'
            )
            lines.append(
                f'trs_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {histogram.count}'
            )
        
        # Business metrics
        lines.append("# HELP trs_proposals_total Total proposals by status")
        lines.append("# TYPE trs_proposals_total counter")
        lines.append(f'trs_proposals_total{{action="created"}} {self.proposals_created.get()}')
        lines.append(f'trs_proposals_total{{action="approved"}} {self.proposals_approved.get()}')
        lines.append(f'trs_proposals_total{{action="rejected"}} {self.proposals_rejected.get()}')
        
        lines.append(f"trs_releases_total {self.releases_created.get()}")
        lines.append(f"trs_searches_total {self.searches_performed.get()}")
        
        # Cache
        lines.append(f"trs_cache_hits_total {self.cache_hits.get()}")
        lines.append(f"trs_cache_misses_total {self.cache_misses.get()}")
        
        return "\n".join(lines) + "\n"


# Global metrics instance
metrics = MetricsCollector()


class track_request:
    """Context manager for tracking request metrics."""
    
    def __init__(self, method: str, path: str):
        self.method = method
        self.path = path
        self.start_time = None
        self.status_code = 200
    
    def __enter__(self):
        self.start_time = time.time()
        metrics.active_requests.inc()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        metrics.active_requests.dec()
        
        if exc_type:
            self.status_code = 500
        
        metrics.record_request(
            self.method,
            self.path,
            self.status_code,
            duration,
        )
        
        return False


class track_db_query:
    """Context manager for tracking database queries."""
    
    def __init__(self):
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        metrics.record_db_query(duration, error=exc_type is not None)
        return False
