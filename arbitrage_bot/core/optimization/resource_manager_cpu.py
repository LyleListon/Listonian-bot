"""
CPU Optimization with Work Stealing

This module provides CPU optimization through work stealing:
- Priority-based task scheduling
- Work stealing for better CPU utilization
- Adaptive throttling based on system load
"""

import os
import time
import asyncio
import logging
import psutil
from typing import (
    Dict,
    Any,
    Optional,
    List,
    # Set, # Unused
    Tuple,
    # Union, # Unused
    TypeVar,
    Generic,
    Callable,
    Awaitable,
)
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Type definitions
T = TypeVar("T")


class TaskPriority(int, Enum):
    """Priority levels for tasks."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class ResourceType(str, Enum):
    """Types of resources."""

    MEMORY = "memory"
    CPU = "cpu"
    IO = "io"
    NETWORK = "network"
    CUSTOM = "custom"


@dataclass
class Task(Generic[T]):
    """Task with metadata."""

    func: Callable[..., Awaitable[T]]
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    resource_type: ResourceType = ResourceType.CPU
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: f"{time.time():.6f}")
    timeout: Optional[float] = None
    retries: int = 0
    max_retries: int = 3
    retry_delay: float = 1.0
    result: Optional[T] = None
    error: Optional[Exception] = None
    done: bool = False
    cancelled: bool = False


class WorkStealingExecutor:
    """
    Work stealing executor for better CPU utilization.

    This class provides:
    - Priority-based task scheduling
    - Work stealing for better CPU utilization
    - Adaptive throttling based on system load
    """

    def __init__(
        self,
        num_workers: int = None,
        max_tasks_per_worker: int = 100,
        steal_threshold: int = 5,
        max_cpu_percent: float = 80.0,
        throttle_threshold: float = 90.0,
    ):
        """
        Initialize the work stealing executor.

        Args:
            num_workers: Number of worker threads (default: number of CPU cores)
            max_tasks_per_worker: Maximum number of tasks per worker
            steal_threshold: Minimum number of tasks to steal
            max_cpu_percent: Maximum CPU usage percentage
            throttle_threshold: CPU usage percentage to start throttling
        """
        self.num_workers = num_workers or os.cpu_count() or 4
        self.max_tasks_per_worker = max_tasks_per_worker
        self.steal_threshold = steal_threshold
        self.max_cpu_percent = max_cpu_percent
        self.throttle_threshold = throttle_threshold

        # Task queues for each worker
        self._queues: List[asyncio.PriorityQueue] = [
            asyncio.PriorityQueue(max_tasks_per_worker) for _ in range(self.num_workers)
        ]

        # Worker tasks
        self._workers: List[asyncio.Task] = []

        # Worker locks
        self._locks: List[asyncio.Lock] = [
            asyncio.Lock() for _ in range(self.num_workers)
        ]

        # Running flag
        self._running = False

        # Statistics
        self._completed_tasks = 0
        self._failed_tasks = 0
        self._stolen_tasks = 0
        self._throttled_count = 0

        # Process for CPU monitoring
        self._process = psutil.Process()

        logger.debug(
            f"WorkStealingExecutor initialized with {self.num_workers} workers"
        )

    async def start(self) -> None:
        """Start the executor."""
        if self._running:
            return

        self._running = True

        # Start workers
        for i in range(self.num_workers):
            self._workers.append(asyncio.create_task(self._worker_loop(i)))

        logger.debug(f"Started {self.num_workers} workers")

    async def stop(self) -> None:
        """Stop the executor."""
        if not self._running:
            return

        self._running = False

        # Cancel workers
        for worker in self._workers:
            if not worker.done():
                worker.cancel()

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

        self._workers.clear()

        logger.debug("WorkStealingExecutor stopped")

    async def submit(self, task: Task) -> None:
        """
        Submit a task for execution.

        Args:
            task: Task to execute
        """
        if not self._running:
            await self.start()

        # Find worker with shortest queue
        worker_id = min(range(self.num_workers), key=lambda i: self._queues[i].qsize())

        # Add task to queue
        await self._queues[worker_id].put((task.priority, task))

        logger.debug(f"Submitted task {task.id} to worker {worker_id}")

    async def _worker_loop(self, worker_id: int) -> None:
        """
        Worker loop.

        Args:
            worker_id: Worker ID
        """
        queue = self._queues[worker_id]

        while self._running:
            try:
                # Check CPU usage
                cpu_percent = self._process.cpu_percent()
                if cpu_percent > self.throttle_threshold:
                    # Throttle execution
                    self._throttled_count += 1
                    await asyncio.sleep(0.1)
                    continue

                # Try to get a task from our queue
                try:
                    priority, task = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    # No task in our queue, try to steal from others
                    stolen_task = await self._steal_task(worker_id)
                    if stolen_task:
                        task = stolen_task
                    else:
                        # No tasks to steal, wait a bit
                        await asyncio.sleep(0.01)
                        continue

                # Execute task
                try:
                    if task.timeout:
                        # Execute with timeout
                        task.result = await asyncio.wait_for(
                            task.func(*task.args, **task.kwargs), timeout=task.timeout
                        )
                    else:
                        # Execute without timeout
                        task.result = await task.func(*task.args, **task.kwargs)

                    task.done = True
                    self._completed_tasks += 1

                except asyncio.TimeoutError:
                    # Task timed out
                    task.error = asyncio.TimeoutError(
                        f"Task {task.id} timed out after {task.timeout} seconds"
                    )
                    self._failed_tasks += 1

                    # Retry if needed
                    if task.retries < task.max_retries:
                        task.retries += 1
                        await asyncio.sleep(task.retry_delay)
                        await self.submit(task)
                    else:
                        task.done = True

                except Exception as e:
                    # Task failed
                    task.error = e
                    self._failed_tasks += 1

                    # Retry if needed
                    if task.retries < task.max_retries:
                        task.retries += 1
                        await asyncio.sleep(task.retry_delay)
                        await self.submit(task)
                    else:
                        task.done = True
                        logger.error(
                            f"Task {task.id} failed after {task.retries} retries: {e}"
                        )

                finally:
                    # Mark task as done in the queue
                    queue.task_done()

            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"Error in worker {worker_id}: {e}")
                await asyncio.sleep(0.1)

    async def _steal_task(self, worker_id: int) -> Optional[Task]:
        """
        Steal a task from another worker.

        Args:
            worker_id: Worker ID

        Returns:
            Stolen task or None if no tasks to steal
        """
        # Find worker with longest queue
        other_workers = [i for i in range(self.num_workers) if i != worker_id]
        if not other_workers:
            return None

        victim_id = max(other_workers, key=lambda i: self._queues[i].qsize())
        victim_queue = self._queues[victim_id]

        # Check if victim has enough tasks to steal
        if victim_queue.qsize() <= self.steal_threshold:
            return None

        # Try to acquire lock on victim's queue
        if not await self._try_lock(victim_id):
            return None

        try:
            # Steal a task
            if not victim_queue.empty():
                priority, task = await victim_queue.get()
                victim_queue.task_done()
                self._stolen_tasks += 1
                logger.debug(
                    f"Worker {worker_id} stole task {task.id} from worker {victim_id}"
                )
                return task
        finally:
            # Release lock
            self._locks[victim_id].release()

        return None

    async def _try_lock(self, worker_id: int) -> bool:
        """
        Try to acquire lock on worker's queue.

        Args:
            worker_id: Worker ID

        Returns:
            True if lock acquired, False otherwise
        """
        try:
            return await asyncio.wait_for(
                self._locks[worker_id].acquire(), timeout=0.01
            )
        except asyncio.TimeoutError:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get executor statistics.

        Returns:
            Dictionary with executor statistics
        """
        queue_sizes = [queue.qsize() for queue in self._queues]
        return {
            "workers": self.num_workers,
            "running": self._running,
            "completed_tasks": self._completed_tasks,
            "failed_tasks": self._failed_tasks,
            "stolen_tasks": self._stolen_tasks,
            "throttled_count": self._throttled_count,
            "queue_sizes": queue_sizes,
            "total_queued": sum(queue_sizes),
            "max_tasks_per_worker": self.max_tasks_per_worker,
            "steal_threshold": self.steal_threshold,
            "max_cpu_percent": self.max_cpu_percent,
            "throttle_threshold": self.throttle_threshold,
        }


