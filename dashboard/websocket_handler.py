"""
WebSocket Handler for Real-time Dashboard Updates

This module implements WebSocket communication for real-time metric updates
and system monitoring.
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any
from datetime import datetime
from aiohttp import web
from aiohttp.web import WebSocketResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Set[WebSocketResponse] = set()
        self.last_metrics: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
    
    async def handle_websocket(self, request: web.Request) -> WebSocketResponse:
        """Handle new WebSocket connections."""
        ws = WebSocketResponse()
        await ws.prepare(request)
        
        async with self._lock:
            self.active_connections.add(ws)
        
        try:
            # Send initial metrics
            if self.last_metrics:
                await ws.send_json({
                    'type': 'metrics',
                    'data': self.last_metrics,
                    'timestamp': datetime.now().isoformat()
                })
            
            # Handle incoming messages
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_message(ws, data)
                    except json.JSONDecodeError:
                        logger.error("Invalid JSON received")
                elif msg.type == web.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        finally:
            async with self._lock:
                self.active_connections.remove(ws)
        
        return ws
    
    async def broadcast_metrics(self, metrics: Dict[str, Any]) -> None:
        """Broadcast metrics to all connected clients."""
        if not metrics:
            return
            
        self.last_metrics = metrics
        message = {
            'type': 'metrics',
            'data': metrics,
            'timestamp': datetime.now().isoformat()
        }
        
        async with self._lock:
            disconnected = set()
            for ws in self.active_connections:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to client: {e}")
                    disconnected.add(ws)
            
            # Remove disconnected clients
            self.active_connections -= disconnected
    
    async def broadcast_alert(self, alert_type: str, message: str, severity: str = "info") -> None:
        """Broadcast an alert to all connected clients."""
        alert = {
            'type': 'alert',
            'alert_type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        
        async with self._lock:
            disconnected = set()
            for ws in self.active_connections:
                try:
                    await ws.send_json(alert)
                except Exception as e:
                    logger.error(f"Error sending alert to client: {e}")
                    disconnected.add(ws)
            
            # Remove disconnected clients
            self.active_connections -= disconnected
    
    async def _handle_message(self, ws: WebSocketResponse, data: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        msg_type = data.get('type')
        
        if msg_type == 'subscribe':
            # Handle subscription requests
            topics = data.get('topics', [])
            await self._handle_subscription(ws, topics)
        elif msg_type == 'unsubscribe':
            # Handle unsubscription requests
            topics = data.get('topics', [])
            await self._handle_unsubscription(ws, topics)
        elif msg_type == 'ping':
            # Handle ping messages
            await ws.send_json({'type': 'pong', 'timestamp': datetime.now().isoformat()})
    
    async def _handle_subscription(self, ws: WebSocketResponse, topics: list) -> None:
        """Handle topic subscription requests."""
        try:
            # Add subscription logic here
            await ws.send_json({
                'type': 'subscription_success',
                'topics': topics,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling subscription: {e}")
            await ws.send_json({
                'type': 'subscription_error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    async def _handle_unsubscription(self, ws: WebSocketResponse, topics: list) -> None:
        """Handle topic unsubscription requests."""
        try:
            # Add unsubscription logic here
            await ws.send_json({
                'type': 'unsubscription_success',
                'topics': topics,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error handling unsubscription: {e}")
            await ws.send_json({
                'type': 'unsubscription_error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })

# Create global WebSocket manager instance
websocket_manager = WebSocketManager()

async def setup_websocket_routes(app: web.Application) -> None:
    """Set up WebSocket routes in the application."""
    app.router.add_get('/ws', websocket_manager.handle_websocket)
    logger.info("WebSocket routes configured")

async def broadcast_system_metrics(metrics: Dict[str, Any]) -> None:
    """Broadcast system metrics through WebSocket."""
    await websocket_manager.broadcast_metrics(metrics)

async def broadcast_system_alert(alert_type: str, message: str, severity: str = "info") -> None:
    """Broadcast system alert through WebSocket."""
    await websocket_manager.broadcast_alert(alert_type, message, severity)