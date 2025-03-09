"""
Async Manager Module

This module provides functionality for:
- Managing asynchronous operations
- Thread safety with locks
- Retry mechanisms
- Resource management
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, TypeVar
from asyncio import Lock, Semaphore

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AsyncManager:
    """Manages asynchronous operations and resources."""

    def __init__(self):
        """Initialize the async manager."""
        self.locks = {}
        self.semaphores = {}

    def get_lock(self, name: str) -> Lock:
        """
        Get or create a named lock.

        Args:
            name: Lock identifier

        Returns:
            Lock instance
        """
        if name not in self.locks:
            self.locks[name] = Lock()
        return self.locks[name]

    def get_semaphore(self, name: str, value: int = 1) -> Semaphore:
        """
        Get or create a named semaphore.

        Args:
            name: Semaphore identifier
            value: Maximum number of concurrent operations

        Returns:
            Semaphore instance
        """
        if name not in self.semaphores:
            self.semaphores[name] = Semaphore(value)
        return self.semaphores[name]

    async def cleanup(self):
        """Clean up resources."""
        self.locks.clear()
        self.semaphores.clear()

# Global manager instance
manager = AsyncManager()

def with_lock(name: str) -> Callable:
    """
    Decorator for using a named lock.

    Args:
        name: Lock identifier

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            lock = manager.get_lock(name)
            async with lock:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def with_semaphore(name: str, value: int = 1) -> Callable:
    """
    Decorator for using a named semaphore.

    Args:
        name: Semaphore identifier
        value: Maximum number of concurrent operations

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            semaphore = manager.get_semaphore(name, value)
            async with semaphore:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

def with_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator for retrying failed operations.

    Args:
        retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            current_delay = delay

            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {retries} retries failed. "
                            f"Last error: {last_exception}"
                        )
                        raise last_exception

        return wrapper
    return decorator
