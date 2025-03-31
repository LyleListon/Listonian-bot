"""
I/O Optimization with Batched Operations

This module provides I/O optimization through batched operations:
- Batched file operations
- Asynchronous file I/O
- I/O prioritization
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Set, Tuple, Union, Callable, Awaitable
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class TaskPriority(int, Enum):
    """Priority levels for tasks."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

class BatchedIOManager:
    """
    Batched I/O operations for better I/O performance.
    
    This class provides:
    - Batched file operations
    - Asynchronous file I/O
    - I/O prioritization
    """
    
    def __init__(
        self,
        max_batch_size: int = 100,
        batch_interval: float = 0.1,
        max_workers: int = 4,
        max_queue_size: int = 1000
    ):
        """
        Initialize the batched I/O manager.
        
        Args:
            max_batch_size: Maximum number of operations in a batch
            batch_interval: Maximum time to wait before processing a batch (seconds)
            max_workers: Maximum number of worker threads
            max_queue_size: Maximum number of operations in the queue
        """
        self.max_batch_size = max_batch_size
        self.batch_interval = batch_interval
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        
        # Thread pool for blocking I/O operations
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Operation queues
        self._read_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(max_queue_size)
        self._write_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(max_queue_size)
        
        # Running flag
        self._running = False
        
        # Batch processing tasks
        self._read_task: Optional[asyncio.Task] = None
        self._write_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._read_ops = 0
        self._write_ops = 0
        self._read_bytes = 0
        self._write_bytes = 0
        self._read_batches = 0
        self._write_batches = 0
        
        logger.debug(f"BatchedIOManager initialized with max_batch_size={max_batch_size}")
    
    async def start(self) -> None:
        """Start the I/O manager."""
        if self._running:
            return
        
        self._running = True
        
        # Start batch processing tasks
        self._read_task = asyncio.create_task(self._process_read_queue())
        self._write_task = asyncio.create_task(self._process_write_queue())
        
        logger.debug("BatchedIOManager started")
    
    async def stop(self) -> None:
        """Stop the I/O manager."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel batch processing tasks
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        
        if self._write_task and not self._write_task.done():
            self._write_task.cancel()
            try:
                await self._write_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown executor
        self._executor.shutdown(wait=False)
        
        logger.debug("BatchedIOManager stopped")
    
    async def read_file(
        self,
        path: str,
        binary: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL
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
        
        # Create future for result
        future = asyncio.Future()
        
        # Add to read queue
        await self._read_queue.put((priority, (path, binary, future)))
        
        # Wait for result
        return await future
    
    async def write_file(
        self,
        path: str,
        data: Union[str, bytes],
        binary: bool = False,
        priority: TaskPriority = TaskPriority.NORMAL
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
        
        # Create future for result
        future = asyncio.Future()
        
        # Add to write queue
        await self._write_queue.put((priority, (path, data, binary, future)))
        
        # Wait for result
        return await future
    
    async def _process_read_queue(self) -> None:
        """Process the read queue."""
        last_batch_time = time.time()
        
        while self._running:
            try:
                # Check if we should process a batch
                now = time.time()
                time_since_last_batch = now - last_batch_time
                should_process_batch = (
                    self._read_queue.qsize() >= self.max_batch_size or
                    (not self._read_queue.empty() and time_since_last_batch >= self.batch_interval)
                )
                
                if should_process_batch:
                    # Process batch
                    batch = []
                    batch_size = min(self.max_batch_size, self._read_queue.qsize())
                    
                    for _ in range(batch_size):
                        if self._read_queue.empty():
                            break
                        
                        priority, (path, binary, future) = await self._read_queue.get()
                        batch.append((path, binary, future))
                        self._read_queue.task_done()
                    
                    if batch:
                        # Process batch in executor
                        asyncio.create_task(self._execute_read_batch(batch))
                        self._read_batches += 1
                        last_batch_time = time.time()
                else:
                    # Wait a bit
                    await asyncio.sleep(0.01)
                    
            except asyncio.CancelledError:
                logger.debug("Read queue processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing read queue: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_write_queue(self) -> None:
        """Process the write queue."""
        last_batch_time = time.time()
        
        while self._running:
            try:
                # Check if we should process a batch
                now = time.time()
                time_since_last_batch = now - last_batch_time
                should_process_batch = (
                    self._write_queue.qsize() >= self.max_batch_size or
                    (not self._write_queue.empty() and time_since_last_batch >= self.batch_interval)
                )
                
                if should_process_batch:
                    # Process batch
                    batch = []
                    batch_size = min(self.max_batch_size, self._write_queue.qsize())
                    
                    for _ in range(batch_size):
                        if self._write_queue.empty():
                            break
                        
                        priority, (path, data, binary, future) = await self._write_queue.get()
                        batch.append((path, data, binary, future))
                        self._write_queue.task_done()
                    
                    if batch:
                        # Process batch in executor
                        asyncio.create_task(self._execute_write_batch(batch))
                        self._write_batches += 1
                        last_batch_time = time.time()
                else:
                    # Wait a bit
                    await asyncio.sleep(0.01)
                    
            except asyncio.CancelledError:
                logger.debug("Write queue processing cancelled")
                break
            except Exception as e:
                logger.error(f"Error processing write queue: {e}")
                await asyncio.sleep(0.1)
    
    async def _execute_read_batch(self, batch: List[Tuple[str, bool, asyncio.Future]]) -> None:
        """
        Execute a batch of read operations.
        
        Args:
            batch: List of (path, binary, future) tuples
        """
        # Group by directory to improve cache locality
        by_directory = {}
        for path, binary, future in batch:
            directory = os.path.dirname(path)
            if directory not in by_directory:
                by_directory[directory] = []
            by_directory[directory].append((path, binary, future))
        
        # Process each directory group
        for directory, items in by_directory.items():
            # Process items in group
            for path, binary, future in items:
                try:
                    # Execute in thread pool
                    mode = "rb" if binary else "r"
                    result = await asyncio.to_thread(self._read_file_sync, path, mode)
                    
                    # Set result
                    if not future.done():
                        future.set_result(result)
                    
                    # Update statistics
                    self._read_ops += 1
                    self._read_bytes += len(result)
                    
                except Exception as e:
                    # Set exception
                    if not future.done():
                        future.set_exception(e)
                    
                    logger.error(f"Error reading file {path}: {e}")
    
    async def _execute_write_batch(self, batch: List[Tuple[str, Union[str, bytes], bool, asyncio.Future]]) -> None:
        """
        Execute a batch of write operations.
        
        Args:
            batch: List of (path, data, binary, future) tuples
        """
        # Group by directory to improve cache locality
        by_directory = {}
        for path, data, binary, future in batch:
            directory = os.path.dirname(path)
            if directory not in by_directory:
                by_directory[directory] = []
            by_directory[directory].append((path, data, binary, future))
        
        # Process each directory group
        for directory, items in by_directory.items():
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # Process items in group
            for path, data, binary, future in items:
                try:
                    # Execute in thread pool
                    mode = "wb" if binary else "w"
                    bytes_written = await asyncio.to_thread(self._write_file_sync, path, data, mode)
                    
                    # Set result
                    if not future.done():
                        future.set_result(bytes_written)
                    
                    # Update statistics
                    self._write_ops += 1
                    self._write_bytes += bytes_written
                    
                except Exception as e:
                    # Set exception
                    if not future.done():
                        future.set_exception(e)
                    
                    logger.error(f"Error writing file {path}: {e}")
    
    def _read_file_sync(self, path: str, mode: str) -> Union[str, bytes]:
        """
        Read a file synchronously.
        
        Args:
            path: File path
            mode: File mode
            
        Returns:
            File contents
        """
        with open(path, mode) as f:
            return f.read()
    
    def _write_file_sync(self, path: str, data: Union[str, bytes], mode: str) -> int:
        """
        Write to a file synchronously.
        
        Args:
            path: File path
            data: Data to write
            mode: File mode
            
        Returns:
            Number of bytes written
        """
        with open(path, mode) as f:
            if isinstance(data, str) and mode == "wb":
                data = data.encode("utf-8")
            elif isinstance(data, bytes) and mode == "w":
                data = data.decode("utf-8")
            
            f.write(data)
            
            if isinstance(data, str):
                return len(data.encode("utf-8"))
            else:
                return len(data)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get I/O manager statistics.
        
        Returns:
            Dictionary with I/O manager statistics
        """
        return {
            "running": self._running,
            "read_queue_size": self._read_queue.qsize(),
            "write_queue_size": self._write_queue.qsize(),
            "read_ops": self._read_ops,
            "write_ops": self._write_ops,
            "read_bytes": self._read_bytes,
            "write_bytes": self._write_bytes,
            "read_batches": self._read_batches,
            "write_batches": self._write_batches,
            "max_batch_size": self.max_batch_size,
            "batch_interval": self.batch_interval,
            "max_workers": self.max_workers,
            "max_queue_size": self.max_queue_size
        }

