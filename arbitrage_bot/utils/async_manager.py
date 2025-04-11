"""
Async Manager Utility

This module provides utilities for managing async operations and ensuring
proper resource cleanup.
"""

import asyncio
import logging
import functools
from typing import Optional, Any, Callable, Awaitable, TypeVar, ParamSpec

from .signal_handler import SignalHandler

logger = logging.getLogger(__name__)


class AsyncLock:
    """
    Thread-safe async lock implementation.

    This class provides a reentrant lock that can be used in async code.
    It ensures proper resource locking across async operations.
    """

    def __init__(self):
        """Initialize the async lock."""
        self._lock = asyncio.Lock()
        self._task_id = None
        self._depth = 0

    async def acquire(self) -> None:
        """Acquire the lock."""
        current_task = asyncio.current_task()
        if self._task_id == id(current_task):
            self._depth += 1
            return

        await self._lock.acquire()
        self._task_id = id(current_task)
        self._depth = 1

    def release(self) -> None:
        """Release the lock."""
        current_task = asyncio.current_task()
        if self._task_id != id(current_task):
            raise RuntimeError("Lock can only be released by the task that acquired it")

        self._depth -= 1
        if self._depth == 0:
            self._task_id = None
            self._lock.release()

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


P = ParamSpec("P")
T = TypeVar("T")


def with_retry(  # Keep the parameter names consistent with usage
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential: bool = True,
    logger: Optional[logging.Logger] = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator for retrying async operations that might fail temporarily.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential: Whether to use exponential backoff
        logger: Logger to use for retry messages
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            log = logger or logging.getLogger(func.__module__)
            attempt = 0
            last_error = None

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    last_error = e

                    if attempt < max_attempts:  # Changed from retries to max_attempts
                        delay = min(
                            base_delay * (2**attempt if exponential else 1), max_delay
                        )
                        log.warning(
                            f"Attempt {attempt} failed, retrying in {delay:.1f}s: {e}"
                        )
                        await asyncio.sleep(delay)

            raise last_error  # type: ignore

        return wrapper

    return decorator


class AsyncManager:
    """
    Manager for async operations and resources.

    This class provides utilities for:
    - Managing the event loop
    - Handling graceful shutdowns
    - Coordinating async resource cleanup
    """

    def __init__(self):
        """Initialize the async manager."""
        self._initialized = False
        self._cleanup_handlers = []
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._signal_handler: Optional[SignalHandler] = None

    async def initialize(self) -> None:
        """Initialize the async manager."""
        async with self._lock:
            if self._initialized:
                return

            logger.info("Initializing async manager")

            try:
                # Get or create event loop
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)

                # Set up signal handler
                self._signal_handler = SignalHandler(self._loop)
                self._signal_handler.register_cleanup(self.async_cleanup)
                self._signal_handler.setup()

                self._initialized = True
                logger.info("Async manager initialized successfully")

            except Exception as e:
                logger.error(f"Failed to initialize async manager: {e}", exc_info=True)
                raise

    async def async_cleanup(self) -> None:
        """Clean up async resources."""
        async with self._lock:
            if not self._initialized:
                return

            logger.info("Cleaning up async resources")

            # Run cleanup handlers in reverse order
            for handler in reversed(self._cleanup_handlers):
                try:
                    await handler()
                except Exception as e:
                    logger.error(f"Error in cleanup handler: {e}", exc_info=True)

            self._cleanup_handlers.clear()

            # Clean up signal handler
            if self._signal_handler:
                self._signal_handler.cleanup()
                self._signal_handler = None

            self._initialized = False

    def register_cleanup_handler(self, handler: Callable[[], Awaitable[None]]) -> None:
        """
        Register a cleanup handler.

        Args:
            handler: Async function to call during cleanup
        """
        if not self._initialized:
            raise RuntimeError("Async manager not initialized")

        self._cleanup_handlers.append(handler)

    async def run_with_async_context(self, coro: Awaitable[Any]) -> Any:
        """
        Run a coroutine with proper async context management.

        Args:
            coro: Coroutine to run

        Returns:
            Result of the coroutine
        """
        if not self._initialized:
            raise RuntimeError("Async manager not initialized")

        try:
            return await coro
        except Exception as e:
            logger.error(f"Error in async context: {e}", exc_info=True)
            raise
        finally:
            # Cleanup will be handled by signal handlers
            pass


# Global instance
manager = AsyncManager()


async def async_init() -> None:
    """Initialize the global async manager."""
    await manager.initialize()


async def run_with_async_context(coro: Awaitable[Any]) -> Any:
    """
    Run a coroutine with the global async context.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    return await manager.run_with_async_context(coro)
