"""
Tests for the Shared Memory components.

This module contains tests for the SharedMemoryManager, SharedMetricsStore,
and SharedStateManager classes.
"""

import os
import time
import asyncio
import unittest
import tempfile
import shutil
from typing import Dict, Any

from arbitrage_bot.core.optimization.shared_memory import (
    SharedMemoryManager,
    SharedMetricsStore,
    SharedStateManager,
    MemoryRegionType,
    MemoryRegionNotFoundError,
    SchemaValidationError
)

class TestSharedMemoryManager(unittest.TestCase):
    """Tests for the SharedMemoryManager class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create temporary directory for test
        self.test_dir = tempfile.mkdtemp()
        
        # Create shared memory manager
        self.memory_manager = SharedMemoryManager(base_dir=self.test_dir)
        
        # Event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Clean up the test environment."""
        # Close the event loop
        self.loop.close()
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_create_region(self):
        """Test creating a memory region."""
        # Create region
        region_info = self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region",
                size=1024,
                region_type=MemoryRegionType.METRICS
            )
        )
        
        # Check region info
        self.assertEqual(region_info.name, "test_region")
        self.assertEqual(region_info.size, 1024)
        self.assertEqual(region_info.type, MemoryRegionType.METRICS)
        
        # Check that region file exists
        self.assertTrue(os.path.exists(region_info.path))
        
        # Check that region is in registry
        registry = self.loop.run_until_complete(self.memory_manager._load_registry())
        self.assertIn("test_region", registry)
    
    def test_get_region_info(self):
        """Test getting region info."""
        # Create region
        self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region",
                size=1024,
                region_type=MemoryRegionType.METRICS
            )
        )
        
        # Get region info
        region_info = self.loop.run_until_complete(
            self.memory_manager.get_region_info("test_region")
        )
        
        # Check region info
        self.assertEqual(region_info.name, "test_region")
        self.assertEqual(region_info.size, 1024)
        self.assertEqual(region_info.type, MemoryRegionType.METRICS)
    
    def test_list_regions(self):
        """Test listing regions."""
        # Create regions
        self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region1",
                size=1024,
                region_type=MemoryRegionType.METRICS
            )
        )
        self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region2",
                size=2048,
                region_type=MemoryRegionType.STATE
            )
        )
        
        # List all regions
        regions = self.loop.run_until_complete(
            self.memory_manager.list_regions()
        )
        
        # Check regions
        self.assertEqual(len(regions), 2)
        self.assertEqual(regions[0].name, "test_region1")
        self.assertEqual(regions[1].name, "test_region2")
        
        # List regions by type
        metrics_regions = self.loop.run_until_complete(
            self.memory_manager.list_regions(region_type=MemoryRegionType.METRICS)
        )
        state_regions = self.loop.run_until_complete(
            self.memory_manager.list_regions(region_type=MemoryRegionType.STATE)
        )
        
        # Check regions by type
        self.assertEqual(len(metrics_regions), 1)
        self.assertEqual(metrics_regions[0].name, "test_region1")
        self.assertEqual(len(state_regions), 1)
        self.assertEqual(state_regions[0].name, "test_region2")
    
    def test_delete_region(self):
        """Test deleting a region."""
        # Create region
        region_info = self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region",
                size=1024,
                region_type=MemoryRegionType.METRICS
            )
        )
        
        # Delete region
        result = self.loop.run_until_complete(
            self.memory_manager.delete_region("test_region")
        )
        
        # Check result
        self.assertTrue(result)
        
        # Check that region file doesn't exist
        self.assertFalse(os.path.exists(region_info.path))
        
        # Check that region is not in registry
        registry = self.loop.run_until_complete(self.memory_manager._load_registry())
        self.assertNotIn("test_region", registry)
        
        # Check that getting region info raises exception
        with self.assertRaises(MemoryRegionNotFoundError):
            self.loop.run_until_complete(
                self.memory_manager.get_region_info("test_region")
            )
    
    def test_write_read_data(self):
        """Test writing and reading data."""
        # Create region
        self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region",
                size=1024,
                region_type=MemoryRegionType.METRICS
            )
        )
        
        # Write data
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        bytes_written = self.loop.run_until_complete(
            self.memory_manager.write_data("test_region", test_data)
        )
        
        # Check bytes written
        self.assertGreater(bytes_written, 0)
        
        # Read data
        read_data = self.loop.run_until_complete(
            self.memory_manager.read_data("test_region")
        )
        
        # Check data
        self.assertEqual(read_data, test_data)
    
    def test_update_data(self):
        """Test updating data."""
        # Create region
        self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region",
                size=1024,
                region_type=MemoryRegionType.METRICS
            )
        )
        
        # Write initial data
        initial_data = {"key": "value", "number": 42}
        self.loop.run_until_complete(
            self.memory_manager.write_data("test_region", initial_data)
        )
        
        # Update data
        def update_func(data):
            data["number"] += 1
            data["new_key"] = "new_value"
            return data
        
        bytes_written = self.loop.run_until_complete(
            self.memory_manager.update_data("test_region", update_func)
        )
        
        # Check bytes written
        self.assertGreater(bytes_written, 0)
        
        # Read updated data
        updated_data = self.loop.run_until_complete(
            self.memory_manager.read_data("test_region")
        )
        
        # Check updated data
        self.assertEqual(updated_data["key"], "value")
        self.assertEqual(updated_data["number"], 43)
        self.assertEqual(updated_data["new_key"], "new_value")
    
    def test_schema_validation(self):
        """Test schema validation."""
        # Create region with schema
        schema = {
            "name": "string",
            "age": "number",
            "active": "boolean"
        }
        self.loop.run_until_complete(
            self.memory_manager.create_region(
                name="test_region",
                size=1024,
                region_type=MemoryRegionType.METRICS,
                schema=schema
            )
        )
        
        # Valid data
        valid_data = {
            "name": "John",
            "age": 30,
            "active": True
        }
        
        # Write valid data
        bytes_written = self.loop.run_until_complete(
            self.memory_manager.write_data("test_region", valid_data)
        )
        
        # Check bytes written
        self.assertGreater(bytes_written, 0)
        
        # Invalid data
        invalid_data = {
            "name": "John",
            "age": "thirty",  # Should be a number
            "active": True
        }
        
        # Write invalid data
        with self.assertRaises(SchemaValidationError):
            self.loop.run_until_complete(
                self.memory_manager.write_data("test_region", invalid_data)
            )

