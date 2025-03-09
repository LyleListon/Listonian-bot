"""Integration tests for performance optimization."""

import pytest
import asyncio
import time
from unittest.mock import patch
from typing import Dict, Any
from arbitrage_bot.core.optimization.performance import PerformanceOptimizer

@pytest.fixture
async def optimizer(config, mock_process, mock_network, monkeypatch):
    """Initialize performance optimizer with mocks."""
    # Mock psutil.Process
    monkeypatch.setattr("psutil.Process", lambda: mock_process)
    
    # Mock psutil.net_io_counters
    monkeypatch.setattr("psutil.net_io_counters", lambda: mock_network)
    
    optimizer = PerformanceOptimizer(config)
    return optimizer

@pytest.mark.asyncio
class TestPerformanceOptimizer:
    """Test performance optimization functionality."""
    
    async def test_resource_monitoring(self, optimizer, mock_process, mock_network):
        """Test resource monitoring."""
        # Set initial values
        mock_process.memory_info_value = 100 * 1024 * 1024  # 100MB
        mock_process.cpu_percent_value = 10.0
        mock_network.update(1000000, 2000000)  # 1MB sent, 2MB received
        
        # Get initial metrics
        metrics = await optimizer.get_metrics()
        assert metrics is not None
        assert metrics.memory_usage == 100  # MB
        assert metrics.cpu_usage == 10.0
        assert metrics.network_rx == 0  # First call establishes baseline
        assert metrics.network_tx == 0
        
        # Update mock values
        mock_process.memory_info_value = 150 * 1024 * 1024  # 150MB
        mock_process.cpu_percent_value = 20.0
        mock_network.update(1500000, 3000000)  # +0.5MB sent, +1MB received
        
        await asyncio.sleep(1)  # Wait for network stats interval
        
        # Get updated metrics
        new_metrics = await optimizer.get_metrics()
        assert new_metrics.memory_usage == 150  # MB
        assert new_metrics.cpu_usage == 20.0
        assert new_metrics.network_rx > 0
        assert new_metrics.network_tx > 0
        
    async def test_cache_management(self, optimizer):
        """Test cache management."""
        # Test basic cache operations
        optimizer.cache_set("test_key", "test_value")
        assert optimizer.cache_get("test_key") == "test_value"
        assert optimizer._cache_hits == 1
        assert optimizer._cache_misses == 0
        
        # Test cache miss
        assert optimizer.cache_get("nonexistent") is None
        assert optimizer._cache_hits == 1
        assert optimizer._cache_misses == 1
        
        # Test TTL expiration
        optimizer.cache_ttl = 0.1  # 100ms
        optimizer.cache_set("ttl_test", "test_value")
        await asyncio.sleep(0.2)
        assert optimizer.cache_get("ttl_test") is None
        assert optimizer._cache_misses == 2
        
        # Test size limit
        optimizer.cache_size = 2
        optimizer.cache_set("key1", "value1")
        optimizer.cache_set("key2", "value2")
        optimizer.cache_set("key3", "value3")  # Should evict oldest
        assert optimizer.cache_get("key1") is None  # Evicted
        assert optimizer.cache_get("key2") == "value2"
        assert optimizer.cache_get("key3") == "value3"
        
    async def test_task_prioritization(self, optimizer, mock_task):
        """Test task prioritization."""
        # Create tasks with different priorities
        high_task = mock_task()
        high_task.priority = 100
        high_task.name = "high_priority"
        
        med_task = mock_task()
        med_task.priority = 50
        med_task.name = "medium_priority"
        
        low_task = mock_task()
        low_task.priority = 10
        low_task.name = "low_priority"
        
        # Track tasks
        optimizer.track_task(high_task)
        optimizer.track_task(med_task)
        optimizer.track_task(low_task)
        
        assert len(optimizer._active_tasks) == 3
        
        # Simulate high CPU usage
        mock_process = optimizer._get_process()
        mock_process.cpu_percent_value = 95.0  # Above 90% threshold
        
        # Run optimization
        await optimizer.optimize_resources()
        
        # Verify low priority task was cancelled
        assert low_task.cancelled
        assert not high_task.cancelled
        assert not med_task.cancelled
        
    async def test_resource_optimization(self, optimizer, mock_process):
        """Test resource optimization."""
        # Set up test data
        test_data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        
        # Fill cache
        for key, value in test_data.items():
            optimizer.cache_set(key, value)
            
        # Simulate high memory usage
        mock_process.memory_info_value = int(optimizer.max_memory * 1024 * 1024 * 0.95)  # 95% of max
        
        # Run optimization
        await optimizer.optimize_resources()
        
        # Verify cache was cleared
        assert len(optimizer._cache) == 0
        assert len(optimizer._cache_timestamps) == 0
        
        # Verify stats
        stats = optimizer.get_optimization_stats()
        assert stats["cache"]["size"] == 0
            
    async def test_performance_stats(self, optimizer, mock_process, mock_network):
        """Test performance statistics."""
        # Set up test metrics
        mock_process.memory_info_value = 200 * 1024 * 1024  # 200MB
        mock_process.cpu_percent_value = 30.0
        mock_network.update(5000000, 10000000)  # 5MB sent, 10MB received
        
        # Generate metrics history
        for _ in range(5):
            await optimizer.get_metrics()
            await asyncio.sleep(0.1)
            
        # Add some cache activity
        optimizer.cache_set("test1", "value1")
        optimizer.cache_get("test1")  # Hit
        optimizer.cache_get("missing")  # Miss
        
        # Get stats
        stats = optimizer.get_optimization_stats()
        
        # Verify metrics
        assert stats["metrics"]["memory_usage"] == 200
        assert stats["metrics"]["cpu_usage"] == 30.0
        assert stats["metrics"]["network_rx"] >= 0
        assert stats["metrics"]["network_tx"] >= 0
        
        # Verify cache stats
        assert stats["cache"]["size"] == 1
        assert stats["cache"]["hits"] == 1
        assert stats["cache"]["misses"] == 1
        assert stats["cache"]["hit_ratio"] == 0.5
        
        # Verify task stats
        assert stats["tasks"]["active"] == 0
        assert stats["tasks"]["max"] == optimizer.max_tasks
