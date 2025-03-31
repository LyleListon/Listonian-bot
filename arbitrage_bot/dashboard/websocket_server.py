"""WebSocket server for real-time dashboard updates."""

import logging
import json
import asyncio
from typing import Dict, Any, Optional
from aiohttp import web, WSMsgType
from weakref import WeakSet
from decimal import Decimal
from datetime import datetime

from .task_manager import TaskManager
from .connection_manager import ConnectionManager
from .metrics_service import MetricsService, MetricsType
from arbitrage_bot.core.optimization.websocket_optimization import (
    OptimizedWebSocketClient,
    WebSocketConnectionPool,
    MessageFormat,
    MessagePriority
)

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for real-time dashboard updates."""

    def __init__(
        self,
        app: web.Application,
        market_analyzer: Any = None,
        portfolio_tracker: Any = None,
        memory_bank: Any = None,
        storage_hub: Any = None,
        distribution_manager: Any = None,
        execution_manager: Any = None,
        gas_optimizer: Any = None
    ):
        """Initialize WebSocket server."""
        self.app = app
        self.market_analyzer = market_analyzer
        self.portfolio_tracker = portfolio_tracker
        self.memory_bank = memory_bank
        self.storage_hub = storage_hub
        self.distribution_manager = distribution_manager
        self.execution_manager = execution_manager
        self.gas_optimizer = gas_optimizer
        self.is_running = False
        self.update_interval = 5  # seconds
        self.clients = WeakSet()
        
        # Initialize managers
        self.task_manager = TaskManager()
        self.connection_manager = ConnectionManager(self.task_manager)
        self.metrics_service = MetricsService()
        
        # Initialize WebSocket connection pool
        self.ws_pool = WebSocketConnectionPool(
            max_connections=5,
            format=MessageFormat.MSGPACK,
            batch_size=10,
            batch_interval=0.1
        )

    async def initialize(self) -> bool:
        """Initialize server components."""
        try:
            # Verify all required components
            if not all([
                self.app,
                self.market_analyzer,
                self.portfolio_tracker,
                self.memory_bank,
                self.storage_hub,
                self.distribution_manager,
                self.execution_manager,
                self.gas_optimizer
            ]):
                logger.error("Missing required components")
                return False

            # Register WebSocket route
            self.app.router.add_get('/ws', self.websocket_handler)
            logger.debug("WebSocket server initialized successfully")
            
            # Register metrics collectors
            self._register_metrics_collectors()
            
            # Start metrics service
            await self.metrics_service.start()
            
            # Start WebSocket connection pool
            await self.ws_pool.connect_all()
            
            # Register cleanup on app shutdown
            self.app.on_shutdown.append(self._on_shutdown)
            
            # Log initialization
            logger.info("WebSocket server initialized with enhanced components")
            logger.debug(f"Task Manager: {self.task_manager}")
            logger.debug(f"Connection Manager: {self.connection_manager}")
            return True

        except Exception as e:
            logger.error("Failed to initialize WebSocket server: %s", str(e))
            return False

    async def start(self):
        """Start WebSocket server."""
        try:
            self.is_running = True
            await self.task_manager.add_task("update_loop", self._update_loop())
            logger.debug("WebSocket server started")

        except Exception as e:
            logger.error("Failed to start WebSocket server: %s", str(e))
            self.is_running = False
            raise

    async def stop(self):
        """Stop WebSocket server."""
        self.is_running = False
        
        # Stop metrics service
        await self.metrics_service.stop()
        
        # Stop WebSocket connection pool
        await self.ws_pool.disconnect_all()
        
        # Cancel all tasks
        await self.task_manager.cancel_all_tasks()
        
        # Disconnect all clients
        await self.connection_manager.disconnect_all()
        logger.debug("WebSocket server stopped")

    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)

        
        # Create a queue for this connection
        metrics_queue = asyncio.Queue(maxsize=100)
        
        # Register connection with connection manager
        await self.connection_manager.connect(ws)
        
        # Register queue with metrics service
        await self.metrics_service.register_subscriber(metrics_queue)
        
        # Register queue with connection manager
        await self.connection_manager.register_queue(ws, metrics_queue, "metrics_queue")

        # Register optimized message handler
        await self._register_optimized_handlers(ws)

        try:
            # Send initial data
            await self._send_initial_data(ws)
            
            # Start message consumer task
            await self.connection_manager.register_task(ws, "message_consumer", 
                                                      self._message_consumer(ws, metrics_queue))

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(ws, data)
                        await self.connection_manager.update_activity(ws)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                elif msg.type == WSMsgType.ERROR:
                    logger.error('WebSocket connection closed with exception %s', ws.exception())

        finally:
            await self.connection_manager.disconnect(ws)
            await self.metrics_service.unregister_subscriber(metrics_queue)

        return ws
    
    async def _register_optimized_handlers(self, ws: web.WebSocketResponse) -> None:
        """Register optimized message handlers."""
        # Create optimized client for external data sources if needed
        if hasattr(self, 'market_analyzer') and self.market_analyzer:
            # Example: Connect to market data source
            market_data_url = self.market_analyzer.get_websocket_url()
            if market_data_url:
                client = await self.ws_pool.get_connection(market_data_url)
                
                # Register handler for market data
                async def handle_market_data(data):
                    await self._broadcast_market_data(data)
                
                await client.register_handler("market_data", handle_market_data)

    async def _handle_message(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        try:
            update_type = data.get('type')
            if update_type == 'market_data':
                await self._send_market_data(ws)
            elif update_type == 'portfolio':
                await self._send_portfolio_data(ws)
            elif update_type == 'memory':
                await self._send_memory_data(ws)
            elif update_type == 'storage':
                await self._send_storage_data(ws)
            elif update_type == 'distribution':
                await self._send_distribution_data(ws)
            elif update_type == 'execution':
                await self._send_execution_data(ws)
            elif update_type == 'gas':
                await self._send_gas_data(ws)
            else:
                logger.warning("Unknown update type requested: %s", update_type)
        except Exception as e:
            logger.error("Error handling message: %s", str(e))

    async def _update_loop(self):
        """Main update loop for metrics collection."""
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
                logger.debug("Update loop cancelled")
                break
            except Exception as e:
                logger.error("Error in update loop: %s", str(e))
                await asyncio.sleep(1)  # Brief delay before retry

    async def _message_consumer(self, ws: web.WebSocketResponse, queue: asyncio.Queue):
        """Consumer for the metrics queue."""
        while not ws.closed:
            try:
                message = await queue.get()
                await ws.send_json(message)
                queue.task_done()
            except Exception as e:
                logger.error("Error in update loop: %s", str(e))
                await asyncio.sleep(1)  # Brief delay before retry

    async def _send_initial_data(self, ws: web.WebSocketResponse):
        """Send initial data to newly connected client."""
        try:
            # Get all metrics at once
            all_metrics = await self.metrics_service.get_all_metrics()
            
            # Send each metric type
            for metric_type, metrics in all_metrics.items():
                await ws.send_json({
                    "type": f"{metric_type}_update",
                    "data": metrics})
        except Exception as e:
            logger.error("Error sending initial data: %s", str(e))

    async def _send_market_data(self, ws: web.WebSocketResponse):
        """Send market data update."""
        try:
            # Use optimized client if available
            if hasattr(self, 'ws_pool'):
                market_data = await self.market_analyzer.get_market_summary()
                await ws.send_json({'type': 'market_update', 'data': market_data})
                await self.connection_manager.update_activity(ws)
            else:
                await self._send_market_data_legacy(ws)
        except Exception as e:
            logger.error("Error sending market data: %s", str(e))
    
    async def _send_market_data_legacy(self, ws: web.WebSocketResponse):
        """Send market data update."""
        try:
            market_data = await self.market_analyzer.get_market_summary()
            await ws.send_json({'type': 'market_update', 'data': market_data})
            await self.connection_manager.update_activity(ws)
        except Exception as e:
            logger.error("Error sending market data: %s", str(e))

    async def _broadcast_market_data(self, data: Dict[str, Any]):
        """Broadcast market data to all clients."""
        try:
            # Send to all clients
            for client in self.clients:
                if not client.closed:
                    await client.send_json({'type': 'market_update', 'data': data})
        except Exception as e:
            logger.error("Error broadcasting market data: %s", str(e))

    async def _send_portfolio_data(self, ws: web.WebSocketResponse):
        """Send portfolio data update."""
        try:
            portfolio_data = await self.portfolio_tracker.get_performance_summary()
            await ws.send_json({'type': 'portfolio_update', 'data': portfolio_data})
            await self.connection_manager.update_activity(ws)
        except Exception as e:
            logger.error("Error sending portfolio data: %s", str(e))

    async def _send_memory_data(self, ws: web.WebSocketResponse):
        """Send memory bank data update."""
        try:
            memory_data = await self.memory_bank.get_all_context()
            await ws.send_json({'type': 'memory_update', 'data': memory_data})
            await self.connection_manager.update_activity(ws)
        except Exception as e:
            logger.error("Error sending memory data: %s", str(e))

    async def _send_storage_data(self, ws: web.WebSocketResponse):
        """Send storage hub data update."""
        try:
            storage_data = await self.storage_hub.get_status()
            await ws.send_json({'type': 'storage_update', 'data': storage_data})
            await self.connection_manager.update_activity(ws)
        except Exception as e:
            logger.error("Error sending storage data: %s", str(e))

    async def _send_distribution_data(self, ws: web.WebSocketResponse):
        """Send distribution data update."""
        try:
            distribution_data = await self.distribution_manager.get_metrics()
            await ws.send_json({'type': 'distribution_update', 'data': distribution_data})
            await self.connection_manager.update_activity(ws)
        except Exception as e:
            logger.error("Error sending distribution data: %s", str(e))

    async def _send_execution_data(self, ws: web.WebSocketResponse):
        """Send execution data update."""
        try:
            execution_data = await self.execution_manager.get_metrics()
            await ws.send_json({'type': 'execution_update', 'data': execution_data})
            await self.connection_manager.update_activity(ws)
        except Exception as e:
            logger.error("Error sending execution data: %s", str(e))

    async def _send_gas_data(self, ws: web.WebSocketResponse):
        """Send gas price update."""
        try:
            gas_data = {
                'gas_prices': {
                    'fast': self.gas_optimizer.gas_prices['fast'],
                    'standard': self.gas_optimizer.gas_prices['standard'],
                    'slow': self.gas_optimizer.gas_prices['slow'],
                    'base_fee': self.gas_optimizer.gas_prices['base_fee'],
                    'priority_fee': self.gas_optimizer.gas_prices['priority_fee'],
                    'pending_txs': self.gas_optimizer.gas_prices['pending_txs']
                },
                'metrics': {
                    'historical_prices': self.gas_optimizer.gas_metrics['historical_prices'][-10:]  # Last 10 entries
                }
            }
            await ws.send_json({'type': 'gas_update', 'data': gas_data})
            await self.connection_manager.update_activity(ws)
        except Exception as e:
            logger.error("Error sending gas data: %s", str(e))

    def _register_metrics_collectors(self):
        """Register metrics collectors with the metrics service."""
        # Register market data collector
        self.metrics_service.register_collector(
            MetricsType.MARKET, 
            self._collect_market_metrics
        )
        
        # Register portfolio data collector
        self.metrics_service.register_collector(
            MetricsType.PORTFOLIO, 
            self._collect_portfolio_metrics
        )
        
        # Register memory data collector
        self.metrics_service.register_collector(
            MetricsType.MEMORY, 
            self._collect_memory_metrics
        )
        
        # Register storage data collector
        self.metrics_service.register_collector(
            MetricsType.STORAGE, 
            self._collect_storage_metrics
        )
        
        # Register distribution data collector
        self.metrics_service.register_collector(
            MetricsType.DISTRIBUTION, 
            self._collect_distribution_metrics
        )
        
        # Register execution data collector
        self.metrics_service.register_collector(
            MetricsType.EXECUTION, 
            self._collect_execution_metrics
        )
        
        # Register gas data collector
        self.metrics_service.register_collector(
            MetricsType.GAS, 
            self._collect_gas_metrics
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

    async def _on_shutdown(self, app):
        """Handle application shutdown."""
        await self.stop()

    # Metrics collector methods
    async def _collect_market_metrics(self): return await self.market_analyzer.get_market_summary()
    async def _collect_portfolio_metrics(self): return await self.portfolio_tracker.get_performance_summary()
    async def _collect_memory_metrics(self): return await self.memory_bank.get_all_context()
    async def _collect_storage_metrics(self): return await self.storage_hub.get_status()
    async def _collect_distribution_metrics(self): return await self.distribution_manager.get_metrics()
    async def _collect_execution_metrics(self): return await self.execution_manager.get_metrics()
    
    async def _collect_gas_metrics(self):
        """Collect gas metrics."""
        return self.gas_optimizer.gas_prices
