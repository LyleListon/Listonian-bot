#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import time
from typing import Dict, Any, Set, Optional
import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for real-time dashboard updates."""
    
    def __init__(self, analytics_system=None, alert_system=None, metrics_manager=None, host="0.0.0.0", port=None):
        """Initialize WebSocket server."""
        self.clients: Dict[WebSocketServerProtocol, Dict] = {}  # client -> {channels: Set[str], last_ping: float}
        self.server = None
        self.analytics_system = analytics_system
        self.alert_system = alert_system
        self.metrics_manager = metrics_manager
        self.host = host
        self.base_port = port or int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
        self.port = self.base_port
        self.max_port_attempts = 10
        self.update_task = None
        self.monitoring_task = None
        self.running = False
        self.start_time = time.time()
        self.connection_stats = {
            'total_messages': 0,
            'error_count': 0,
            'last_error_time': None,
            'client_latencies': {}
        }

    async def register(self, websocket: WebSocketServerProtocol):
        """Register a new client connection."""
        self.clients[websocket] = {
            'channels': set(),
            'last_ping': time.time(),
            'latency': 0,
            'messages_received': 0,
            'errors': 0
        }
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        await self.send_system_status(websocket)

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister a client connection."""
        if websocket in self.clients:
            del self.clients[websocket]
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def subscribe(self, websocket: WebSocketServerProtocol, channels: list):
        """Subscribe client to specified channels."""
        if websocket in self.clients:
            self.clients[websocket]['channels'].update(channels)
            logger.info(f"Client subscribed to channels: {channels}")
            # Send initial data for subscribed channels
            try:
                await self.send_initial_data(websocket, channels)
            except Exception as e:
                logger.error(f"Error sending initial data: {e}", exc_info=True)
                # Send empty data to prevent dashboard from hanging
                await websocket.send(json.dumps({
                    'type': 'system',
                    'status': 'warning',
                    'message': 'Waiting for market data...'
                }))

    async def get_dex_status(self) -> list:
        """Get status of all DEXes."""
        if not self.analytics_system:
            return []

        dexes = []
        try:
            metrics = await self.analytics_system.get_performance_metrics()
            if metrics and len(metrics) > 0 and 'dex_metrics' in metrics[0]:
                for dex_name, dex_data in metrics[0]['dex_metrics'].items():
                    # Format DEX name for display
                    display_name = dex_name.replace('_', ' ').title()
                    if dex_name.lower() == 'uniswap_v3':
                        display_name = 'Uniswap V3'
                    elif dex_name.lower() == 'sushiswap':
                        display_name = 'SushiSwap'
                    elif dex_name.lower() == 'baseswap':
                        display_name = 'BaseSwap'
                    elif dex_name.lower() == 'pancakeswap':
                        display_name = 'PancakeSwap'

                    dexes.append({
                        'name': display_name,
                        'active': dex_data.get('active', False),
                        'liquidity': dex_data.get('liquidity', 0),
                        'volume_24h': dex_data.get('volume_24h', 0)
                    })
        except Exception as e:
            logger.error(f"Error getting DEX status: {e}")

        return dexes

    async def get_arbitrage_opportunities(self) -> list:
        """Get current arbitrage opportunities."""
        if not self.analytics_system:
            return []

        opportunities = []
        try:
            if hasattr(self.analytics_system, 'get_opportunities'):
                opportunities = await self.analytics_system.get_opportunities()
                # Convert opportunities to dashboard format
                return [{
                    'token_pair': opp['details']['pair'],
                    'potential_profit': opp['profit_usd'] + opp['gas_cost_usd'],
                    'gas_cost': opp['gas_cost_usd'],
                    'net_profit': opp['profit_usd'],
                    'price_impact': opp['price_impact'],
                    'executable': opp['status'] == 'Ready'
                } for opp in opportunities]
        except Exception as e:
            logger.error(f"Error getting arbitrage opportunities: {e}")

        return opportunities

    async def send_initial_data(self, websocket: WebSocketServerProtocol, channels: list):
        """Send initial data for subscribed channels."""
        try:
            if 'metrics' in channels and self.analytics_system:
                metrics = await self.analytics_system.get_performance_metrics()
                if metrics and len(metrics) > 0:
                    latest = metrics[0]  # Latest metrics are first in the list
                    data = {
                        'type': 'metrics',
                        'metrics': {
                            'total_trades': latest.get('total_trades', 0),
                            'trades_24h': latest.get('trades_24h', 0),
                            'success_rate': latest.get('success_rate', 0.0),
                            'total_profit': latest.get('total_profit_usd', 0.0),
                            'profit_24h': latest.get('portfolio_change_24h', 0.0),
                            'active_opportunities': latest.get('active_opportunities', 0),
                            'system_status': latest.get('system_status', 'active'),
                            'backoff_time': latest.get('backoff_time', 0),
                            'dex_status': latest.get('dex_metrics', [])
                        }
                    }
                    await websocket.send(json.dumps(data))

            if 'performance' in channels and self.analytics_system:
                metrics = await self.analytics_system.get_performance_metrics()
                if metrics and len(metrics) > 0:
                    now = int(time.time() * 1000)
                    latest = metrics[0]

                    # Get market conditions for price history
                    price_history = []
                    if hasattr(self.analytics_system, 'market_conditions'):
                        for symbol, condition in self.analytics_system.market_conditions.items():
                            if symbol == 'WETH':
                                price_history.append([now, float(condition.price)])

                    data = {
                        'type': 'performance',
                        'price_history': price_history,
                        'profit_history': [[now, float(latest.get('total_profit_usd', 0.0))]],
                        'volume_history': [[now, latest.get('total_trades', 0)]],
                        'opportunities': await self.get_arbitrage_opportunities()
                    }
                    await websocket.send(json.dumps(data))

        except Exception as e:
            logger.error(f"Error sending initial data: {e}", exc_info=True)

    async def broadcast(self, data: Dict[str, Any], channel: str):
        """Broadcast data to subscribed clients."""
        if not self.clients:
            return

        message = json.dumps(data)
        timestamp = time.time()
        
        for websocket, client_data in list(self.clients.items()):
            if channel in client_data['channels']:
                try:
                    await websocket.send(message)
                    self.connection_stats['total_messages'] += 1
                    client_data['last_ping'] = timestamp
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    client_data['errors'] += 1
                    self.connection_stats['error_count'] += 1
                    self.connection_stats['last_error_time'] = timestamp

    async def send_periodic_updates(self):
        """Send periodic updates to subscribed clients."""
        while self.running:
            try:
                if self.analytics_system and self.clients:
                    try:
                        metrics = await self.analytics_system.get_performance_metrics()
                        opportunities = await self.get_arbitrage_opportunities()
                        
                        if metrics and len(metrics) > 0:
                            latest = metrics[0]  # Latest metrics are first in the list
                            await self.broadcast({
                                'type': 'metrics',
                                'metrics': {
                                    'total_trades': latest.get('total_trades', 0),
                                    'trades_24h': latest.get('trades_24h', 0),
                                    'success_rate': latest.get('success_rate', 0.0),
                                    'total_profit': latest.get('total_profit_usd', 0.0),
                                    'profit_24h': latest.get('portfolio_change_24h', 0.0),
                                    'active_opportunities': latest.get('active_opportunities', 0),
                                    'system_status': latest.get('system_status', 'active'),
                                    'backoff_time': latest.get('backoff_time', 0),
                                    'dex_status': latest.get('dex_metrics', [])
                                }
                            }, 'metrics')

                            # Send performance updates
                            now = int(time.time() * 1000)
                            price_history = []
                            if hasattr(self.analytics_system, 'market_conditions'):
                                for symbol, condition in self.analytics_system.market_conditions.items():
                                    if symbol == 'WETH':
                                        price_history.append([now, float(condition.price)])

                            await self.broadcast({
                                'type': 'performance',
                                'price_history': price_history,
                                'profit_history': [[now, float(latest.get('total_profit_usd', 0.0))]],
                                'volume_history': [[now, latest.get('total_trades', 0)]],
                                'opportunities': opportunities or []
                            }, 'performance')
                    except Exception as e:
                        logger.error(f"Error getting metrics: {e}")
                        # Notify clients that data is not yet available
                        await self.broadcast({
                            'type': 'system',
                            'status': 'warning',
                            'message': 'Market data temporarily unavailable, retrying...'
                        }, 'system')
                        
                        # Wait before next attempt
                        await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Error in periodic updates: {e}")

            await asyncio.sleep(1)  # Update every second for real-time opportunities

    async def handler(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket connection."""
        client_id = id(websocket)
        logger.info(f"New client connected. ID: {client_id}")

        try:
            # Send welcome message
            await websocket.send(json.dumps({
                'type': 'system',
                'message': 'Connected to WebSocket server',
                'port': self.port
            }))

            await self.register(websocket)
            
            # Auto-subscribe to all channels
            await self.subscribe(websocket, ['metrics', 'performance', 'system'])
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')

                    if msg_type == 'subscribe':
                        channels = data.get('channels', [])
                        await self.subscribe(websocket, channels)
                        await websocket.send(json.dumps({
                            'type': 'system',
                            'message': f'Subscribed to channels: {channels}'
                        }))
                    elif msg_type == 'ping':
                        await websocket.send(json.dumps({
                            'type': 'pong',
                            'timestamp': time.time()
                        }))
                    elif msg_type == 'health':
                        await websocket.send(json.dumps({
                            'type': 'system',
                            'status': 'ok',
                            'port': self.port,
                            'uptime': time.time() - self.start_time,
                            'connections': len(self.clients),
                            'message': 'WebSocket server is healthy'
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

    async def monitor_connections(self):
        """Monitor client connections and performance."""
        while self.running:
            try:
                current_time = time.time()
                for client, data in list(self.clients.items()):
                    # Check client health
                    if current_time - data['last_ping'] > 30:  # No response for 30 seconds
                        logger.warning(f"Client unresponsive: {id(client)}")
                        await self.broadcast({
                            'type': 'system',
                            'status': 'warning',
                            'message': 'Connection quality degraded'
                        }, 'system')
                    
                    # Calculate and store latency
                    try:
                        pong_waiter = await client.ping()
                        start_time = time.time()
                        await pong_waiter
                        latency = time.time() - start_time
                        data['latency'] = latency
                        self.connection_stats['client_latencies'][id(client)] = latency
                    except Exception as e:
                        logger.error(f"Error checking client latency: {e}")
                
                # Send connection stats to clients
                stats_message = {
                    'type': 'system',
                    'status': 'info',
                    'stats': {
                        'total_clients': len(self.clients),
                        'total_messages': self.connection_stats['total_messages'],
                        'error_rate': self.connection_stats['error_count'] / max(1, self.connection_stats['total_messages']),
                        'average_latency': sum(self.connection_stats['client_latencies'].values()) / max(1, len(self.connection_stats['client_latencies']))
                    }
                }
                await self.broadcast(stats_message, 'system')
                
            except Exception as e:
                logger.error(f"Error in connection monitoring: {e}")
            
            await asyncio.sleep(5)  # Check every 5 seconds

    async def check_port_available(self, port: int) -> bool:
        """Check if a port is available."""
        try:
            # Try to create a socket with the port
            test_socket = await websockets.serve(
                lambda x, y: None,  # Dummy handler
                self.host,
                port
            )
            test_socket.close()
            await test_socket.wait_closed()
            return True
        except Exception:
            return False

    async def find_available_port(self) -> Optional[int]:
        """Find an available port starting from base_port."""
        logger.info(f"Finding available port starting from {self.base_port}")
        
        for port_offset in range(self.max_port_attempts):
            try_port = self.base_port + port_offset
            if await self.check_port_available(try_port):
                logger.info(f"Found available port: {try_port}")
                return try_port
            else:
                logger.warning(f"Port {try_port} is not available, trying next port")
        
        logger.error(f"No available ports found after {self.max_port_attempts} attempts")
        return None

    async def start(self):
        """Start WebSocket server with port conflict resolution."""
        retries = 0
        max_retries = 3
        
        while retries < max_retries:
            try:
                # Try to find an available port
                available_port = await self.find_available_port()
                if not available_port:
                    raise RuntimeError("No available ports found")
                
                self.port = available_port
                logger.info(f"Attempting to start WebSocket server on {self.host}:{self.port}")
                
                # Start WebSocket server without SSL for development
                try:
                    self.server = await websockets.serve(
                        self.handler,
                        self.host,
                        self.port,
                        ping_interval=20,
                        ping_timeout=20,
                        close_timeout=20
                    )
                    logger.info(f"WebSocket server created on {self.host}:{self.port}")
                    
                    # Start tasks
                    self.running = True
                    self.update_task = asyncio.create_task(self.send_periodic_updates())
                    self.monitoring_task = asyncio.create_task(self.monitor_connections())
                    
                    # Wait for tasks to start
                    await asyncio.sleep(1)
                    
                    if self.is_running():
                        logger.info(f"WebSocket server successfully running on {self.host}:{self.port}")
                        return self
                    else:
                        logger.error(f"WebSocket server failed to start on {self.host}:{self.port}")
                        await self.stop()
                        retries += 1
                        continue
                        
                except Exception as e:
                    logger.error(f"Error starting WebSocket server: {e}")
                    await self.stop()
                    retries += 1
                    continue
                
            except Exception as e:
                retries += 1
                logger.error(f"Attempt {retries}/{max_retries} failed to start WebSocket server: {e}")
                
                if retries < max_retries:
                    logger.info(f"Retrying with different port in 1 second...")
                    await asyncio.sleep(1)
                    continue
                else:
                    logger.error("Maximum retry attempts reached. Failed to start WebSocket server.")
                    raise RuntimeError(f"Failed to start WebSocket server after {max_retries} attempts: {str(e)}")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running and self.server is not None and self.server.is_serving()

    async def stop(self):
        """Stop WebSocket server."""
        self.running = False
        for task in [self.update_task, self.monitoring_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("WebSocket server stopped")

    async def send_system_status(self, websocket: WebSocketServerProtocol):
        """Send system status to a client."""
        try:
            status = {
                'type': 'system',
                'status': 'info',
                'message': 'Connected to WebSocket server',
                'stats': {
                    'total_clients': len(self.clients),
                    'uptime': time.time() - self.start_time,
                    'error_rate': self.connection_stats['error_count'] / max(1, self.connection_stats['total_messages'])
                }
            }
            await websocket.send(json.dumps(status))
        except Exception as e:
            logger.error(f"Error sending system status: {e}")

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
    await server.start()
    return server