class CPUOptimizer:
    """
    CPU optimizer for efficient CPU usage.

    This class provides:
    - CPU usage tracking
    - Adaptive throttling based on system load
    - Priority-based task scheduling
    """

    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        throttle_threshold: float = 70.0,
        check_interval: float = 1.0,
    ):
        """
        Initialize the CPU optimizer.

        Args:
            max_cpu_percent: Maximum CPU usage percentage
            throttle_threshold: CPU usage percentage to start throttling
            check_interval: Interval between CPU checks (seconds)
        """
        self.max_cpu_percent = max_cpu_percent
        self.throttle_threshold = throttle_threshold
        self.check_interval = check_interval

        # CPU usage history
        self._cpu_history = []

        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None

        # Running flag
        self._running = False

        # Throttling state
        self._throttling = False
        self._throttle_factor = 1.0

        # Statistics
        self._throttle_count = 0

        logger.debug("CPUOptimizer initialized")

    async def start(self) -> None:
        """Start the CPU optimizer."""
        if self._running:
            return

        self._running = True

        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_cpu())

        logger.debug("CPUOptimizer started")

    async def stop(self) -> None:
        """Stop the CPU optimizer."""
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

        logger.debug("CPUOptimizer stopped")

    async def should_throttle(self) -> Tuple[bool, float]:
        """
        Check if execution should be throttled.

        Returns:
            Tuple of (should_throttle, throttle_factor)
        """
        return self._throttling, self._throttle_factor

    async def _monitor_cpu(self) -> None:
        """Monitor CPU usage."""
        process = psutil.Process()

        while self._running:
            try:
                # Get CPU usage
                cpu_percent = process.cpu_percent()
                self._cpu_history.append((time.time(), cpu_percent))

                # Limit history size
                if len(self._cpu_history) > 100:
                    self._cpu_history = self._cpu_history[-100:]

                # Check if we need to throttle
                if cpu_percent > self.throttle_threshold:
                    # Calculate throttle factor based on how much we exceed the threshold
                    excess = (cpu_percent - self.throttle_threshold) / (
                        self.max_cpu_percent - self.throttle_threshold
                    )
                    self._throttle_factor = max(0.1, 1.0 - excess)

                    if not self._throttling:
                        logger.debug(
                            f"CPU usage {cpu_percent:.1f}% exceeds throttle threshold {self.throttle_threshold:.1f}%, throttling execution (factor: {self._throttle_factor:.2f})"
                        )
                        self._throttling = True
                        self._throttle_count += 1
                else:
                    # No need to throttle
                    self._throttling = False
                    self._throttle_factor = 1.0

                # Wait before next check
                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.debug("CPU monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error monitoring CPU: {e}")
                await asyncio.sleep(1.0)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get CPU optimizer statistics.

        Returns:
            Dictionary with CPU optimizer statistics
        """
        stats = {
            "running": self._running,
            "max_cpu_percent": self.max_cpu_percent,
            "throttle_threshold": self.throttle_threshold,
            "check_interval": self.check_interval,
            "throttling": self._throttling,
            "throttle_factor": self._throttle_factor,
            "throttle_count": self._throttle_count,
            "current_cpu_percent": None,
            "cpu_history": self._cpu_history,
        }

        # Add current CPU usage
        if self._cpu_history:
            stats["current_cpu_percent"] = self._cpu_history[-1][1]

        return stats
