"""Initialize gevent with Python 3.12+ asyncio support and proper monkey patching."""

import logging
import asyncio
from contextlib import asynccontextmanager
import ssl

logger = logging.getLogger(__name__)

# Store original SSL methods before patching
_orig_wrap_socket = ssl.wrap_socket if hasattr(ssl, 'wrap_socket') else None
_orig_ssl_context = ssl.SSLContext if hasattr(ssl, 'SSLContext') else None

class GeventManager:
    def __init__(self):
        self.loop = None
        self.eventlet = None  # For compatibility with existing code
        self._initialized = False

    def _do_initialize(self):
        """Internal synchronous initialization."""
        try:
            # Import gevent first
            import gevent
            import gevent.monkey

            # Store gevent as eventlet for compatibility
            self.eventlet = gevent

            # Patch everything except SSL first
            gevent.monkey.patch_all(
                socket=True,
                dns=True,
                time=True,
                select=True,
                thread=False,
                os=False,  # Don't patch OS to avoid SSL issues
                ssl=False,  # We'll patch SSL separately
                httplib=False,
                subprocess=True,
                sys=False,
                aggressive=True,
                Event=False,
                builtins=True,
                signal=True
            )

            # Initialize asyncio event loop
            import aiohttp

            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            if logger.getEffectiveLevel() <= logging.DEBUG:
                self.loop.set_debug(True)

            # Add gevent sleep as eventlet sleep for compatibility
            self.eventlet.sleep = gevent.sleep

            logger.info("✓ Event loop initialized")
            logger.info("✓ Gevent patches applied")

            self._initialized = True
            return self.eventlet

        except Exception as e:
            logger.error("Failed to initialize gevent: %s", str(e))
            raise

    def initialize(self):
        """Initialize gevent synchronously."""
        if self._initialized:
            return self.eventlet
        return self._do_initialize()

    async def async_initialize(self):
        """Initialize gevent asynchronously."""
        if self._initialized:
            return self.eventlet
        
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
        """Clean up gevent resources synchronously."""
        return self._do_cleanup()

    async def async_cleanup(self):
        """Clean up gevent resources asynchronously."""
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
        """Context manager for running with gevent."""
        if not self._initialized:
            await self.async_initialize()
        try:
            yield self
        finally:
            await self.async_cleanup()

# Create global manager instance
manager = GeventManager()

def init():
    """Initialize gevent and event loop synchronously."""
    try:
        return manager.initialize()
    except Exception as e:
        logger.error("Failed to initialize gevent: %s", str(e))
        raise

async def async_init():
    """Initialize gevent and event loop asynchronously."""
    try:
        return await manager.async_initialize()
    except Exception as e:
        logger.error("Failed to initialize gevent: %s", str(e), exc_info=True)
        raise

async def run_with_eventlet(coro):
    """Run a coroutine with gevent context."""
    async with manager.run_context():
        return await coro

# Initialize on module import to ensure early patching
init()
