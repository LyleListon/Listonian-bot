"""Initialize eventlet with Python 3.12+ asyncio support."""

import logging
import asyncio
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class EventletManager:
    def __init__(self):
        self.loop = None
        self.eventlet = None
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return self.eventlet

        try:
            import eventlet
            self.eventlet = eventlet

            eventlet.monkey_patch(
                os=True,
                select=True,
                socket=True,
                thread=False,
                time=False,
                psycopg=False,
                MySQLdb=False,
                builtins=True
            )

            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)

            if logger.getEffectiveLevel() <= logging.DEBUG:
                self.loop.set_debug(True)

            logger.info("✓ Event loop initialized")
            logger.info("✓ Eventlet patches applied")

            self._initialized = True
            return self.eventlet

        except Exception as e:
            logger.error("Failed to initialize eventlet", exc_info=True)
            raise

    async def cleanup(self):
        if not self._initialized:
            return

        if self.loop and self.loop.is_running():
            current_task = asyncio.current_task(self.loop)
            tasks = [t for t in asyncio.all_tasks(self.loop) if t is not current_task]

            for task in tasks:
                task.cancel()

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            if self.loop is not asyncio.get_event_loop():
                self.loop.stop()
                await self.loop.shutdown_asyncgens()
                self.loop.close()

            logger.info("✓ Event loop cleaned up")

        self._initialized = False

    @asynccontextmanager
    async def run_context(self):
        if not self._initialized:
            await self.initialize()
        try:
            yield self
        finally:
            await self.cleanup()

manager = EventletManager()

async def setup_eventlet():
    return await manager.initialize()

async def cleanup_eventlet():
    await manager.cleanup()

async def run_with_eventlet(coro):
    async with manager.run_context():
        return await coro

if __name__ != "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception as e:
        logger.error("Failed to setup event loop", exc_info=True)
        raise
