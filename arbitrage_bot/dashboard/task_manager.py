"""Task management for async operations.

This module provides a robust task management system for handling async tasks
with proper lifecycle tracking, cancellation, and error handling.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Coroutine, Set
from enum import Enum, auto
import time
import traceback

logger = logging.getLogger(__name__)


class TaskState(str, Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskManager:
    """Manages async tasks with proper lifecycle tracking and cancellation.
    
    This class provides a centralized way to create, track, and cancel async tasks
    with proper error handling and resource cleanup.
    
    Attributes:
        _tasks: Dictionary mapping task names to asyncio.Task objects
        _state: Dictionary mapping task names to their current state
        _metadata: Dictionary storing additional metadata for each task
        _lock: Asyncio lock for thread safety
    """

    def __init__(self):
        """Initialize the task manager."""
        self._tasks: Dict[str, asyncio.Task] = {}
        self._state: Dict[str, TaskState] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._cancel_timeout = 2.0  # seconds
        logger.debug("TaskManager initialized")

    async def add_task(self, name: str, coro: Coroutine, metadata: Optional[Dict[str, Any]] = None) -> asyncio.Task:
        """Add a new task to be managed.
        
        Args:
            name: Unique name for the task
            coro: Coroutine to be executed as a task
            metadata: Optional metadata to store with the task
            
        Returns:
            The created asyncio.Task object
            
        Raises:
            ValueError: If a task with the same name already exists
        """
        async with self._lock:
            if name in self._tasks:
                logger.warning(f"Task {name} already exists, cancelling old task")
                await self.cancel_task(name)
                
            # Create a wrapped coroutine that updates the task state
            wrapped_coro = self._wrap_coroutine(name, coro)
            
            # Create and store the task
            task = asyncio.create_task(wrapped_coro, name=name)
            self._tasks[name] = task
            self._state[name] = TaskState.RUNNING
            self._metadata[name] = metadata or {
                "created_at": time.time(),
                "last_updated": time.time()
            }
            
            logger.debug(f"Task {name} added and started")
            return task

    async def cancel_task(self, name: str) -> bool:
        """Cancel a task with proper cleanup.
        
        Args:
            name: Name of the task to cancel
            
        Returns:
            True if task was successfully cancelled, False otherwise
        """
        async with self._lock:
            if name not in self._tasks:
                logger.warning(f"Task {name} not found for cancellation")
                return False
                
            task = self._tasks[name]
            if task.done():
                logger.debug(f"Task {name} already completed, no need to cancel")
                return True
                
            # Update state and cancel the task
            self._state[name] = TaskState.CANCELLING
            self._metadata[name]["last_updated"] = time.time()
            task.cancel()
            
            try:
                # Wait for the task to be cancelled with a timeout
                await asyncio.wait_for(asyncio.shield(task), timeout=self._cancel_timeout)
                logger.debug(f"Task {name} cancelled successfully")
            except asyncio.TimeoutError:
                logger.warning(f"Task {name} cancellation timed out after {self._cancel_timeout}s")
            except asyncio.CancelledError:
                logger.debug(f"Task {name} cancelled")
            except Exception as e:
                logger.error(f"Error during task {name} cancellation: {str(e)}")
                
            # Update final state
            self._state[name] = TaskState.CANCELLED
            self._metadata[name]["cancelled_at"] = time.time()
            
            return True

    async def cancel_all_tasks(self) -> None:
        """Cancel all managed tasks."""
        async with self._lock:
            task_names = list(self._tasks.keys())
            
        for name in task_names:
            await self.cancel_task(name)
            
        logger.debug(f"All {len(task_names)} tasks cancelled")

    async def get_task_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific task.
        
        Args:
            name: Name of the task
            
        Returns:
            Dictionary with task information or None if task not found
        """
        async with self._lock:
            if name not in self._tasks:
                return None
                
            task = self._tasks[name]
            state = self._state[name]
            metadata = self._metadata[name]
            
            return {
                "name": name,
                "state": state,
                "done": task.done(),
                "cancelled": task.cancelled(),
                "exception": str(task.exception()) if task.done() and not task.cancelled() and task.exception() else None,
                "metadata": metadata
            }

    async def get_all_tasks_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all managed tasks.
        
        Returns:
            Dictionary mapping task names to their information
        """
        async with self._lock:
            result = {}
            for name in self._tasks:
                task = self._tasks[name]
                state = self._state[name]
                metadata = self._metadata[name]
                
                result[name] = {
                    "name": name,
                    "state": state,
                    "done": task.done(),
                    "cancelled": task.cancelled(),
                    "exception": str(task.exception()) if task.done() and not task.cancelled() and task.exception() else None,
                    "metadata": metadata
                }
                
            return result

    async def cleanup_completed_tasks(self) -> int:
        """Remove completed tasks from the manager.
        
        Returns:
            Number of tasks cleaned up
        """
        async with self._lock:
            to_remove = []
            for name, task in self._tasks.items():
                if task.done():
                    to_remove.append(name)
                    
            for name in to_remove:
                del self._tasks[name]
                del self._state[name]
                del self._metadata[name]
                
            logger.debug(f"Cleaned up {len(to_remove)} completed tasks")
            return len(to_remove)

    def _wrap_coroutine(self, name: str, coro: Coroutine) -> Coroutine:
        """Wrap a coroutine to track its lifecycle.
        
        Args:
            name: Task name
            coro: Original coroutine
            
        Returns:
            Wrapped coroutine that updates task state
        """
        async def wrapped():
            try:
                # Execute the original coroutine
                result = await coro
                
                # Update state on successful completion
                async with self._lock:
                    if name in self._state:
                        self._state[name] = TaskState.COMPLETED
                        self._metadata[name]["completed_at"] = time.time()
                        self._metadata[name]["last_updated"] = time.time()
                        
                return result
                
            except asyncio.CancelledError:
                # Handle cancellation
                async with self._lock:
                    if name in self._state:
                        self._state[name] = TaskState.CANCELLED
                        self._metadata[name]["cancelled_at"] = time.time()
                        self._metadata[name]["last_updated"] = time.time()
                        
                raise
                
            except Exception as e:
                # Handle other exceptions
                error_details = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                
                logger.error(f"Task {name} failed with error: {str(e)}")
                logger.debug(f"Task {name} traceback: {traceback.format_exc()}")
                
                async with self._lock:
                    if name in self._state:
                        self._state[name] = TaskState.FAILED
                        self._metadata[name]["error"] = error_details
                        self._metadata[name]["failed_at"] = time.time()
                        self._metadata[name]["last_updated"] = time.time()
                        
                raise
                
        return wrapped()

    async def get_task_metrics(self) -> Dict[str, Any]:
        """Get metrics about managed tasks.
        
        Returns:
            Dictionary with task metrics
        """
        async with self._lock:
            total = len(self._tasks)
            running = sum(1 for state in self._state.values() if state == TaskState.RUNNING)
            completed = sum(1 for state in self._state.values() if state == TaskState.COMPLETED)
            failed = sum(1 for state in self._state.values() if state == TaskState.FAILED)
            cancelled = sum(1 for state in self._state.values() if state == TaskState.CANCELLED)
            cancelling = sum(1 for state in self._state.values() if state == TaskState.CANCELLING)
            
            return {
                "total": total,
                "running": running,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "cancelling": cancelling,
                "by_state": {
                    TaskState.RUNNING: running,
                    TaskState.COMPLETED: completed,
                    TaskState.FAILED: failed,
                    TaskState.CANCELLED: cancelled,
                    TaskState.CANCELLING: cancelling
                }
            }