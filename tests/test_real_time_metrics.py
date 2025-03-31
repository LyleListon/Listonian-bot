"""Tests for real-time metrics optimization components."""

import asyncio
import pytest
import logging
import time
from unittest.mock import MagicMock, patch
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from arbitrage_bot.dashboard.task_manager import TaskManager, TaskState
from arbitrage_bot.dashboard.connection_manager import ConnectionManager, ConnectionState
from arbitrage_bot.dashboard.metrics_service import MetricsService, MetricsType
from arbitrage_bot.dashboard.websocket_server import WebSocketServer


# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestTaskManager:
    """Test the TaskManager class."""

    @pytest.fixture
    async def task_manager(self):
        """Create a TaskManager instance for testing."""
        manager = TaskManager()
        yield manager
        await manager.cancel_all_tasks()

    @pytest.mark.asyncio
    async def test_add_task(self, task_manager):
        """Test adding a task."""
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "done"

        task = await task_manager.add_task("test_task", dummy_task())
        assert "test_task" in task_manager._tasks
        assert task_manager._state["test_task"] == TaskState.RUNNING
        
        # Wait for task to complete
        await asyncio.sleep(0.2)
        task_info = await task_manager.get_task_info("test_task")
        assert task_info["state"] == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_cancel_task(self, task_manager):
        """Test cancelling a task."""
        async def long_running_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise

        task = await task_manager.add_task("long_task", long_running_task())
        assert task_manager._state["long_task"] == TaskState.RUNNING
        
        # Cancel the task
        result = await task_manager.cancel_task("long_task")
        assert result is True
        assert task_manager._state["long_task"] == TaskState.CANCELLED

    @pytest.mark.asyncio
    async def test_task_error_handling(self, task_manager):
        """Test error handling in tasks."""
        async def failing_task():
            await asyncio.sleep(0.1)
            raise ValueError("Task failed")

        task = await task_manager.add_task("failing_task", failing_task())
        
        # Wait for task to fail
        await asyncio.sleep(0.2)
        task_info = await task_manager.get_task_info("failing_task")
        assert task_info["state"] == TaskState.FAILED
        assert "Task failed" in task_info["exception"]

    @pytest.mark.asyncio
    async def test_get_task_metrics(self, task_manager):
        """Test getting task metrics."""
        # Add some tasks
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "done"
            
        async def long_task():
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                raise

        await task_manager.add_task("task1", dummy_task())
        await task_manager.add_task("task2", long_task())
        
        # Get metrics
        metrics = await task_manager.get_task_metrics()
        assert metrics["total"] == 2
        assert metrics["running"] == 2
        
        # Cancel one task
        await task_manager.cancel_task("task2")
        
        # Wait for the other to complete
        await asyncio.sleep(0.2)
        
        # Get updated metrics
        metrics = await task_manager.get_task_metrics()
        assert metrics["total"] == 2
        assert metrics["running"] == 0
        assert metrics["completed"] == 1
        assert metrics["cancelled"] == 1


