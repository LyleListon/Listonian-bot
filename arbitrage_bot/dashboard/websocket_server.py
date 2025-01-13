"""
WebSocket server for real-time dashboard updates.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Any, Set, Optional
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for real-time dashboard updates."""
    
    def __init__(self, analytics_system=None, alert_system=None, metrics_manager=None, host="0.0.0.0", port=None):
        """Initialize WebSocket server."""
        self.clients: Dict[WebSocketServerProtocol, Set[str]] = {}  # client -> subscribed channels
        self.server = None
        self.analytics_system = analytics_system
        self.alert_system = alert_system
        self.metrics_manager = metrics_manager
        self.host = host
        self.base_port = port or int(os.getenv('WEBSOCKET_PORT', '8771'))
        self.port = self.base_port
        self.max_port_attempts = 10
        self.update_task = None
        self.running = False

    async def register(self, websocket: WebSocketServerProtocol):
        """Register a new client connection."""
        self.clients[websocket] = set()  # Initialize with empty subscriptions
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister a client connection."""
        if websocket in self.clients:
            del self.clients[websocket]
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def subscribe(self, websocket: WebSocketServerProtocol, channels: list):
        """Subscribe client to specified channels."""
        if websocket in self.clients:
            self.clients[websocket].update(channels)
            logger.info(f"Client subscribed to channels: {channels}")
            # Send initial data for subscribed channels
            await self.send_initial_data(websocket, channels)

    async def send_initial_data(self, websocket: WebSocketServerProtocol, channels: list):
        """Send initial data for subscribed channels."""
        try:
            if 'metrics' in channels and self.analytics_system:
                metrics = await self.analytics_system.get_performance_metrics()
                if metrics:
                    latest = metrics[-1]
                    data = {
                        'type': 'metrics',
                        'metrics': {
                            'total_trades': len(metrics),
                            'trades_24h': sum(1 for m in metrics if m.timestamp > time.time() - 24*3600),
                            'success_rate': latest.success_rate,
                            'total_profit': float(latest.total_profit_usd),
                            'profit_24h': float(latest.portfolio_change_24h),
                            'active_opportunities': 0
                        }
                    }
                    await websocket.send(json.dumps(data))

            if 'performance' in channels and self.analytics_system:
                metrics = await self.analytics_system.get_performance_metrics()
                if metrics:
                    profit_history = [
                        [int(m.timestamp * 1000), float(m.total_profit_usd)]
                        for m in metrics
                    ]
                    volume_history = [
                        [int(m.timestamp * 1000), m.total_trades]
                        for m in metrics
                    ]
                    data = {
                        'type': 'performance',
                        'profit_history': sorted(profit_history, key=lambda x: x[0]),
                        'volume_history': sorted(volume_history, key=lambda x: x[0])
                    }
                    await websocket.send(json.dumps(data))

        except Exception as e:
            logger.error(f"Error sending initial data: {e}")

    async def broadcast(self, data: Dict[str, Any], channel: str):
        """Broadcast data to subscribed clients."""
        if not self.clients:
            return

        message = json.dumps(data)
        await asyncio.gather(*[
            client.send(message)
            for client, channels in self.clients.items()
            if channel in channels
        ], return_exceptions=True)

    async def send_periodic_updates(self):
        """Send periodic updates to subscribed clients."""
        while self.running:
            try:
                if self.analytics_system and self.clients:
                    metrics = await self.analytics_system.get_performance_metrics()
                    if metrics:
                        latest = metrics[-1]
                        await self.broadcast({
                            'type': 'metrics',
                            'metrics': {
                                'total_trades': len(metrics),
                                'trades_24h': sum(1 for m in metrics if m.timestamp > time.time() - 24*3600),
                                'success_rate': latest.success_rate,
                                'total_profit': float(latest.total_profit_usd),
                                'profit_24h': float(latest.portfolio_change_24h),
                                'active_opportunities': 0
                            }
                        }, 'metrics')

            except Exception as e:
                logger.error(f"Error in periodic updates: {e}")

            await asyncio.sleep(5)

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket connection."""
        client_id = id(websocket)
        logger.info(f"New client connected. ID: {client_id}")

        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'system',
                'message': 'Connected to WebSocket server'
            }))

            await self.register(websocket)
            
            # Send initial metrics
            if hasattr(self, 'analytics_system'):
                metrics = {
                    'total_trades': 0,
                    'trades_24h': 0,
                    'success_rate': 0,
                    'total_profit': 0.0,
                    'profit_24h': 0.0,
                    'active_opportunities': 0
                }
                
                await websocket.send(json.dumps({
                    'type': 'metrics',
                    'metrics': metrics
                }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')

                    if msg_type == 'subscribe':
                        channels = data.get('channels', [])
                        await self.subscribe(websocket, channels)
                        # Send confirmation
                        await websocket.send(json.dumps({
                            'type': 'system',
                            'message': f'Subscribed to channels: {channels}'
                        }))
                    elif msg_type == 'ping':
                        await websocket.send(json.dumps({
                            'type': 'pong',
                            'timestamp': time.time()
                        }))

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client {client_id}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': 'Invalid JSON message'
                    }))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await websocket.send(json.dumps({
                        'type': 'error',
                        'message': str(e)
                    }))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            await self.unregister(websocket)

    async def start(self):
        """Start WebSocket server."""
        try:
            self.server = await websockets.serve(
                self.handler,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=20
            )
            self.running = True
            self.update_task = asyncio.create_task(self.send_periodic_updates())
            logger.info(f"WebSocket server running on {self.host}:{self.port}")
            return self
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running and self.server is not None and self.server.is_serving()

    async def stop(self):
        """Stop WebSocket server."""
        self.running = False
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("WebSocket server stopped")

async def create_websocket_server(
    analytics_system=None,
    alert_system=None,
    metrics_manager=None,
    host="0.0.0.0",
    port=None
) -> WebSocketServer:
    """Create and start a new WebSocket server instance."""
    server = WebSocketServer(
        analytics_system=analytics_system,
        alert_system=alert_system,
        metrics_manager=metrics_manager,
        host=host,
        port=port
    )
    
    try:
        await server.start()
        if not server.is_running():
            raise RuntimeError("WebSocket server failed to start")
        return server
    except Exception as e:
        logger.error(f"Failed to create WebSocket server: {e}")
        raise
