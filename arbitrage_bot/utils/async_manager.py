"""
Async Manager Module

This module provides utilities for:
- Async operations management
- Retry mechanisms
- Lock management
"""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

class AsyncLock:
    """Thread-safe async lock implementation."""

    def __init__(self):
        """Initialize lock."""
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        """Enter async context manager."""
        await self._lock.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        self._lock.release()

def with_retry(retries: int = 3, delay: float = 1.0) -> Callable:
    """
    Retry decorator for async functions.

    Args:
        retries: Number of retries
        delay: Delay between retries in seconds

    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error = None
            current_delay = delay

            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries + 1} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= 2  # Exponential backoff
                    else:
                        logger.error(
                            f"All {retries + 1} attempts failed. "
                            f"Last error: {e}"
                        )
                        raise last_error

        return wrapper
    return decorator

class AsyncRetryManager:
    """Manages retries for async operations."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0
    ):
        """
        Initialize retry manager.

        Args:
            max_retries: Maximum number of retries
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._lock = AsyncLock()

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries fail
        """
        last_error = None
        current_delay = self.base_delay

        async with self._lock:
            for attempt in range(self.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay = min(
                            current_delay * 2,  # Exponential backoff
                            self.max_delay
                        )
                    else:
                        logger.error(
                            f"All {self.max_retries + 1} attempts failed. "
                            f"Last error: {e}"
                        )
                        raise last_error

class AsyncRateLimiter:
    """Rate limiter for async operations."""

    def __init__(self, requests_per_second: float):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.interval = 1.0 / requests_per_second
        self.last_request = 0.0
        self._lock = AsyncLock()

    async def acquire(self):
        """Acquire rate limit slot."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait_time = max(0, self.interval - (now - self.last_request))
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.last_request = now
