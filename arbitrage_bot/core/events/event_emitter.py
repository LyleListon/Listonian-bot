"""Async event emitter for managing and distributing events."""

import asyncio
import logging
import time
import uuid
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    TypeVar,
    Generic,
    Union,
    cast,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")  # Type variable for event data


class Event(Generic[T]):
    """Event class with metadata and typed payload."""

    def __init__(
        self,
        name: str,
        data: T,
        source: Optional[str] = None,
        timestamp: Optional[float] = None,
        event_id: Optional[str] = None,
        severity: str = "info",
    ):
        """
        Initialize event with metadata.

        Args:
            name: Event name/type
            data: Event payload
            source: Component that generated the event
            timestamp: Event creation time (default: current time)
            event_id: Unique event identifier (default: generated UUID)
            severity: Event importance level (debug, info, warning, error, critical)
        """
        self.name = name
        self.data = data
        self.source = source
        self.timestamp = timestamp or time.time()
        self.id = event_id or str(uuid.uuid4())
        self.severity = severity

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "severity": self.severity,
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"Event({self.name}, id={self.id}, source={self.source}, severity={self.severity})"


# Type definitions for event handlers
SyncHandler = Callable[[Event[Any]], None]
AsyncHandler = Callable[[Event[Any]], asyncio.Future]
EventHandler = Union[SyncHandler, AsyncHandler]


class EventEmitter:
    """
    Thread-safe async event emitter.

    Handles both synchronous and asynchronous event handlers, with support
    for typed events and comprehensive event metadata.
    """

    def __init__(self):
        """Initialize event emitter."""
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._handler_lock = asyncio.Lock()
        self._running_tasks: Set[asyncio.Task] = set()
        self._task_lock = asyncio.Lock()

    async def on(self, event_name: str, handler: EventHandler) -> None:
        """
        Register an event handler.

        Args:
            event_name: Name of the event to listen for
            handler: Function or coroutine function to handle the event
        """
        async with self._handler_lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []

            self._handlers[event_name].append(handler)
            logger.debug("Registered handler for event %s", event_name)

    async def off(self, event_name: str, handler: EventHandler) -> bool:
        """
        Remove an event handler.

        Args:
            event_name: Name of the event
            handler: Handler to remove

        Returns:
            True if handler was removed, False otherwise
        """
        async with self._handler_lock:
            if event_name not in self._handlers:
                return False

            handlers = self._handlers[event_name]
            if handler not in handlers:
                return False

            handlers.remove(handler)
            logger.debug("Removed handler for event %s", event_name)

            # Clean up empty handler lists
            if not handlers:
                del self._handlers[event_name]

            return True

    async def emit(self, event_name: str, data: Any, **kwargs) -> None:
        """
        Emit an event asynchronously.

        Args:
            event_name: Name of the event to emit
            data: Data to pass to handlers
            **kwargs: Additional metadata for the event
        """
        # Create event object
        event = Event(name=event_name, data=data, **kwargs)

        await self._emit_event(event)

    async def _emit_event(self, event: Event[Any]) -> None:
        """
        Internal method to emit an event to all registered handlers.

        Args:
            event: Event object to emit
        """
        async with self._handler_lock:
            handlers = self._handlers.get(event.name, []).copy()
            # Also notify wildcard handlers
            handlers.extend(self._handlers.get("*", []))

        if not handlers:
            logger.debug("No handlers for event %s", event.name)
            return

        logger.debug("Emitting event %s to %d handlers", event.name, len(handlers))

        # Process handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Async handler
                    task = asyncio.create_task(
                        self._run_async_handler(cast(AsyncHandler, handler), event)
                    )

                    async with self._task_lock:
                        self._running_tasks.add(task)
                        # Clean up task when done
                        task.add_done_callback(
                            lambda t: asyncio.create_task(self._cleanup_task(t))
                        )
                else:
                    # Sync handler - run in executor to avoid blocking
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, cast(SyncHandler, handler), event)
            except Exception as e:
                logger.error("Error calling event handler: %s", str(e))

    async def _run_async_handler(
        self, handler: AsyncHandler, event: Event[Any]
    ) -> None:
        """Run an async handler with error handling."""
        try:
            await handler(event)
        except Exception as e:
            logger.error("Error in async event handler: %s", str(e))

    async def _cleanup_task(self, task: asyncio.Task) -> None:
        """Clean up completed task from tracking set."""
        async with self._task_lock:
            if task in self._running_tasks:
                self._running_tasks.remove(task)

    async def wait_for_pending_events(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all pending event handlers to complete.

        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)

        Returns:
            True if all handlers completed, False if timeout occurred
        """
        async with self._task_lock:
            pending_tasks = list(self._running_tasks)

        if not pending_tasks:
            return True

        try:
            logger.debug("Waiting for %d pending event handlers", len(pending_tasks))
            await asyncio.wait(pending_tasks, timeout=timeout)

            # Check if all tasks are done
            return all(task.done() for task in pending_tasks)

        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for event handlers to complete")
            return False

    async def once(self, event_name: str) -> Event[Any]:
        """
        Wait for a specific event to occur once.

        Args:
            event_name: Name of the event to wait for

        Returns:
            The event when it occurs
        """
        # Create a future that will be resolved when the event occurs
        future: asyncio.Future[Event[Any]] = asyncio.Future()

        # Create a one-time handler
        async def one_time_handler(event: Event[Any]) -> None:
            if not future.done():
                future.set_result(event)
                await self.off(event_name, one_time_handler)

        # Register the handler
        await self.on(event_name, one_time_handler)

        # Wait for the event
        return await future

    def get_handler_count(self, event_name: Optional[str] = None) -> int:
        """
        Get count of registered handlers.

        Args:
            event_name: Name of event to count handlers for (None = count all)

        Returns:
            Number of registered handlers
        """
        if event_name:
            return len(self._handlers.get(event_name, []))

        # Count all handlers
        return sum(len(handlers) for handlers in self._handlers.values())
