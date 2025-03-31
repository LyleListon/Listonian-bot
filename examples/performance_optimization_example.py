"""
Performance Optimization Example

This example demonstrates how to use the performance optimization components:
- Memory-Mapped Files
- WebSocket Optimization
- Resource Management
"""

import os
import sys
import time
import json
import asyncio
import logging
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arbitrage_bot.core.optimization.shared_memory import (
    SharedMemoryManager, 
    SharedMetricsStore, 
    SharedStateManager,
    MemoryRegionType
)
from arbitrage_bot.core.optimization.websocket_optimization import (
    OptimizedWebSocketClient,
    WebSocketConnectionPool,
    MessageFormat,
    MessagePriority
)
from arbitrage_bot.core.optimization.resource_manager import (
    ResourceManager,
    ResourceType,
    TaskPriority
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Example data
EXAMPLE_METRICS = {
    "system": {
        "cpu_percent": 25.5,
        "memory_percent": 45.2,
        "disk_percent": 68.7
    },
    "market": {
        "eth_price": 3450.75,
        "btc_price": 65432.10,
        "gas_price": 25.5
    },
    "performance": {
        "transactions_per_second": 125,
        "average_latency": 0.45,
        "success_rate": 99.8
    }
}

EXAMPLE_STATE = {
    "arbitrage_opportunities": [
        {
            "pair": "ETH/USDC",
            "dex1": "Uniswap",
            "dex2": "Sushiswap",
            "profit_percent": 0.25,
            "timestamp": time.time()
        },
        {
            "pair": "BTC/USDT",
            "dex1": "Pancakeswap",
            "dex2": "Uniswap",
            "profit_percent": 0.18,
            "timestamp": time.time()
        }
    ],
    "active_trades": 3,
    "total_profit": 1250.75
}

async def example_task(name: str, duration: float) -> str:
    """Example task that simulates work."""
    logger.info(f"Task {name} started")
    await asyncio.sleep(duration)
    logger.info(f"Task {name} completed after {duration} seconds")
    return f"Result from {name}"

async def demonstrate_shared_memory():
    """Demonstrate shared memory components."""
    logger.info("=== Demonstrating Shared Memory ===")
    
    # Create shared memory manager
    memory_manager = SharedMemoryManager()
    
    # Create metrics store
    metrics_store = SharedMetricsStore(memory_manager)
    await metrics_store.initialize()
    
    # Create state manager
    state_manager = SharedStateManager(memory_manager)
    await state_manager.initialize()
    
    # Store metrics
    logger.info("Storing metrics...")
    await metrics_store.store_metrics("system", EXAMPLE_METRICS["system"])
    await metrics_store.store_metrics("market", EXAMPLE_METRICS["market"])
    await metrics_store.store_metrics("performance", EXAMPLE_METRICS["performance"])
    
    # Set TTL for different metric types
    await metrics_store.set_ttl("system", 5.0)  # 5 seconds TTL
    await metrics_store.set_ttl("market", 10.0)  # 10 seconds TTL
    await metrics_store.set_ttl("performance", 30.0)  # 30 seconds TTL
    
    # Get metrics
    logger.info("Getting metrics...")
    system_metrics = await metrics_store.get_metrics("system")
    market_metrics = await metrics_store.get_metrics("market")
    performance_metrics = await metrics_store.get_metrics("performance")
    
    logger.info(f"System metrics: {system_metrics}")
    logger.info(f"Market metrics: {market_metrics}")
    logger.info(f"Performance metrics: {performance_metrics}")
    
    # Get all metrics
    all_metrics = await metrics_store.get_all_metrics()
    logger.info(f"All metrics: {all_metrics.keys()}")
    
    # Update metrics
    logger.info("Updating metrics...")
    await metrics_store.update_metrics("system", lambda m: {**m, "cpu_percent": 30.0})
    
    # Get updated metrics
    updated_system_metrics = await metrics_store.get_metrics("system")
    logger.info(f"Updated system metrics: {updated_system_metrics}")
    
    # Store state
    logger.info("Storing state...")
    version = await state_manager.set_state("arbitrage", EXAMPLE_STATE)
    logger.info(f"State stored with version {version}")
    
    # Get state
    logger.info("Getting state...")
    state, state_version = await state_manager.get_state("arbitrage")
    logger.info(f"State: {state}")
    logger.info(f"State version: {state_version}")
    
    # Update state
    logger.info("Updating state...")
    new_version = await state_manager.set_state(
        "arbitrage",
        {**state, "total_profit": 1300.50},
        version=state_version
    )
    logger.info(f"State updated with version {new_version}")
    
    # Get updated state
    updated_state, updated_version = await state_manager.get_state("arbitrage")
    logger.info(f"Updated state: {updated_state}")
    logger.info(f"Updated state version: {updated_version}")
    
    # Clean up
    await memory_manager.delete_region("metrics_registry")
    await memory_manager.delete_region("state_registry")
    for region in await memory_manager.list_regions():
        await memory_manager.delete_region(region.name)

async def demonstrate_websocket_optimization():
    """Demonstrate WebSocket optimization components."""
    logger.info("=== Demonstrating WebSocket Optimization ===")
    
    # Create a simple echo server for testing
    async def echo_server(websocket, path):
        async for message in websocket:
            try:
                data = json.loads(message)
                await websocket.send(json.dumps({
                    "type": "echo",
                    "data": data,
                    "timestamp": time.time()
                }))
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": time.time()
                }))
    
    # Start server
    import websockets
    server = await websockets.serve(echo_server, "localhost", 8765)
    
    try:
        # Create optimized WebSocket client
        client = OptimizedWebSocketClient(
            url="ws://localhost:8765",
            format=MessageFormat.MSGPACK,
            batch_size=5,
            batch_interval=0.5
        )
        
        # Connect to server
        await client.connect()
        
        # Register message handler
        async def handle_echo(data):
            logger.info(f"Received echo: {data}")
        
        await client.register_handler("echo", handle_echo)
        
        # Send messages with different priorities
        logger.info("Sending messages...")
        for i in range(10):
            await client.send(
                {"message": f"Hello {i}", "timestamp": time.time()},
                priority=MessagePriority.NORMAL if i % 2 == 0 else MessagePriority.HIGH
            )
        
        # Wait for messages to be processed
        await asyncio.sleep(2)
        
        # Create connection pool
        pool = WebSocketConnectionPool(
            max_connections=3,
            format=MessageFormat.MSGPACK,
            batch_size=5,
            batch_interval=0.5
        )
        
        # Get connection from pool
        logger.info("Using connection pool...")
        connection = await pool.get_connection("ws://localhost:8765")
        
        # Register handler
        await pool.register_handler("ws://localhost:8765", "echo", handle_echo)
        
        # Send messages through pool
        for i in range(5):
            await pool.send(
                "ws://localhost:8765",
                {"message": f"Pool message {i}", "timestamp": time.time()},
                priority=MessagePriority.NORMAL
            )
        
        # Wait for messages to be processed
        await asyncio.sleep(2)
        
        # Disconnect
        await client.disconnect()
        await pool.disconnect_all()
        
    finally:
        # Stop server
        server.close()
        await server.wait_closed()

