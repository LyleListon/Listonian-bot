"""
Memory Optimization with Object Pooling

This module provides memory optimization through object pooling:
- Reusable object pools to reduce memory allocations
- Automatic cleanup of unused objects
- Thread-safe operations
"""

import time
import asyncio
import logging
import threading
# import weakref # Unused
from typing import (
    Dict,
    Any,
    Optional,
    List,
    Set,
    Tuple,
    # Union, # Unused
    TypeVar,
    Generic,
    Callable,
)
from collections import deque

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar("T")


class ObjectPool(Generic[T]):
    """
    Pool of reusable objects to reduce memory allocations.

    This class provides:
    - Object creation and reuse
    - Automatic cleanup of unused objects
    - Thread-safe operations
    """

    def __init__(
        self,
        factory: Callable[[], T],
        max_size: int = 100,
        ttl: float = 60.0,
        validation_func: Optional[Callable[[T], bool]] = None,
    ):
        """
        Initialize the object pool.

        Args:
            factory: Function to create new objects
            max_size: Maximum number of objects in the pool
            ttl: Time-to-live for unused objects (seconds)
            validation_func: Function to validate objects before reuse
        """
        self.factory = factory
        self.max_size = max_size
        self.ttl = ttl
        self.validation_func = validation_func

        # Pool of available objects
        self._available: List[Tuple[T, float]] = []
        self._in_use: Set[T] = set()
        self._lock = threading.RLock()

        # Statistics
        self._created = 0
        self._reused = 0
        self._discarded = 0

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.debug(f"ObjectPool initialized with max_size={max_size}")

    async def get(self) -> T:
        """
        Get an object from the pool.

        Returns:
            Object from the pool
        """
        with self._lock:
            # Check if we have available objects
            while self._available:
                obj, timestamp = self._available.pop()

                # Check if object is expired
                if time.time() - timestamp > self.ttl:
                    self._discarded += 1
                    continue

                # Validate object if needed
                if self.validation_func and not self.validation_func(obj):
                    self._discarded += 1
                    continue

                # Object is valid
                self._in_use.add(obj)
                self._reused += 1
                return obj

            # No available objects, create a new one
            obj = self.factory()
            self._in_use.add(obj)
            self._created += 1
            return obj

    def release(self, obj: T) -> None:
        """
        Release an object back to the pool.

        Args:
            obj: Object to release
        """
        with self._lock:
            # Remove from in-use set
            if obj in self._in_use:
                self._in_use.remove(obj)

            # Check if pool is full
            if len(self._available) >= self.max_size:
                # Discard oldest object
                self._available.pop(0)
                self._discarded += 1

            # Add to available pool
            self._available.append((obj, time.time()))

    async def _cleanup_loop(self) -> None:
        """Cleanup loop to remove expired objects."""
        while True:
            try:
                await asyncio.sleep(self.ttl / 2)

                with self._lock:
                    # Find expired objects
                    now = time.time()
                    expired = [
                        i
                        for i, (_, timestamp) in enumerate(self._available)
                        if now - timestamp > self.ttl
                    ]

                    # Remove expired objects (in reverse order to avoid index issues)
                    for i in reversed(expired):
                        self._available.pop(i)
                        self._discarded += 1

                    if expired:
                        logger.debug(
                            f"Removed {len(expired)} expired objects from pool"
                        )

            except asyncio.CancelledError:
                logger.debug("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        with self._lock:
            return {
                "available": len(self._available),
                "in_use": len(self._in_use),
                "created": self._created,
                "reused": self._reused,
                "discarded": self._discarded,
                "max_size": self.max_size,
                "ttl": self.ttl,
            }

    async def shutdown(self) -> None:
        """Shutdown the pool."""
        # Cancel cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clear pools
        with self._lock:
            self._available.clear()
            self._in_use.clear()

        logger.debug("ObjectPool shutdown")


class MemoryOptimizer:
    """
    Memory optimizer for efficient memory usage.

    This class provides:
    - Memory usage tracking
    - Garbage collection optimization
    - Memory pressure handling
    """

    def __init__(
        self,
        max_memory_percent: float = 80.0,
        gc_threshold: float = 70.0,
        check_interval: float = 5.0,
    ):
        """
        Initialize the memory optimizer.

        Args:
            max_memory_percent: Maximum memory usage percentage
            gc_threshold: Memory usage percentage to trigger garbage collection
            check_interval: Interval between memory checks (seconds)
        """
        self.max_memory_percent = max_memory_percent
        self.gc_threshold = gc_threshold
        self.check_interval = check_interval

        # Memory usage history
        self._memory_history = deque(maxlen=100)

        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None

        # Running flag
        self._running = False

        # Statistics
        self._gc_count = 0
        self._pressure_count = 0

        logger.debug("MemoryOptimizer initialized")

    async def start(self) -> None:
        """Start the memory optimizer."""
        if self._running:
            return

        self._running = True

        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_memory())

        logger.debug("MemoryOptimizer started")

    async def stop(self) -> None:
        """Stop the memory optimizer."""
        if not self._running:
            return

        self._running = False

        # Stop monitoring
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.debug("MemoryOptimizer stopped")

    async def _monitor_memory(self) -> None:
        """Monitor memory usage."""
        import psutil
        import gc

        process = psutil.Process()

        while self._running:
            try:
                # Get memory usage
                memory_percent = process.memory_percent()
                self._memory_history.append((time.time(), memory_percent))

                # Check if we need to trigger garbage collection
                if memory_percent > self.gc_threshold:
                    logger.debug(
                        f"Memory usage {memory_percent:.1f}% exceeds GC threshold {self.gc_threshold:.1f}%, triggering garbage collection"
                    )
                    gc.collect()
                    self._gc_count += 1

                # Check if we're under memory pressure
                if memory_percent > self.max_memory_percent:
                    logger.warning(f"High memory usage: {memory_percent:.1f}%")

                    # Trigger more aggressive garbage collection
                    gc.collect(2)

                    # Clear caches
                    # This is a placeholder - in a real implementation, you would
                    # clear application-specific caches here

                    self._pressure_count += 1

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.debug("Memory monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error monitoring memory: {e}")
                await asyncio.sleep(1.0)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory optimizer statistics.

        Returns:
            Dictionary with memory optimizer statistics
        """
        stats = {
            "running": self._running,
            "max_memory_percent": self.max_memory_percent,
            "gc_threshold": self.gc_threshold,
            "check_interval": self.check_interval,
            "gc_count": self._gc_count,
            "pressure_count": self._pressure_count,
            "current_memory_percent": None,
            "memory_history": [],
        }

        # Add memory history
        if self._memory_history:
            stats["memory_history"] = list(self._memory_history)
            stats["current_memory_percent"] = self._memory_history[-1][1]

        return stats
