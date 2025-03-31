"""Example demonstrating the real-time metrics optimization components.

This script shows how to use the TaskManager, ConnectionManager, and MetricsService
classes to implement efficient real-time metrics collection and distribution.
"""

import asyncio
import logging
import time
import json
import sys
import os
import signal
from aiohttp import web
import psutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from arbitrage_bot.dashboard.task_manager import TaskManager, TaskState
from arbitrage_bot.dashboard.connection_manager import ConnectionManager, ConnectionState
from arbitrage_bot.dashboard.metrics_service import MetricsService, MetricsType

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockMarketAnalyzer:
    """Mock market analyzer for demonstration."""
    
    async def get_market_summary(self):
        """Get mock market data."""
        return {
            "prices": {
                "ETH/USD": 3500.25,
                "BTC/USD": 65000.75,
                "LINK/USD": 18.45
            },
            "volume_24h": {
                "ETH/USD": 1250000,
                "BTC/USD": 3500000,
                "LINK/USD": 750000
            },
            "timestamp": time.time()
        }


class MockPortfolioTracker:
    """Mock portfolio tracker for demonstration."""
    
    async def get_performance_summary(self):
        """Get mock portfolio data."""
        return {
            "total_trades": 125,
            "total_profit": 1250.75,
            "average_gas_used": 150000,
            "total_gas_cost": 12.5,
            "last_24h_stats": {
                "trade_count": 15,
                "profit": 125.5,
                "avg_gas": 145000,
                "gas_cost": 1.5
            }
        }


