"""WebSocket server for real-time dashboard updates."""

import logging
import json
import asyncio
from typing import Dict, Any, Optional
from aiohttp import web, WSMsgType
from decimal import Decimal
from datetime import datetime

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
        self.clients = set()
        logger.debug("WebSocket server initialized")

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
            return True

        except Exception as e:
            logger.error("Failed to initialize WebSocket server: %s", str(e))
            return False

    async def start(self):
        """Start WebSocket server."""
        try:
            self.is_running = True
            asyncio.create_task(self._update_loop())
            logger.debug("WebSocket server started")

        except Exception as e:
            logger.error("Failed to start WebSocket server: %s", str(e))
            self.is_running = False
            raise

    async def stop(self):
        """Stop WebSocket server."""
        self.is_running = False
        # Close all client connections
        for ws in self.clients:
            await ws.close()
        self.clients.clear()
        logger.debug("WebSocket server stopped")

    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)

        try:
            # Send initial data
            await self._send_initial_data(ws)

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(ws, data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                elif msg.type == WSMsgType.ERROR:
                    logger.error('WebSocket connection closed with exception %s', ws.exception())

        finally:
            self.clients.remove(ws)
            await ws.close()

        return ws

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
        """Main update loop for pushing data to clients."""
        while self.is_running:
            try:
                if self.clients:  # Only send updates if there are connected clients
                    for ws in self.clients:
                        await self._send_market_data(ws)
                        await self._send_portfolio_data(ws)
                        await self._send_memory_data(ws)
                        await self._send_storage_data(ws)
                        await self._send_distribution_data(ws)
                        await self._send_execution_data(ws)
                        await self._send_gas_data(ws)
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error("Error in update loop: %s", str(e))
                await asyncio.sleep(1)  # Brief delay before retry

    async def _send_initial_data(self, ws: web.WebSocketResponse):
        """Send initial data to newly connected client."""
        try:
            await self._send_market_data(ws)
            await self._send_portfolio_data(ws)
            await self._send_memory_data(ws)
            await self._send_storage_data(ws)
            await self._send_distribution_data(ws)
            await self._send_execution_data(ws)
            await self._send_gas_data(ws)
        except Exception as e:
            logger.error("Error sending initial data: %s", str(e))

    async def _send_market_data(self, ws: web.WebSocketResponse):
        """Send market data update."""
        try:
            market_data = await self.market_analyzer.get_market_summary()
            await ws.send_json({'type': 'market_update', 'data': market_data})
        except Exception as e:
            logger.error("Error sending market data: %s", str(e))

    async def _send_portfolio_data(self, ws: web.WebSocketResponse):
        """Send portfolio data update."""
        try:
            portfolio_data = await self.portfolio_tracker.get_performance_summary()
            await ws.send_json({'type': 'portfolio_update', 'data': portfolio_data})
        except Exception as e:
            logger.error("Error sending portfolio data: %s", str(e))

    async def _send_memory_data(self, ws: web.WebSocketResponse):
        """Send memory bank data update."""
        try:
            memory_data = await self.memory_bank.get_all_context()
            await ws.send_json({'type': 'memory_update', 'data': memory_data})
        except Exception as e:
            logger.error("Error sending memory data: %s", str(e))

    async def _send_storage_data(self, ws: web.WebSocketResponse):
        """Send storage hub data update."""
        try:
            storage_data = await self.storage_hub.get_status()
            await ws.send_json({'type': 'storage_update', 'data': storage_data})
        except Exception as e:
            logger.error("Error sending storage data: %s", str(e))

    async def _send_distribution_data(self, ws: web.WebSocketResponse):
        """Send distribution data update."""
        try:
            distribution_data = await self.distribution_manager.get_metrics()
            await ws.send_json({'type': 'distribution_update', 'data': distribution_data})
        except Exception as e:
            logger.error("Error sending distribution data: %s", str(e))

    async def _send_execution_data(self, ws: web.WebSocketResponse):
        """Send execution data update."""
        try:
            execution_data = await self.execution_manager.get_metrics()
            await ws.send_json({'type': 'execution_update', 'data': execution_data})
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
        except Exception as e:
            logger.error("Error sending gas data: %s", str(e))
