"""Integration tests for process management."""

import pytest
import asyncio
import os
import psutil
from pathlib import Path
from typing import Dict, Any
from arbitrage_bot.core.process.manager import ProcessManager
from arbitrage_bot.utils.config_loader import load_config

@pytest.fixture
async def config():
    """Load test configuration."""
    return load_config()

@pytest.fixture
async def manager(config):
    """Initialize process manager."""
    return ProcessManager(config)

class TestProcessManager:
    """Test process management functionality."""
    
    @pytest.mark.asyncio
    async def test_instance_lifecycle(self, manager):
        """Test instance start/stop lifecycle."""
        # Start instance
        instance_id = "test_instance_1"
        success = await manager.start_instance(instance_id)
        assert success is True
        
        # Verify instance running
        info = manager.get_instance_info(instance_id)
        assert info is not None
        assert info["status"] == "starting"
        assert info["pid"] > 0
        
        # Stop instance
        success = await manager.stop_instance(instance_id)
        assert success is True
        
        # Verify instance stopped
        info = manager.get_instance_info(instance_id)
        assert info is None
        
    @pytest.mark.asyncio
    async def test_port_allocation(self, manager):
        """Test port allocation and release."""
        # Start multiple instances
        instance_ids = ["test_1", "test_2", "test_3"]
        allocated_ports = set()
        
        for instance_id in instance_ids:
            success = await manager.start_instance(instance_id)
            assert success is True
            
            # Verify port allocation
            info = manager.get_instance_info(instance_id)
            assert info is not None
            
            # Check dashboard port
            dashboard_port = info["ports"]["dashboard"]
            assert dashboard_port not in allocated_ports
            assert 5000 <= dashboard_port <= 5010
            allocated_ports.add(dashboard_port)
            
            # Check websocket port
            ws_port = info["ports"]["websocket"]
            assert ws_port not in allocated_ports
            assert 8771 <= ws_port <= 8780
            allocated_ports.add(ws_port)
            
        # Stop instances and verify port release
        for instance_id in instance_ids:
            success = await manager.stop_instance(instance_id)
            assert success is True
            
        # Verify all ports released
        assert len(manager.allocated_ports) == 0
        
    @pytest.mark.asyncio
    async def test_resource_limits(self, manager):
        """Test resource limits enforcement."""
        # Try to exceed max instances
        max_instances = manager.max_instances
        instances = []
        
        for i in range(max_instances + 1):
            success = await manager.start_instance(f"test_{i}")
            if i < max_instances:
                assert success is True
                instances.append(f"test_{i}")
            else:
                assert success is False
                
        # Clean up
        for instance_id in instances:
            await manager.stop_instance(instance_id)
            
    @pytest.mark.asyncio
    async def test_heartbeat_monitoring(self, manager):
        """Test heartbeat monitoring."""
        # Start instance
        instance_id = "test_heartbeat"
        await manager.start_instance(instance_id)
        
        # Send heartbeats
        for _ in range(3):
            success = await manager.heartbeat(instance_id)
            assert success is True
            await asyncio.sleep(0.1)
            
        # Start monitoring
        monitor_task = asyncio.create_task(
            manager.monitor_instances()
        )
        
        # Wait for heartbeat timeout
        await asyncio.sleep(
            manager.heartbeat_timeout + 1
        )
        
        # Verify instance stopped
        info = manager.get_instance_info(instance_id)
        assert info is None
        
        # Clean up
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_state_persistence(self, manager):
        """Test state persistence."""
        # Start instance
        instance_id = "test_state"
        await manager.start_instance(instance_id)
        
        # Verify state file created
        assert manager.state_file.exists()
        
        # Create new manager
        new_manager = ProcessManager(manager.config)
        
        # Verify state loaded
        info = new_manager.get_instance_info(instance_id)
        assert info is not None
        assert info["pid"] > 0
        
        # Clean up
        await manager.stop_instance(instance_id)
        
    @pytest.mark.asyncio
    async def test_instance_monitoring(self, manager):
        """Test instance monitoring."""
        # Start instance
        instance_id = "test_monitor"
        await manager.start_instance(instance_id)
        
        # Get initial metrics
        info = manager.get_instance_info(instance_id)
        assert info is not None
        initial_memory = info["memory_mb"]
        
        # Create some load
        data = [i for i in range(1000000)]
        await asyncio.sleep(0.1)
        
        # Start monitoring
        monitor_task = asyncio.create_task(
            manager.monitor_instances()
        )
        await asyncio.sleep(1)
        
        # Verify metrics updated
        info = manager.get_instance_info(instance_id)
        assert info["memory_mb"] > initial_memory
        
        # Clean up
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
            
        await manager.stop_instance(instance_id)
        
    @pytest.mark.asyncio
    async def test_instance_recovery(self, manager):
        """Test instance recovery after failure."""
        # Start instance
        instance_id = "test_recovery"
        await manager.start_instance(instance_id)
        
        # Get process
        info = manager.get_instance_info(instance_id)
        process = psutil.Process(info["pid"])
        
        # Kill process
        process.kill()
        
        # Start monitoring
        monitor_task = asyncio.create_task(
            manager.monitor_instances()
        )
        await asyncio.sleep(1)
        
        # Verify instance removed
        info = manager.get_instance_info(instance_id)
        assert info is None
        
        # Clean up
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
