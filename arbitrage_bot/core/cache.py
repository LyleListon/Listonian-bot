"""
In-memory cache with TTL support.

This module provides:
1. Thread-safe caching
2. TTL-based expiration
3. Performance metrics
4. Auto cleanup
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


class Cache:
    """Thread-safe cache with TTL support."""

    def __init__(self):
        """Initialize the cache."""
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._active = False

        # Performance metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._total_set_time = 0.0
        self._total_get_time = 0.0
        self._total_sets = 0
        self._total_gets = 0
        self._start_time = datetime.utcnow()

    async def start_cleanup_task(self) -> None:
        """Start the cleanup task."""
        async with self._lock:
            if not self._active:
                self._active = True
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                logger.info("Cache cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop the cleanup task."""
        async with self._lock:
            if self._active:
                self._active = False
                if self._cleanup_task:
                    self._cleanup_task.cancel()
                    try:
                        await self._cleanup_task
                    except asyncio.CancelledError:
                        pass
                    self._cleanup_task = None
                logger.info("Cache cleanup task stopped")

    async def set(self, key: str, value: Any, expire: int = 0) -> None:
        """Set a cache value with optional TTL."""
        start_time = time.perf_counter()
        try:
            async with self._lock:
                if expire > 0:
                    expiry = time.time() + expire
                else:
                    expiry = float("inf")
                self._cache[key] = (value, expiry)
                self._total_sets += 1
        finally:
            self._total_set_time += time.perf_counter() - start_time

    async def get(self, key: str) -> Optional[Any]:
        """Get a cache value."""
        start_time = time.perf_counter()
        try:
            async with self._lock:
                self._total_gets += 1
                if key not in self._cache:
                    self._misses += 1
                    return None

                value, expiry = self._cache[key]
                if time.time() > expiry:
                    del self._cache[key]
                    self._evictions += 1
                    self._misses += 1
                    return None

                self._hits += 1
                return value
        finally:
            self._total_get_time += time.perf_counter() - start_time

    async def delete(self, key: str) -> bool:
        """Delete a cache value."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        async with self._lock:
            total_ops = self._hits + self._misses
            avg_get_time = (
                self._total_get_time / self._total_gets if self._total_gets > 0 else 0
            )
            avg_set_time = (
                self._total_set_time / self._total_sets if self._total_sets > 0 else 0
            )

            uptime = datetime.utcnow() - self._start_time
            ops_per_second = (
                total_ops / uptime.total_seconds() if uptime.total_seconds() > 0 else 0
            )

            return {
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": (self._hits / total_ops * 100) if total_ops > 0 else 0,
                "evictions": self._evictions,
                "total_operations": total_ops,
                "operations_per_second": ops_per_second,
                "average_get_time_ms": avg_get_time * 1000,
                "average_set_time_ms": avg_set_time * 1000,
                "total_items": len(self._cache),
                "uptime": str(uptime),
            }

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired entries."""
        while self._active:
            try:
                now = time.time()
                async with self._lock:
                    # Find expired keys
                    expired_keys = [
                        key for key, (_, expiry) in self._cache.items() if now > expiry
                    ]

                    # Remove expired keys
                    for key in expired_keys:
                        del self._cache[key]
                        self._evictions += 1

                    if expired_keys:
                        logger.debug(
                            f"Cleaned up {len(expired_keys)} expired cache entries"
                        )

                await asyncio.sleep(60)  # Run cleanup every minute

            except Exception as e:
                logger.error(f"Error in cache cleanup loop: {e}")
                await asyncio.sleep(300)  # Wait longer on error

    async def __aenter__(self) -> "Cache":
        """Async context manager entry."""
        await self.start_cleanup_task()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop_cleanup_task()


# Singleton instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get the cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
