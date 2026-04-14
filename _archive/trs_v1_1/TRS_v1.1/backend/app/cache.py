"""
TRS-505: API response caching.

Provides simple in-memory caching for expensive operations.

Usage:
    from backend.app.cache import cache, invalidate_cache
    
    @cache(ttl=300)  # Cache for 5 minutes
    def expensive_operation():
        ...
    
    invalidate_cache("expensive_operation")  # Clear specific cache
    invalidate_cache()  # Clear all caches
"""

from __future__ import annotations
import functools
import hashlib
import json
import time
from typing import Any, Callable, Optional

# Simple in-memory cache
_cache: dict[str, tuple[float, Any]] = {}
_cache_stats = {
    "hits": 0,
    "misses": 0,
}


def cache(ttl: int = 300, key_prefix: Optional[str] = None):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time-to-live in seconds (default 5 minutes)
        key_prefix: Optional prefix for cache key
    
    Example:
        @cache(ttl=60)
        def get_registry():
            return load_registry()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            prefix = key_prefix or func.__name__
            
            # Hash arguments for key
            key_data = json.dumps({
                "args": [str(a) for a in args],
                "kwargs": {k: str(v) for k, v in sorted(kwargs.items())},
            }, sort_keys=True)
            key_hash = hashlib.md5(key_data.encode()).hexdigest()[:12]
            cache_key = f"{prefix}:{key_hash}"
            
            # Check cache
            if cache_key in _cache:
                expires, value = _cache[cache_key]
                if time.time() < expires:
                    _cache_stats["hits"] += 1
                    return value
                else:
                    # Expired
                    del _cache[cache_key]
            
            # Cache miss
            _cache_stats["misses"] += 1
            result = func(*args, **kwargs)
            
            # Store in cache
            _cache[cache_key] = (time.time() + ttl, result)
            
            return result
        
        # Add cache control methods
        wrapper.invalidate = lambda: invalidate_cache(key_prefix or func.__name__)
        wrapper.cache_key_prefix = key_prefix or func.__name__
        
        return wrapper
    return decorator


def invalidate_cache(prefix: Optional[str] = None) -> int:
    """
    Invalidate cache entries.
    
    Args:
        prefix: If provided, only invalidate keys with this prefix.
                If None, invalidate all entries.
    
    Returns:
        Number of entries invalidated.
    """
    global _cache
    
    if prefix is None:
        count = len(_cache)
        _cache = {}
        return count
    
    keys_to_delete = [k for k in _cache if k.startswith(f"{prefix}:")]
    for key in keys_to_delete:
        del _cache[key]
    
    return len(keys_to_delete)


def get_cache_stats() -> dict:
    """Get cache statistics."""
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = _cache_stats["hits"] / total if total > 0 else 0
    
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "hit_rate": round(hit_rate, 3),
        "entries": len(_cache),
        "size_estimate": sum(len(str(v)) for _, v in _cache.values()),
    }


def reset_cache_stats() -> None:
    """Reset cache statistics."""
    _cache_stats["hits"] = 0
    _cache_stats["misses"] = 0


# ============================================================================
# Registry-specific caching
# ============================================================================

_registry_cache: dict[str, tuple[float, dict]] = {}
_registry_cache_ttl = 60  # 1 minute


def get_cached_registry(loader_fn: Callable, registry_dir) -> dict:
    """
    Get registry with caching.
    
    Args:
        loader_fn: Function to load registry
        registry_dir: Registry directory path (used as cache key)
    """
    cache_key = str(registry_dir)
    now = time.time()
    
    if cache_key in _registry_cache:
        expires, data = _registry_cache[cache_key]
        if now < expires:
            return data
    
    # Load fresh
    data = loader_fn(registry_dir)
    _registry_cache[cache_key] = (now + _registry_cache_ttl, data)
    
    return data


def invalidate_registry_cache() -> None:
    """Invalidate all registry caches."""
    global _registry_cache
    _registry_cache = {}


# ============================================================================
# FastAPI middleware helper
# ============================================================================

class CacheMiddleware:
    """
    Simple response caching for FastAPI.
    
    Usage:
        from backend.app.cache import CacheMiddleware
        
        # In main.py:
        cache_middleware = CacheMiddleware(ttl=60)
        
        @app.get("/registry")
        async def get_registry():
            return cache_middleware.get_or_set(
                "registry",
                lambda: load_registry()
            )
    """
    
    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        self.cache: dict[str, tuple[float, Any]] = {}
    
    def get_or_set(self, key: str, factory: Callable) -> Any:
        """Get from cache or compute and store."""
        now = time.time()
        
        if key in self.cache:
            expires, value = self.cache[key]
            if now < expires:
                return value
        
        value = factory()
        self.cache[key] = (now + self.ttl, value)
        return value
    
    def invalidate(self, key: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        if key is None:
            self.cache = {}
        elif key in self.cache:
            del self.cache[key]
    
    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "entries": len(self.cache),
            "keys": list(self.cache.keys()),
        }