class ExampleWebSocketServer:
    """Example WebSocket server using the optimized components."""
    
    def __init__(self):
        """Initialize the example server."""
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.on_startup.append(self.on_startup)
        self.app.on_shutdown.append(self.on_shutdown)
        
        # Initialize components
        self.task_manager = TaskManager()
        self.connection_manager = ConnectionManager(self.task_manager)
        self.metrics_service = MetricsService()
        
        # Mock data sources
        self.market_analyzer = MockMarketAnalyzer()
        self.portfolio_tracker = MockPortfolioTracker()
        
        # Register metrics collectors
        self._register_metrics_collectors()
        
        # Flag for running state
        self.is_running = False
        
        logger.info("Example WebSocket server initialized")
        
    async def on_startup(self, app):
        """Handle application startup."""
        # Start metrics service
        await self.metrics_service.start()
        
        # Start background tasks
        self.is_running = True
        await self.task_manager.add_task(
            "housekeeping", 
            self._housekeeping_task()
        )
        
        # Add simulated load task
        await self.task_manager.add_task(
            "simulated_load",
            self._simulated_load_task()
        )
        
        logger.info("Example WebSocket server started")
        
    async def on_shutdown(self, app):
        """Handle application shutdown."""
        self.is_running = False
        
        # Stop metrics service
        await self.metrics_service.stop()
        
        # Cancel all tasks
        await self.task_manager.cancel_all_tasks()
        
        # Disconnect all clients
        await self.connection_manager.disconnect_all()
        
        logger.info("Example WebSocket server stopped")
        
    async def handle_index(self, request):
        """Handle index page request."""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Real-Time Metrics Example</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; }
                #metrics { 
                    border: 1px solid #ccc; 
                    padding: 10px; 
                    margin-top: 20px;
                    min-height: 300px;
                    white-space: pre-wrap;
                    font-family: monospace;
                }
                .stats {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 20px;
                    margin-bottom: 20px;
                }
                .stat-card {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    min-width: 200px;
                }
                .stat-title {
                    font-weight: bold;
                    margin-bottom: 10px;
                }
            </style>
        </head>
        <body>
            <h1>Real-Time Metrics Example</h1>
            <p>This page demonstrates the real-time metrics optimization components.</p>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-title">Connections</div>
                    <div id="connections">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Tasks</div>
                    <div id="tasks">-</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">System</div>
                    <div id="system">-</div>
                </div>
            </div>
            
            <h2>Metrics Stream</h2>
            <div id="metrics"></div>
            
            <script>
                const metricsDiv = document.getElementById('metrics');
                const connectionsDiv = document.getElementById('connections');
                const tasksDiv = document.getElementById('tasks');
                const systemDiv = document.getElementById('system');
                
                // Connect to WebSocket
                const ws = new WebSocket(`ws://${window.location.host}/ws`);
                
                ws.onopen = function() {
                    metricsDiv.textContent += "Connected to WebSocket server\\n";
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    metricsDiv.textContent = `Received ${data.type}:\\n${JSON.stringify(data.data, null, 2)}\\n\\n` + metricsDiv.textContent;
                    
                    // Update stat cards
                    if (data.type === 'connections_update') {
                        connectionsDiv.textContent = `Active: ${data.data.active_connections}`;
                    }
                    if (data.type === 'tasks_update') {
                        tasksDiv.textContent = `Running: ${data.data.running}, Total: ${data.data.total}`;
                    }
                    if (data.type === 'system_update') {
                        systemDiv.textContent = `CPU: ${data.data.system.cpu_percent}%, Memory: ${data.data.system.memory_percent}%`;
                    }
                    
                    // Limit the number of messages shown
                    const lines = metricsDiv.textContent.split('\\n');
                    if (lines.length > 100) {
                        metricsDiv.textContent = lines.slice(0, 100).join('\\n');
                    }
                };
                
                ws.onclose = function() {
                    metricsDiv.textContent += "Disconnected from WebSocket server\\n";
                };
                
                ws.onerror = function(error) {
                    metricsDiv.textContent += `WebSocket error: ${error}\\n`;
                };
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
        
    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Create a queue for this connection
        metrics_queue = asyncio.Queue(maxsize=100)
        
        # Register connection with connection manager
        await self.connection_manager.connect(ws)
        
        # Register queue with metrics service
        await self.metrics_service.register_subscriber(metrics_queue)
        
        # Register queue with connection manager
        await self.connection_manager.register_queue(ws, metrics_queue, "metrics_queue")
        
        try:
            # Start message consumer task
            await self.connection_manager.register_task(
                ws, 
                "message_consumer", 
                self._message_consumer(ws, metrics_queue)
            )
            
            # Handle incoming messages
            async for msg in ws:
                # Just log received messages for this example
                logger.debug(f"Received message: {msg.data}")
                await self.connection_manager.update_activity(ws)
                
        finally:
            # Clean up on disconnect
            await self.connection_manager.disconnect(ws)
            await self.metrics_service.unregister_subscriber(metrics_queue)
            
        return ws
        
    async def _message_consumer(self, ws, queue):
        """Consumer for the metrics queue."""
        while not ws.closed:
            try:
                message = await queue.get()
                await ws.send_json(message)
                queue.task_done()
            except Exception as e:
                logger.error(f"Error in message consumer: {str(e)}")
                await asyncio.sleep(1)  # Brief delay before retry
                
    async def _housekeeping_task(self):
        """Periodic housekeeping task."""
        while self.is_running:
            try:
                # Get connection metrics
                connection_metrics = await self.connection_manager.get_connection_metrics()
                
                # Get task metrics
                task_metrics = await self.task_manager.get_task_metrics()
                
                # Log metrics periodically
                logger.debug(f"Active connections: {connection_metrics['active_connections']}")
                logger.debug(f"Active tasks: {task_metrics['running']}")
                
                # Clean up completed tasks periodically
                await self.task_manager.cleanup_completed_tasks()
                
                # Sleep for the update interval
                await asyncio.sleep(5.0)  # 5 second interval for housekeeping
                
            except asyncio.CancelledError:
                logger.debug("Housekeeping task cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in housekeeping task: {str(e)}")
                await asyncio.sleep(1)  # Brief delay before retry
                
    async def _simulated_load_task(self):
        """Task that simulates varying system load."""
        while self.is_running:
            try:
                # Create some short-lived tasks to simulate load
                for i in range(5):
                    await self.task_manager.add_task(
                        f"simulated_work_{i}",
                        self._simulated_work()
                    )
                    
                # Sleep for random interval
                await asyncio.sleep(2.0)
                
            except asyncio.CancelledError:
                logger.debug("Simulated load task cancelled")
                break
                
            except Exception as e:
                logger.error(f"Error in simulated load task: {str(e)}")
                await asyncio.sleep(1)  # Brief delay before retry
                
    async def _simulated_work(self):
        """Simulate some CPU work."""
        # Simulate CPU work
        start = time.time()
        while time.time() - start < 0.5:  # Work for 500ms
            # Do some meaningless calculations
            _ = [i * i for i in range(10000)]
            await asyncio.sleep(0.01)  # Yield to event loop
            
        return "work completed"
        
    def _register_metrics_collectors(self):
        """Register metrics collectors with the metrics service."""
        # Register market data collector
        self.metrics_service.register_collector(
            MetricsType.MARKET, 
            self.market_analyzer.get_market_summary
        )
        
        # Register portfolio data collector
        self.metrics_service.register_collector(
            MetricsType.PORTFOLIO, 
            self.portfolio_tracker.get_performance_summary
        )
        
        # Register task metrics collector
        self.metrics_service.register_collector(
            MetricsType.TASKS, 
            self.task_manager.get_task_metrics
        )
        
        # Register connection metrics collector
        self.metrics_service.register_collector(
            MetricsType.CONNECTIONS, 
            self.connection_manager.get_connection_metrics
        )


async def shutdown(server, app, loop):
    """Shutdown the server gracefully."""
    logger.info("Shutting down server...")
    await app.shutdown()
    await app.cleanup()
    loop.stop()


def main():
    """Run the example server."""
    # Create server
    server = ExampleWebSocketServer()
    
    # Get event loop
    loop = asyncio.get_event_loop()
    
    # Setup signal handlers for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, 
            lambda: asyncio.create_task(shutdown(server, server.app, loop))
        )
    
    # Run the server
    web.run_app(server.app, host='localhost', port=8080)


if __name__ == "__main__":
    main()