class TestConnectionManager:
    """Test the ConnectionManager class."""

    @pytest.fixture
    async def connection_manager(self):
        """Create a ConnectionManager instance for testing."""
        task_manager = TaskManager()
        manager = ConnectionManager(task_manager)
        yield manager
        await task_manager.cancel_all_tasks()

    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, connection_manager):
        """Test connection lifecycle management."""
        # Mock WebSocket
        ws = MagicMock()
        ws.closed = False
        ws.close = MagicMock(return_value=asyncio.Future())
        ws.close.return_value.set_result(None)
        ws.prepare = MagicMock(return_value=asyncio.Future())
        ws.prepare.return_value.set_result(None)
        ws._req = {"remote": "127.0.0.1", "headers": {"User-Agent": "test"}}
        
        # Connect
        result = await connection_manager.connect(ws)
        assert result is True
        assert ws in connection_manager._connections
        assert connection_manager._connections[ws]["state"] == ConnectionState.CONNECTED
        
        # Disconnect
        result = await connection_manager.disconnect(ws)
        assert result is True
        assert ws not in connection_manager._connections

    @pytest.mark.asyncio
    async def test_register_task(self, connection_manager):
        """Test registering a task with a connection."""
        # Mock WebSocket
        ws = MagicMock()
        ws.closed = False
        ws.close = MagicMock(return_value=asyncio.Future())
        ws.close.return_value.set_result(None)
        ws.prepare = MagicMock(return_value=asyncio.Future())
        ws.prepare.return_value.set_result(None)
        ws._req = {"remote": "127.0.0.1", "headers": {"User-Agent": "test"}}
        
        # Connect
        await connection_manager.connect(ws)
        
        # Register task
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "done"
            
        result = await connection_manager.register_task(ws, "test_task", dummy_task())
        assert result is True
        
        # Check task was registered
        client_id = connection_manager._connections[ws]["client_info"]["id"]
        task_name = f"{client_id}_test_task"
        assert task_name in connection_manager._connections[ws]["tasks"]
        
        # Disconnect (should cancel task)
        await connection_manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_connection_metrics(self, connection_manager):
        """Test getting connection metrics."""
        # Mock WebSockets
        ws1 = MagicMock()
        ws1.closed = False
        ws1.close = MagicMock(return_value=asyncio.Future())
        ws1.close.return_value.set_result(None)
        ws1.prepare = MagicMock(return_value=asyncio.Future())
        ws1.prepare.return_value.set_result(None)
        ws1._req = {"remote": "127.0.0.1", "headers": {"User-Agent": "test1"}}
        
        ws2 = MagicMock()
        ws2.closed = False
        ws2.close = MagicMock(return_value=asyncio.Future())
        ws2.close.return_value.set_result(None)
        ws2.prepare = MagicMock(return_value=asyncio.Future())
        ws2.prepare.return_value.set_result(None)
        ws2._req = {"remote": "127.0.0.2", "headers": {"User-Agent": "test2"}}
        
        # Connect both
        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)
        
        # Get metrics
        metrics = await connection_manager.get_connection_metrics()
        assert metrics["active_connections"] == 2
        assert metrics["total_connections_ever"] == 2
        assert metrics["by_state"][ConnectionState.CONNECTED] == 2
        
        # Disconnect one
        await connection_manager.disconnect(ws1)
        
        # Get updated metrics
        metrics = await connection_manager.get_connection_metrics()
        assert metrics["active_connections"] == 1
        assert metrics["total_connections_ever"] == 2
        assert metrics["by_state"][ConnectionState.CONNECTED] == 1


class TestMetricsService:
    """Test the MetricsService class."""

    @pytest.fixture
    async def metrics_service(self):
        """Create a MetricsService instance for testing."""
        service = MetricsService()
        yield service
        await service.stop()

    @pytest.mark.asyncio
    async def test_register_collector(self, metrics_service):
        """Test registering a metrics collector."""
        # Define a collector
        async def test_collector():
            return {"value": 42}
            
        # Register it
        metrics_service.register_collector("test", test_collector)
        assert "test" in metrics_service._collectors
        
        # Get metrics
        metrics = await metrics_service.get_metrics("test")
        assert metrics["value"] == 42
        
        # Check cache
        assert "test" in metrics_service._cache
        assert metrics_service._cache["test"]["data"]["value"] == 42

    @pytest.mark.asyncio
    async def test_caching(self, metrics_service):
        """Test metrics caching."""
        # Define a collector that counts calls
        call_count = 0
        
        async def counting_collector():
            nonlocal call_count
            call_count += 1
            return {"count": call_count}
            
        # Register it with a short TTL
        metrics_service.register_collector("counter", counting_collector)
        metrics_service._cache_ttl["counter"] = 0.2  # 200ms TTL
        
        # First call should increment counter
        metrics = await metrics_service.get_metrics("counter")
        assert metrics["count"] == 1
        
        # Second immediate call should use cache
        metrics = await metrics_service.get_metrics("counter")
        assert metrics["count"] == 1  # Still 1
        
        # Wait for TTL to expire
        await asyncio.sleep(0.3)
        
        # Call again should increment counter
        metrics = await metrics_service.get_metrics("counter")
        assert metrics["count"] == 2

    @pytest.mark.asyncio
    async def test_subscribers(self, metrics_service):
        """Test subscriber management."""
        # Create queues
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        
        # Register subscribers
        await metrics_service.register_subscriber(queue1)
        await metrics_service.register_subscriber(queue2)
        assert len(metrics_service._subscribers) == 2
        
        # Define a collector
        async def test_collector():
            return {"value": 42}
            
        # Register it
        metrics_service.register_collector("test", test_collector)
        
        # Broadcast metrics
        count = await metrics_service.broadcast_metrics("test", await test_collector())
        assert count == 2
        
        # Check queues received the message
        msg1 = queue1.get_nowait()
        assert msg1["type"] == "test_update"
        assert msg1["data"]["value"] == 42
        
        msg2 = queue2.get_nowait()
        assert msg2["type"] == "test_update"
        assert msg2["data"]["value"] == 42
        
        # Unregister one subscriber
        await metrics_service.unregister_subscriber(queue1)
        assert len(metrics_service._subscribers) == 1
        
        # Broadcast again
        count = await metrics_service.broadcast_metrics("test", await test_collector())
        assert count == 1
        
        # Only queue2 should receive it
        assert queue1.empty()
        msg2 = queue2.get_nowait()
        assert msg2["type"] == "test_update"