class TestSharedMetricsStore(unittest.TestCase):
    """Tests for the SharedMetricsStore class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create temporary directory for test
        self.test_dir = tempfile.mkdtemp()
        
        # Create shared memory manager
        self.memory_manager = SharedMemoryManager(base_dir=self.test_dir)
        
        # Create metrics store
        self.metrics_store = SharedMetricsStore(self.memory_manager)
        
        # Event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize metrics store
        self.loop.run_until_complete(self.metrics_store.initialize())
    
    def tearDown(self):
        """Clean up the test environment."""
        # Close the event loop
        self.loop.close()
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_store_get_metrics(self):
        """Test storing and getting metrics."""
        # Store metrics
        test_metrics = {"cpu": 50.0, "memory": 75.0}
        self.loop.run_until_complete(
            self.metrics_store.store_metrics("system", test_metrics)
        )
        
        # Get metrics
        metrics = self.loop.run_until_complete(
            self.metrics_store.get_metrics("system")
        )
        
        # Check metrics
        self.assertEqual(metrics, test_metrics)
    
    def test_ttl(self):
        """Test TTL-based cache invalidation."""
        # Set TTL
        self.loop.run_until_complete(
            self.metrics_store.set_ttl("system", 0.1)  # 100ms TTL
        )
        
        # Store metrics
        test_metrics = {"cpu": 50.0, "memory": 75.0}
        self.loop.run_until_complete(
            self.metrics_store.store_metrics("system", test_metrics)
        )
        
        # Get metrics immediately
        metrics = self.loop.run_until_complete(
            self.metrics_store.get_metrics("system")
        )
        
        # Check metrics
        self.assertEqual(metrics, test_metrics)
        
        # Wait for TTL to expire
        time.sleep(0.2)
        
        # Get metrics after TTL expired
        metrics = self.loop.run_until_complete(
            self.metrics_store.get_metrics("system")
        )
        
        # Check metrics (should be None)
        self.assertIsNone(metrics)
    
    def test_update_metrics(self):
        """Test updating metrics."""
        # Store initial metrics
        initial_metrics = {"cpu": 50.0, "memory": 75.0}
        self.loop.run_until_complete(
            self.metrics_store.store_metrics("system", initial_metrics)
        )
        
        # Update metrics
        def update_func(metrics):
            metrics["cpu"] = 60.0
            metrics["disk"] = 80.0
            return metrics
        
        self.loop.run_until_complete(
            self.metrics_store.update_metrics("system", update_func)
        )
        
        # Get updated metrics
        updated_metrics = self.loop.run_until_complete(
            self.metrics_store.get_metrics("system")
        )
        
        # Check updated metrics
        self.assertEqual(updated_metrics["cpu"], 60.0)
        self.assertEqual(updated_metrics["memory"], 75.0)
        self.assertEqual(updated_metrics["disk"], 80.0)
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        # Store metrics
        system_metrics = {"cpu": 50.0, "memory": 75.0}
        market_metrics = {"eth_price": 3000.0, "btc_price": 50000.0}
        
        self.loop.run_until_complete(
            self.metrics_store.store_metrics("system", system_metrics)
        )
        self.loop.run_until_complete(
            self.metrics_store.store_metrics("market", market_metrics)
        )
        
        # Get all metrics
        all_metrics = self.loop.run_until_complete(
            self.metrics_store.get_all_metrics()
        )
        
        # Check all metrics
        self.assertEqual(len(all_metrics), 2)
        self.assertEqual(all_metrics["system"], system_metrics)
        self.assertEqual(all_metrics["market"], market_metrics)

class TestSharedStateManager(unittest.TestCase):
    """Tests for the SharedStateManager class."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create temporary directory for test
        self.test_dir = tempfile.mkdtemp()
        
        # Create shared memory manager
        self.memory_manager = SharedMemoryManager(base_dir=self.test_dir)
        
        # Create state manager
        self.state_manager = SharedStateManager(self.memory_manager)
        
        # Event loop for async tests
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize state manager
        self.loop.run_until_complete(self.state_manager.initialize())
    
    def tearDown(self):
        """Clean up the test environment."""
        # Close the event loop
        self.loop.close()
        
        # Remove temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_set_get_state(self):
        """Test setting and getting state."""
        # Set state
        test_state = {"key": "value", "number": 42}
        version = self.loop.run_until_complete(
            self.state_manager.set_state("test_state", test_state)
        )
        
        # Check version
        self.assertEqual(version, 1)
        
        # Get state
        state, state_version = self.loop.run_until_complete(
            self.state_manager.get_state("test_state")
        )
        
        # Check state
        self.assertEqual(state, test_state)
        self.assertEqual(state_version, 1)
    
    def test_version_conflict(self):
        """Test version conflict resolution."""
        # Set initial state
        initial_state = {"key": "value", "number": 42}
        version = self.loop.run_until_complete(
            self.state_manager.set_state("test_state", initial_state)
        )
        
        # Check version
        self.assertEqual(version, 1)
        
        # Update state with correct version
        updated_state = {"key": "new_value", "number": 43}
        new_version = self.loop.run_until_complete(
            self.state_manager.set_state("test_state", updated_state, version=1)
        )
        
        # Check new version
        self.assertEqual(new_version, 2)
        
        # Update state with incorrect version
        with self.assertRaises(ValueError):
            self.loop.run_until_complete(
                self.state_manager.set_state("test_state", {"key": "value"}, version=1)
            )
        
        # Get state
        state, state_version = self.loop.run_until_complete(
            self.state_manager.get_state("test_state")
        )
        
        # Check state
        self.assertEqual(state, updated_state)
        self.assertEqual(state_version, 2)
    
    def test_change_notification(self):
        """Test change notification."""
        # Create a callback
        callback_called = False
        callback_state = None
        callback_version = None
        
        def callback(state, version):
            nonlocal callback_called, callback_state, callback_version
            callback_called = True
            callback_state = state
            callback_version = version
        
        # Register callback
        self.loop.run_until_complete(
            self.state_manager.register_change_callback("test_state", callback)
        )
        
        # Set state
        test_state = {"key": "value", "number": 42}
        version = self.loop.run_until_complete(
            self.state_manager.set_state("test_state", test_state)
        )
        
        # Check callback
        self.assertTrue(callback_called)
        self.assertEqual(callback_state, test_state)
        self.assertEqual(callback_version, version)

if __name__ == "__main__":
    unittest.main()