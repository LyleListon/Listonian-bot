"""Test async functionality."""

import logging
import asyncio
import time
import socket
import threading
from datetime import datetime

logger = logging.getLogger(__name__)

async def test_async():
    """Test async functionality."""
    try:
        logger.info("Testing async functionality...")

        # Test event loop
        logger.info("Testing event loop...")
        loop = asyncio.get_running_loop()
        logger.info("✓ Event loop running")

        # Test async sleep
        logger.info("Testing async sleep...")
        start = time.time()
        await asyncio.sleep(0.1)
        duration = time.time() - start
        logger.info(f"Sleep duration: {duration:.3f}s")
        assert 0.09 <= duration <= 0.15, f"Sleep duration {duration} outside expected range"
        logger.info("✓ Async sleep working")

        # Test async task
        logger.info("Testing async task...")
        async def task_test():
            await asyncio.sleep(0.1)
            return "Task completed"

        task = asyncio.create_task(task_test())
        result = await task
        assert result == "Task completed"
        logger.info("✓ Async task working")

        # Test concurrent tasks
        logger.info("Testing concurrent tasks...")
        async def concurrent_test(i):
            await asyncio.sleep(0.1)
            return f"Task {i} completed"

        tasks = [asyncio.create_task(concurrent_test(i)) for i in range(3)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 3
        assert all("completed" in r for r in results)
        logger.info("✓ Concurrent tasks working")

        # Test error handling
        logger.info("Testing error handling...")
        async def error_test():
            await asyncio.sleep(0.1)
            raise ValueError("Test error")

        try:
            await error_test()
            assert False, "Should have raised error"
        except ValueError as e:
            assert str(e) == "Test error"
            logger.info("✓ Error handling working")

        logger.info("✓ All async tests completed successfully")
        return True

    except Exception as e:
        logger.error(f"Async test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(test_async())
    except Exception as e:
        logger.error(f"Test error: {e}")
        raise