"""Async event loop management with Python 3.12+ asyncio support."""

import logging
import asyncio
from contextlib import asynccontextmanager
import ssl

logger = logging.getLogger(__name__)

class AsyncManager:
    def __init__(self):
        self.loop = None
        self._initialized = False

    def _do_initialize(self):
        """Internal synchronous initialization."""
        try:
            # Initialize asyncio event loop
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            if logger.getEffectiveLevel() <= logging.DEBUG:
                self.loop.set_debug(True)

            logger.info("✓ Event loop initialized")

            self._initialized = True
            return True

        except Exception as e:
            logger.error("Failed to initialize event loop: %s", str(e))
            raise

    def initialize(self):
        """Initialize event loop synchronously."""
        if self._initialized:
            return True
        return self._do_initialize()

    async def async_initialize(self):
        """Initialize event loop asynchronously."""
        if self._initialized:
            return True
        
        # If we're in an event loop, use sync initialization
        try:
            loop = asyncio.get_running_loop()
            if not loop.is_running():
                return self.initialize()
            # If loop is running, we need to run initialization in executor
            return await loop.run_in_executor(None, self.initialize)
        except RuntimeError:
            # No event loop, we can use sync initialization
            return self.initialize()

    def _do_cleanup(self):
        """Internal synchronous cleanup."""
        if not self._initialized:
            return

        if self.loop and self.loop.is_running():
            try:
                current_task = asyncio.current_task(self.loop)
                tasks = [t for t in asyncio.all_tasks(self.loop) if t is not current_task]

                for task in tasks:
                    task.cancel()

                if tasks:
                    self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

                if self.loop is not asyncio.get_event_loop():
                    self.loop.stop()
                    self.loop.run_until_complete(self.loop.shutdown_asyncgens())
                    self.loop.close()

                logger.info("✓ Event loop cleaned up")
            except Exception as e:
                logger.error("Failed to cleanup event loop: %s", str(e))

        self._initialized = False

    def cleanup(self):
        """Clean up event loop resources synchronously."""
        return self._do_cleanup()

    async def async_cleanup(self):
        """Clean up event loop resources asynchronously."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                await loop.run_in_executor(None, self.cleanup)
            else:
                self.cleanup()
        except RuntimeError:
            self.cleanup()

    @asynccontextmanager
    async def run_context(self):
        """Context manager for running with event loop."""
        if not self._initialized:
            await self.async_initialize()
        try:
            yield self
        finally:
            await self.async_cleanup()

# Create global manager instance
manager = AsyncManager()

def init():
    """Initialize event loop synchronously."""
    try:
        return manager.initialize()
    except Exception as e:
        logger.error("Failed to initialize event loop: %s", str(e))
        raise

async def async_init():
    """Initialize event loop asynchronously."""
    try:
        return await manager.async_initialize()
    except Exception as e:
        logger.error("Failed to initialize event loop: %s", str(e), exc_info=True)
        raise

async def run_with_async_context(coro):
    """Run a coroutine with event loop context."""
    async with manager.run_context():
        return await coro

# Initialize on module import to ensure early setup
init()