class TestWebSocketServer(AioHTTPTestCase):
    """Test the WebSocketServer class."""

    async def get_application(self):
        """Create an aiohttp application for testing."""
        app = web.Application()
        
        # Mock components
        self.market_analyzer = MagicMock()
        self.market_analyzer.get_market_summary = MagicMock(
            return_value=asyncio.Future())
        self.market_analyzer.get_market_summary.return_value.set_result(
            {"market": "data"})
            
        self.portfolio_tracker = MagicMock()
        self.portfolio_tracker.get_performance_summary = MagicMock(
            return_value=asyncio.Future())
        self.portfolio_tracker.get_performance_summary.return_value.set_result(
            {"portfolio": "data"})
            
        self.memory_bank = MagicMock()
        self.memory_bank.get_all_context = MagicMock(
            return_value=asyncio.Future())
        self.memory_bank.get_all_context.return_value.set_result(
            {"memory": "data"})
            
        self.storage_hub = MagicMock()
        self.storage_hub.get_status = MagicMock(
            return_value=asyncio.Future())
        self.storage_hub.get_status.return_value.set_result(
            {"storage": "data"})
            
        self.distribution_manager = MagicMock()
        self.distribution_manager.get_metrics = MagicMock(
            return_value=asyncio.Future())
        self.distribution_manager.get_metrics.return_value.set_result(
            {"distribution": "data"})
            
        self.execution_manager = MagicMock()
        self.execution_manager.get_metrics = MagicMock(
            return_value=asyncio.Future())
        self.execution_manager.get_metrics.return_value.set_result(
            {"execution": "data"})
            
        self.gas_optimizer = MagicMock()
        self.gas_optimizer.gas_prices = {
            "fast": 100,
            "standard": 80,
            "slow": 60,
            "base_fee": 50,
            "priority_fee": 10,
            "pending_txs": 100
        }
        self.gas_optimizer.gas_metrics = {
            "historical_prices": [70, 75, 80, 85, 90, 95, 100]
        }
        
        # Create WebSocketServer
        self.ws_server = WebSocketServer(
            app=app,
            market_analyzer=self.market_analyzer,
            portfolio_tracker=self.portfolio_tracker,
            memory_bank=self.memory_bank,
            storage_hub=self.storage_hub,
            distribution_manager=self.distribution_manager,
            execution_manager=self.execution_manager,
            gas_optimizer=self.gas_optimizer
        )
        
        await self.ws_server.initialize()
        
        return app

    @unittest_run_loop
    async def test_initialization(self):
        """Test WebSocketServer initialization."""
        assert self.ws_server.task_manager is not None
        assert self.ws_server.connection_manager is not None
        assert self.ws_server.metrics_service is not None

    @unittest_run_loop
    async def test_start_stop(self):
        """Test starting and stopping the WebSocketServer."""
        await self.ws_server.start()
        assert self.ws_server.is_running is True
        
        await self.ws_server.stop()
        assert self.ws_server.is_running is False


if __name__ == "__main__":
    pytest.main(["-xvs", "test_real_time_metrics.py"])