class IOOptimizer:
    """
    I/O optimizer for efficient I/O operations.
    
    This class provides:
    - I/O usage tracking
    - I/O prioritization
    - Adaptive batching
    """
    
    def __init__(
        self,
        max_io_ops_per_second: int = 1000,
        throttle_threshold: int = 800,
        check_interval: float = 1.0
    ):
        """
        Initialize the I/O optimizer.
        
        Args:
            max_io_ops_per_second: Maximum I/O operations per second
            throttle_threshold: I/O operations per second to start throttling
            check_interval: Interval between I/O checks (seconds)
        """
        self.max_io_ops_per_second = max_io_ops_per_second
        self.throttle_threshold = throttle_threshold
        self.check_interval = check_interval
        
        # I/O usage history
        self._io_history = []
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        
        # Running flag
        self._running = False
        
        # Throttling state
        self._throttling = False
        self._throttle_factor = 1.0
        
        # Statistics
        self._throttle_count = 0
        self._read_ops = 0
        self._write_ops = 0
        
        logger.debug("IOOptimizer initialized")
    
    async def start(self) -> None:
        """Start the I/O optimizer."""
        if self._running:
            return
        
        self._running = True
        
        # Start monitoring
        self._monitoring_task = asyncio.create_task(self._monitor_io())
        
        logger.debug("IOOptimizer started")
    
    async def stop(self) -> None:
        """Stop the I/O optimizer."""
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
        
        logger.debug("IOOptimizer stopped")
    
    async def record_operation(self, operation_type: str) -> None:
        """
        Record an I/O operation.
        
        Args:
            operation_type: Type of operation ("read" or "write")
        """
        if operation_type == "read":
            self._read_ops += 1
        elif operation_type == "write":
            self._write_ops += 1
    
    async def should_throttle(self) -> Tuple[bool, float]:
        """
        Check if I/O operations should be throttled.
        
        Returns:
            Tuple of (should_throttle, throttle_factor)
        """
        return self._throttling, self._throttle_factor
    
    async def _monitor_io(self) -> None:
        """Monitor I/O usage."""
        while self._running:
            try:
                # Calculate operations per second
                now = time.time()
                ops_per_second = self._read_ops + self._write_ops
                
                # Record history
                self._io_history.append((now, ops_per_second))
                
                # Reset counters
                self._read_ops = 0
                self._write_ops = 0
                
                # Limit history size
                if len(self._io_history) > 100:
                    self._io_history = self._io_history[-100:]
                
                # Check if we need to throttle
                if ops_per_second > self.throttle_threshold:
                    # Calculate throttle factor based on how much we exceed the threshold
                    excess = (ops_per_second - self.throttle_threshold) / (self.max_io_ops_per_second - self.throttle_threshold)
                    self._throttle_factor = max(0.1, 1.0 - excess)
                    
                    if not self._throttling:
                        logger.debug(f"I/O operations {ops_per_second} exceeds throttle threshold {self.throttle_threshold}, throttling operations (factor: {self._throttle_factor:.2f})")
                        self._throttling = True
                        self._throttle_count += 1
                else:
                    # No need to throttle
                    self._throttling = False
                    self._throttle_factor = 1.0
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                logger.debug("I/O monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"Error monitoring I/O: {e}")
                await asyncio.sleep(1.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get I/O optimizer statistics.
        
        Returns:
            Dictionary with I/O optimizer statistics
        """
        stats = {
            "running": self._running,
            "max_io_ops_per_second": self.max_io_ops_per_second,
            "throttle_threshold": self.throttle_threshold,
            "check_interval": self.check_interval,
            "throttling": self._throttling,
            "throttle_factor": self._throttle_factor,
            "throttle_count": self._throttle_count,
            "current_ops_per_second": None,
            "io_history": self._io_history
        }
        
        # Add current I/O usage
        if self._io_history:
            stats["current_ops_per_second"] = self._io_history[-1][1]
        
        return stats