"""
Core caching module.

This module provides:
1. In-memory caching with TTL
2. Distributed cache support
3. Cache invalidation
"""

import os
import time
import asyncio
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Cache:
    """Async cache implementation."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            if entry['expire'] and entry['expire'] < time.time():
                del self._cache[key]
                return None
            
            return entry['value']
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
        """Set value in cache with optional expiration in seconds."""
        async with self._lock:
            self._cache[key] = {
                'value': value,
                'expire': time.time() + expire if expire else None
            }
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup(self) -> None:
        """Remove expired entries."""
        async with self._lock:
            now = time.time()
            expired = [
                key for key, entry in self._cache.items()
                if entry['expire'] and entry['expire'] < now
            ]
            for key in expired:
                del self._cache[key]

_cache: Optional[Cache] = None

async def get_cache() -> Cache:
    """Get the cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache

# Start background cleanup task
async def start_cleanup_task():
    """Start periodic cache cleanup."""
    cache = await get_cache()
    while True:
        await asyncio.sleep(300)  # Clean every 5 minutes
        await cache.cleanup()

# Create cleanup task when module is imported
asyncio.create_task(start_cleanup_task())