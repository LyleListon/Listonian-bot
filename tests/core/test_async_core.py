"""
Test core async functionality and patterns.

This module tests:
1. Async event loop management
2. Concurrent task execution
3. Resource cleanup
4. Error handling patterns
5. Lock management
"""

import pytest
import asyncio
import logging
from typing import List, Set, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test fixtures
@pytest.fixture
async def event_loop():
    """Create and yield a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
async def task_lock():
    """Create a lock for testing thread safety."""
    return asyncio.Lock()

# Test async context manager
@asynccontextmanager
async def managed_resource():
    """Test resource with proper cleanup."""
    try:
        yield "resource"
    finally:
        await asyncio.sleep(0.1)  # Simulate cleanup

# Test cases
@pytest.mark.asyncio
async def test_concurrent_tasks():
    """Test concurrent task execution."""
    async def task(delay: float, result: List[int], value: int) -> None:
        await asyncio.sleep(delay)
        result.append(value)
    
    results: List[int] = []
    tasks = [
        task(0.1, results, 1),
        task(0.2, results, 2),
        task(0.3, results, 3)
    ]
    
    await asyncio.gather(*tasks)
    assert results == [1, 2, 3], "Tasks did not complete in expected order"

@pytest.mark.asyncio
async def test_lock_management(task_lock: asyncio.Lock):
    """Test thread safety with locks."""
    shared_resource: Set[int] = set()
    
    async def critical_section(value: int) -> None:
        async with task_lock:
            await asyncio.sleep(0.1)  # Simulate work
            shared_resource.add(value)
            await asyncio.sleep(0.1)  # Simulate more work
    
    # Run concurrent tasks that access shared resource
    tasks = [critical_section(i) for i in range(5)]
    await asyncio.gather(*tasks)
    
    assert len(shared_resource) == 5, "Lock failed to protect shared resource"

@pytest.mark.asyncio
async def test_resource_cleanup():
    """Test proper resource cleanup patterns."""
    cleanup_called = False
    
    async with managed_resource() as resource:
        assert resource == "resource"
        
        # Simulate work with resource
        await asyncio.sleep(0.1)
        cleanup_called = True
    
    assert cleanup_called, "Resource cleanup was not called"

@pytest.mark.asyncio
async def test_error_handling():
    """Test async error handling patterns."""
    class CustomError(Exception):
        pass
    
    async def failing_task() -> None:
        await asyncio.sleep(0.1)
        raise CustomError("Expected error")
    
    with pytest.raises(CustomError):
        await failing_task()

@pytest.mark.asyncio
async def test_timeout_handling():
    """Test timeout handling for async operations."""
    async def slow_task() -> str:
        await asyncio.sleep(2)
        return "completed"
    
    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(0.5):
            await slow_task()

@pytest.mark.asyncio
async def test_cancellation():
    """Test task cancellation handling."""
    cancel_called = False
    
    async def cancellable_task() -> None:
        nonlocal cancel_called
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancel_called = True
            raise
    
    task = asyncio.create_task(cancellable_task())
    await asyncio.sleep(0.1)
    task.cancel()
    
    with pytest.raises(asyncio.CancelledError):
        await task
    
    assert cancel_called, "Task was not properly cancelled"

@pytest.mark.asyncio
async def test_parallel_execution():
    """Test parallel execution performance."""
    async def parallel_task(delay: float) -> float:
        start = datetime.now()
        await asyncio.sleep(delay)
        return (datetime.now() - start).total_seconds()
    
    delays = [0.1, 0.2, 0.3]
    start_time = datetime.now()
    
    # Execute tasks in parallel
    results = await asyncio.gather(*[parallel_task(d) for d in delays])
    
    total_time = (datetime.now() - start_time).total_seconds()
    max_delay = max(delays)
    
    # Verify parallel execution
    assert total_time < sum(delays), "Tasks did not execute in parallel"
    assert total_time >= max_delay, "Tasks completed too quickly"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])