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
    """
    WebSocket server for real-time dashboard updates.
    """
    
    def __init__(self, analytics_system=None, alert_system=None, metrics_manager=None, host="0.0.0.0", port=None):
        """Initialize WebSocket server."""
        self.clients: Set[WebSocketServerProtocol] = set()
        self.server = None
        self.analytics_system = analytics_system
        self.alert_system = alert_system
        self.metrics_manager = metrics_manager
        self.host = host
        self.base_port = port or int(os.getenv('WEBSOCKET_PORT', '8770'))
        self.port = self.base_port
        self.max_port_attempts = 10  # Try up to 10 ports
        self.update_task = None

    async def check_port_available(self, port: int) -> bool:
        """Check if a port is available for use."""
        try:
            # Try to create a test server
            test_server = await websockets.serve(
                lambda ws, path: None,  # Dummy handler
                self.host,
                port
            )
            test_server.close()
            await test_server.wait_closed()
            return True
        except Exception:
            return False

    async def find_available_port(self) -> Optional[int]:
        """Find an available port starting from base_port."""
        for port_offset in range(self.max_port_attempts):
            try_port = self.base_port + port_offset
            if await self.check_port_available(try_port):
                return try_port
        return None
        
    async def register(self, websocket: WebSocketServerProtocol):
        """Register a new client connection."""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        # Send initial state if analytics system is available
        if self.analytics_system:
            try:
                # Get latest performance metrics
                metrics = await self.analytics_system.get_performance_metrics()
                if metrics:
                    latest_metrics = metrics[-1]  # Get most recent metrics
                    
                    initial_data = {
                        'type': 'metrics',
                        'metrics': {
                            'total_trades': len(metrics),
                            'trades_24h': sum(1 for m in metrics if m.timestamp > time.time() - 24*3600),
                            'success_rate': latest_metrics.success_rate,
                            'failed_trades': latest_metrics.failed_trades,
                            'total_profit': float(latest_metrics.total_profit_usd),
                            'profit_24h': float(latest_metrics.portfolio_change_24h),
                            'active_opportunities': 0,
                            'rejected_opportunities': 0
                        }
                    }
                    
                    await websocket.send(json.dumps(initial_data))
                    
                    # Convert metrics to time series data
                    profit_history = [
                        [int(m.timestamp * 1000), float(m.total_profit_usd)]
                        for m in metrics
                    ]
                    
                    volume_history = [
                        [int(m.timestamp * 1000), m.total_trades]
                        for m in metrics
                    ]
                    
                    performance_data = {
                        'type': 'performance',
                        'profit_history': sorted(profit_history, key=lambda x: x[0]),
                        'volume_history': sorted(volume_history, key=lambda x: x[0])
                    }
                    
                    await websocket.send(json.dumps(performance_data))
                
            except Exception as e:
                logger.error(f"Failed to send initial state: {e}")
        
    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister a client connection."""
        self.clients.remove(websocket)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
        
    async def send_update(self, data: Dict[str, Any]):
        """Send update to all connected clients."""
        if not self.clients:
            return
            
        try:
            message = json.dumps(data, default=str)  # Handle datetime serialization
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"Error sending update: {e}")

    async def broadcast_metrics(self, metrics: Dict[str, Any]):
        """Broadcast metrics update to all clients."""
        try:
            await self.send_update({
                'type': 'metrics',
                'metrics': {
                    'total_trades': metrics.get('performance', {}).get('total_trades', 0),
                    'trades_24h': metrics.get('performance', {}).get('trades_24h', 0),
                    'success_rate': metrics.get('performance', {}).get('success_rate', 0),
                    'total_profit': metrics.get('performance', {}).get('total_profit_usd', 0),
                    'profit_24h': metrics.get('performance', {}).get('profit_24h', 0),
                    'active_opportunities': len(metrics.get('market', {}).get('opportunities', [])),
                }
            })
            
            # Send performance history for charts
            await self.send_update({
                'type': 'performance',
                'profit_history': metrics.get('performance', {}).get('profit_history', []),
                'volume_history': metrics.get('performance', {}).get('volume_history', [])
            })
        except Exception as e:
            logger.error(f"Error broadcasting metrics: {e}")

    async def broadcast_trade(self, trade_data: Dict[str, Any]):
        """Broadcast trade update to all clients."""
        try:
            await self.send_update({
                'type': 'trade',
                'trade': {
                    'id': trade_data.get('id'),
                    'status': trade_data.get('status'),
                    'token_in': trade_data.get('token_in'),
                    'token_out': trade_data.get('token_out'),
                    'amount_in': trade_data.get('amount_in'),
                    'amount_out': trade_data.get('amount_out'),
                    'profit': trade_data.get('analysis', {}).get('profit', 0),
                    'gas_cost': trade_data.get('analysis', {}).get('gas_cost', 0),
                    'timestamp': trade_data.get('completion_time', datetime.now()).isoformat()
                }
            })
        except Exception as e:
            logger.error(f"Error broadcasting trade: {e}")
        
    async def send_periodic_updates(self):
        """Send periodic updates to all connected clients."""
        while True:
            try:
                if self.analytics_system:
                    metrics = await self.analytics_system.get_performance_metrics()
                    if metrics:
                        latest_metrics = metrics[-1]
                        update_data = {
                            'type': 'metrics',
                            'metrics': {
                                'total_trades': len(metrics),
                                'trades_24h': sum(1 for m in metrics if m.timestamp > time.time() - 24*3600),
                                'success_rate': latest_metrics.success_rate,
                                'failed_trades': latest_metrics.failed_trades,
                                'total_profit': float(latest_metrics.total_profit_usd),
                                'profit_24h': float(latest_metrics.portfolio_change_24h),
                                'active_opportunities': 0,
                                'rejected_opportunities': 0
                            }
                        }
                        await self.send_update(update_data)
            except Exception as e:
                logger.error(f"Error sending periodic updates: {e}")
            await asyncio.sleep(5)  # Update every 5 seconds

    async def process_request(self, path: str, request_headers):
        """Process WebSocket request for CORS."""
        if "Origin" in request_headers:
            response_headers = [
                ("Access-Control-Allow-Origin", request_headers["Origin"]),
                ("Access-Control-Allow-Methods", "GET, POST"),
                ("Access-Control-Allow-Headers", "content-type"),
                ("Access-Control-Allow-Credentials", "true"),
            ]
            return None, response_headers
        return None, []

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket connection."""
        client_id = id(websocket)
        logger.info(f"New client connected. ID: {client_id}")
        logger.info(f"Client info - Remote: {websocket.remote_address}, Path: {path}")
        
        try:
            # Send welcome message first to confirm connection
            welcome = {
                "type": "system",
                "message": "Welcome! WebSocket connection established.",
                "status": "connected"
            }
            await websocket.send(json.dumps(welcome))
            logger.info(f"Sent welcome message to client {client_id}")
            
            # Register client after successful welcome
            await self.register(websocket)
            
            # Send initial state
            if self.analytics_system:
                try:
                    metrics = await self.analytics_system.get_performance_metrics()
                    if metrics:
                        latest_metrics = metrics[-1]
                        initial_data = {
                            'type': 'metrics',
                            'metrics': {
                                'total_trades': len(metrics),
                                'trades_24h': sum(1 for m in metrics if m.timestamp > time.time() - 24*3600),
                                'success_rate': latest_metrics.success_rate,
                                'failed_trades': latest_metrics.failed_trades,
                                'total_profit': float(latest_metrics.total_profit_usd),
                                'profit_24h': float(latest_metrics.portfolio_change_24h),
                                'active_opportunities': 0,
                                'rejected_opportunities': 0
                            }
                        }
                        await websocket.send(json.dumps(initial_data))
                        logger.info(f"Sent initial metrics to client {client_id}")
                except Exception as e:
                    logger.error(f"Failed to send initial metrics: {e}")
                    # Don't raise here, continue with connection
            
            # Handle incoming messages
            try:
                async for message in websocket:
                    try:
                        logger.info(f"Received message from client {client_id}: {message}")
                        data = json.loads(message)
                        logger.info(f"Parsed message: {data}")
                        
                        # Handle ping messages
                        if data.get('type') == 'ping':
                            await websocket.send(json.dumps({
                                'type': 'pong',
                                'timestamp': time.time()
                            }))
                            continue
                            
                        # Handle other messages if needed
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse message from client {client_id}: {message}")
                    except websockets.exceptions.ConnectionClosedOK:
                        logger.info(f"Client {client_id} connection closed normally")
                        break
                    except websockets.exceptions.ConnectionClosedError as e:
                        logger.error(f"Client {client_id} connection closed with error: {e}")
                        break
                    except Exception as e:
                        logger.error(f"Error handling message from client {client_id}: {str(e)}")
                        continue
            except websockets.exceptions.ConnectionClosed:
                logger.info(f"Client {client_id} connection closed normally")
            except Exception as e:
                logger.error(f"Error in message loop for client {client_id}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {str(e)}", exc_info=True)
        finally:
            await self.unregister(websocket)
            logger.info(f"Client {client_id} disconnected")
            
    async def start(self):
        """Start WebSocket server with port fallback."""
        last_error = None
        available_port = await self.find_available_port()

        if not available_port:
            error_msg = (
                f"No available ports found after {self.max_port_attempts} attempts. "
                f"Tried ports {self.base_port} through {self.base_port + self.max_port_attempts - 1}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            self.port = available_port
            # Create server with CORS and ping settings
            self.server = await websockets.serve(
                self.handler,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=20,
                process_request=self.process_request,
                compression=None  # Disable compression for better stability
            )
            
            # Start periodic updates task
            self.update_task = asyncio.create_task(self.send_periodic_updates())
            logger.info(f"WebSocket server initialized on {self.host}:{self.port}")
            
            # Return immediately to allow server to run in background
            return self
            
        except Exception as e:
            error_msg = f"Failed to start WebSocket server on port {self.port}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
            
    def is_running(self) -> bool:
        """Check if server is running."""
        return self.server is not None and self.server.is_serving()
        
    async def stop(self):
        """Stop WebSocket server."""
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
    """Create and return a new WebSocket server instance."""
    server = WebSocketServer(
        analytics_system=analytics_system,
        alert_system=alert_system,
        metrics_manager=metrics_manager,
        host=host,
        port=port
    )
    
    # Initialize server in a separate task
    loop = asyncio.get_event_loop()
    start_task = loop.create_task(server.start())
    
    try:
        # Wait for server to start with timeout
        await asyncio.wait_for(start_task, timeout=5.0)
        logger.info(f"WebSocket server started successfully on {host}:{port}")
        return server
    except asyncio.TimeoutError:
        logger.error("WebSocket server startup timed out")
        raise
    except Exception as e:
        logger.error(f"WebSocket server startup failed: {e}")
        raise
