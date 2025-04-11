"""
Resource Management for Improved Performance

This module provides optimizations for system resources:
- Memory optimization with object pooling
- CPU optimization with work stealing
- I/O optimization with batched operations
"""

import os
import gc
import time
import asyncio
import logging
# import threading # Unused
import psutil
# import weakref # Unused
from typing import (
    Dict,
    Any,
    Optional,
    List, # Keep List
    # Set, # Unused
    # Tuple, # Unused
    Union,
    TypeVar,
    # Generic, # Unused
    Callable,
    Awaitable,
)
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
# from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor # Unused
# from functools import partial # Unused

from .resource_manager_memory import ObjectPool

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar("T")
U = TypeVar("U")


class ResourceType(str, Enum):
    """Types of resources."""

    MEMORY = "memory"
    CPU = "cpu"
    IO = "io"
    NETWORK = "network"
    CUSTOM = "custom"


class TaskPriority(int, Enum):
    """Priority levels for tasks."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class ResourceUsage:
    """Resource usage information."""

    memory_percent: float = 0.0
    cpu_percent: float = 0.0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    network_recv_bytes: int = 0
    network_sent_bytes: int = 0
    timestamp: float = field(default_factory=time.time)


class ResourceManager:
    """
    Resource manager for optimizing system resources.

    This class provides:
    - Memory optimization with object pooling
    - CPU optimization with work stealing
    - I/O optimization with batched operations
    """

    def __init__(
        self,
        num_workers: int = None,
        max_cpu_percent: float = 80.0,
        max_memory_percent: float = 80.0,
        max_io_workers: int = 4,
        max_batch_size: int = 100,
        batch_interval: float = 0.1,
    ):
        """
        Initialize the resource manager.

        Args:
            num_workers: Number of worker threads (default: number of CPU cores)
            max_cpu_percent: Maximum CPU usage percentage
            max_memory_percent: Maximum memory usage percentage
            max_io_workers: Maximum number of I/O worker threads
            max_batch_size: Maximum number of operations in a batch
            batch_interval: Maximum time to wait before processing a batch (seconds)
        """
        self.num_workers = num_workers or os.cpu_count() or 4
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_percent = max_memory_percent
        self.max_io_workers = max_io_workers
        self.max_batch_size = max_batch_size
        self.batch_interval = batch_interval

        # Object pools
        self._object_pools: Dict[str, ObjectPool] = {}

        # Work stealing executor
        self._executor = None

        # Batched I/O manager
        self._io_manager = None

        # Process for resource monitoring
        self._process = psutil.Process()

        # Resource usage history
        self._resource_history: deque[ResourceUsage] = deque(maxlen=100)

        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None

        # Running flag
        self._running = False

        logger.debug("ResourceManager initialized")

    async def start(self) -> None:
        """Start the resource manager."""
        if self._running:
            return

        self._running = True

        # Create executor
        from .resource_manager_cpu import WorkStealingExecutor

        self._executor = WorkStealingExecutor(
            num_workers=self.num_workers, max_cpu_percent=self.max_cpu_percent
        )

        # Create I/O manager
        from .resource_manager_io import BatchedIOManager

        self._io_manager = BatchedIOManager(
            max_batch_size=self.max_batch_size,
            batch_interval=self.batch_interval,
            max_workers=self.max_io_workers,
        )

        # Start components
        await self._executor.start()
        await self._io_manager.start()

        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_resources())

        logger.debug("ResourceManager started")

    async def stop(self) -> None:
        """Stop the resource manager."""
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

        # Stop components
        if self._executor:
            await self._executor.stop()

        if self._io_manager:
            await self._io_manager.stop()

        # Shutdown object pools
        for pool in self._object_pools.values():
            await pool.shutdown()

        logger.debug("ResourceManager stopped")

    async def create_object_pool(
        self,
        name: str,
        factory: Callable[[], T],
        max_size: int = 100,
        ttl: float = 60.0,
        validation_func: Optional[Callable[[T], bool]] = None,
    ) -> None:
        """
        Create an object pool.

        Args:
            name: Pool name
            factory: Function to create new objects
            max_size: Maximum number of objects in the pool
            ttl: Time-to-live for unused objects (seconds)
            validation_func: Function to validate objects before reuse
        """
        from .resource_manager_memory import ObjectPool

        if name in self._object_pools:
            raise ValueError(f"Object pool '{name}' already exists")

        pool = ObjectPool(
            factory=factory, max_size=max_size, ttl=ttl, validation_func=validation_func
        )

        self._object_pools[name] = pool

        logger.debug(f"Created object pool '{name}' with max_size={max_size}")

    async def get_object(self, pool_name: str) -> T:
        """
        Get an object from a pool.

        Args:
            pool_name: Pool name

        Returns:
            Object from the pool

        Raises:
            ValueError: If the pool doesn't exist
        """
        if pool_name not in self._object_pools:
            raise ValueError(f"Object pool '{pool_name}' doesn't exist")

        return await self._object_pools[pool_name].get()

    def release_object(self, pool_name: str, obj: T) -> None:
        """
        Release an object back to a pool.

        Args:
            pool_name: Pool name
            obj: Object to release

        Raises:
            ValueError: If the pool doesn't exist
        """
        if pool_name not in self._object_pools:
            raise ValueError(f"Object pool '{pool_name}' doesn't exist")

        self._object_pools[pool_name].release(obj)

    async def submit_task(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        resource_type: ResourceType = ResourceType.CPU,
        timeout: Optional[float] = None,
        retries: int = 0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        **kwargs,
    ) -> T:
        """
        Submit a task for execution.

        Args:
            func: Async function to execute
            *args: Function arguments
            priority: Task priority
            resource_type: Resource type
            timeout: Task timeout (seconds)
            retries: Number of retries
            max_retries: Maximum number of retries
            retry_delay: Delay between retries (seconds)
            **kwargs: Function keyword arguments

        Returns:
            Task result
        """
        if not self._running:
            await self.start()

        # Create task
        from .resource_manager_cpu import Task

        task = Task(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            resource_type=resource_type,
            timeout=timeout,
            retries=retries,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

        # Submit task
        await self._executor.submit(task)

        # Wait for task to complete
        while not task.done:
            await asyncio.sleep(0.01)

        # Check for error
        if task.error:
            raise task.error

        return task.result

    async def read_file(
        self,
        path: str,
        binary: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> Union[str, bytes]:
        """
        Read a file asynchronously.

        Args:
            path: File path
            binary: Whether to read in binary mode
            priority: Operation priority

        Returns:
            File contents
        """
        if not self._running:
            await self.start()

        return await self._io_manager.read_file(path, binary, priority)

    async def write_file(
        self,
        path: str,
        data: Union[str, bytes],
        binary: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> int:
        """
        Write to a file asynchronously.

        Args:
            path: File path
            data: Data to write
            binary: Whether to write in binary mode
            priority: Operation priority

        Returns:
            Number of bytes written
        """
        if not self._running:
            await self.start()

        return await self._io_manager.write_file(path, data, binary, priority)

    async def get_resource_usage(self) -> ResourceUsage:
        """
        Get current resource usage.

        Returns:
            Resource usage information
        """
        try:
            # Get CPU and memory usage
            cpu_percent = self._process.cpu_percent()
            memory_percent = self._process.memory_percent()

            # Get I/O stats
            io_counters = self._process.io_counters()
            io_read_bytes = io_counters.read_bytes if io_counters else 0
            io_write_bytes = io_counters.write_bytes if io_counters else 0

            # Get network stats
            net_io_counters = psutil.net_io_counters()
            network_recv_bytes = net_io_counters.bytes_recv if net_io_counters else 0
            network_sent_bytes = net_io_counters.bytes_sent if net_io_counters else 0

            # Create resource usage
            usage = ResourceUsage(
                memory_percent=memory_percent,
                cpu_percent=cpu_percent,
                io_read_bytes=io_read_bytes,
                io_write_bytes=io_write_bytes,
                network_recv_bytes=network_recv_bytes,
                network_sent_bytes=network_sent_bytes,
            )

            # Add to history
            self._resource_history.append(usage)

            return usage

        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return ResourceUsage()

    async def _monitor_resources(self) -> None:
        """Monitor system resources."""
        while self._running:
            try:
                # Get resource usage
                usage = await self.get_resource_usage()

                # Check memory usage
                if usage.memory_percent > self.max_memory_percent:
                    logger.warning(f"High memory usage: {usage.memory_percent:.1f}%")

                    # Force garbage collection
                    gc.collect()

                # Check CPU usage
                if usage.cpu_percent > self.max_cpu_percent:
                    logger.warning(f"High CPU usage: {usage.cpu_percent:.1f}%")

                # Wait before next check
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                logger.debug("Resource monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                await asyncio.sleep(1.0)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get resource manager statistics.

        Returns:
            Dictionary with resource manager statistics
        """
        stats = {
            "running": self._running,
            "num_workers": self.num_workers,
            "max_cpu_percent": self.max_cpu_percent,
            "max_memory_percent": self.max_memory_percent,
            "max_io_workers": self.max_io_workers,
            "max_batch_size": self.max_batch_size,
            "batch_interval": self.batch_interval,
            "object_pools": {},
            "executor": None,
            "io_manager": None,
            "resource_usage": None,
        }

        # Add object pool stats
        for name, pool in self._object_pools.items():
            stats["object_pools"][name] = pool.get_stats()

        # Add executor stats
        if self._executor:
            stats["executor"] = self._executor.get_stats()

        # Add I/O manager stats
        if self._io_manager:
            stats["io_manager"] = self._io_manager.get_stats()

        # Add resource usage
        if self._resource_history:
            latest = self._resource_history[-1]
            stats["resource_usage"] = {
                "memory_percent": latest.memory_percent,
                "cpu_percent": latest.cpu_percent,
                "io_read_bytes": latest.io_read_bytes,
                "io_write_bytes": latest.io_write_bytes,
                "network_recv_bytes": latest.network_recv_bytes,
                "network_sent_bytes": latest.network_sent_bytes,
                "timestamp": latest.timestamp,
            }

        return stats