async def demonstrate_resource_management():
    """Demonstrate resource management components."""
    logger.info("=== Demonstrating Resource Management ===")
    
    # Create resource manager
    resource_manager = ResourceManager(
        num_workers=4,
        max_cpu_percent=80.0,
        max_memory_percent=80.0,
        max_io_workers=2,
        max_batch_size=10,
        batch_interval=0.1
    )
    
    # Start resource manager
    await resource_manager.start()
    
    try:
        # Create object pool
        await resource_manager.create_object_pool(
            "connection_pool",
            factory=lambda: {"connection": f"conn_{time.time()}", "created_at": time.time()},
            max_size=5,
            ttl=30.0
        )
        
        # Get objects from pool
        logger.info("Getting objects from pool...")
        obj1 = await resource_manager.get_object("connection_pool")
        obj2 = await resource_manager.get_object("connection_pool")
        logger.info(f"Object 1: {obj1}")
        logger.info(f"Object 2: {obj2}")
        
        # Release objects back to pool
        resource_manager.release_object("connection_pool", obj1)
        resource_manager.release_object("connection_pool", obj2)
        
        # Submit tasks
        logger.info("Submitting tasks...")
        results = []
        for i in range(10):
            priority = TaskPriority.HIGH if i % 3 == 0 else TaskPriority.NORMAL
            result = await resource_manager.submit_task(
                example_task,
                f"Task {i}",
                0.5,
                priority=priority,
                resource_type=ResourceType.CPU,
                timeout=2.0
            )
            results.append(result)
        
        logger.info(f"Task results: {results}")
        
        # Read and write files
        logger.info("Reading and writing files...")
        
        # Write test file
        test_file = "test_data.json"
        test_data = {"data": EXAMPLE_METRICS, "timestamp": time.time()}
        bytes_written = await resource_manager.write_file(
            test_file,
            json.dumps(test_data, indent=2),
            binary=False,
            priority=TaskPriority.NORMAL
        )
        logger.info(f"Wrote {bytes_written} bytes to {test_file}")
        
        # Read test file
        file_content = await resource_manager.read_file(
            test_file,
            binary=False,
            priority=TaskPriority.NORMAL
        )
        logger.info(f"Read {len(file_content)} bytes from {test_file}")
        
        # Get resource usage
        usage = await resource_manager.get_resource_usage()
        logger.info(f"Resource usage: CPU {usage.cpu_percent:.1f}%, Memory {usage.memory_percent:.1f}%")
        
        # Get statistics
        stats = resource_manager.get_stats()
        logger.info(f"Resource manager stats: {stats.keys()}")
        
    finally:
        # Clean up
        await resource_manager.stop()
        
        # Remove test file
        if os.path.exists("test_data.json"):
            os.remove("test_data.json")

async def main():
    """Main function."""
    logger.info("Starting Performance Optimization Example")
    
    # Demonstrate shared memory
    await demonstrate_shared_memory()
    
    # Demonstrate WebSocket optimization
    await demonstrate_websocket_optimization()
    
    # Demonstrate resource management
    await demonstrate_resource_management()
    
    logger.info("Performance Optimization Example completed")

if __name__ == "__main__":
    asyncio.run(main())