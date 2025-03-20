"""
WebSocket manager for real-time updates.

This module provides:
1. WebSocket connection management
2. Real-time data broadcasting
3. Connection tracking and cleanup
"""

import asyncio
import logging
import json
from typing import Dict, Set, Any, Optional
from datetime import datetime
from fastapi import WebSocket

# Configure logging
logger = logging.getLogger(__name__)

class ConnectionInfo:
    """Stores information about a WebSocket connection."""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        """Initialize connection info."""
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.messages_sent = 0
        self.messages_received = 0

class WebSocketManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self._lock = asyncio.Lock()
        self._connections: Dict[str, ConnectionInfo] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._active = False
        
    async def start(self) -> None:
        """Start the WebSocket manager."""
        async with self._lock:
            if not self._active:
                self._active = True
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
                logger.info("WebSocket manager started")
    
    async def stop(self) -> None:
        """Stop the WebSocket manager."""
        async with self._lock:
            if self._active:
                self._active = False
                if self._cleanup_task:
                    self._cleanup_task.cancel()
                    try:
                        await self._cleanup_task
                    except asyncio.CancelledError:
                        pass
                    self._cleanup_task = None
                
                # Close all connections
                for conn_info in list(self._connections.values()):
                    try:
                        await conn_info.websocket.close()
                    except Exception as e:
                        logger.error(f"Error closing connection {conn_info.client_id}: {e}")
                
                self._connections.clear()
                logger.info("WebSocket manager stopped")
    
    async def add_connection(self, websocket: WebSocket) -> None:
        """Add a new WebSocket connection."""
        async with self._lock:
            # Generate a unique client ID
            client_id = f"{websocket.client.host}:{websocket.client.port}"
            
            # Remove any existing connection with same client ID
            if client_id in self._connections:
                old_conn = self._connections[client_id]
                try:
                    await old_conn.websocket.close()
                except Exception:
                    pass
                del self._connections[client_id]
            
            # Add new connection
            self._connections[client_id] = ConnectionInfo(websocket, client_id)
            logger.info(f"New WebSocket connection added from {client_id}. Total connections: {len(self._connections)}")
    
    async def remove_connection(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            client_id = f"{websocket.client.host}:{websocket.client.port}"
            if client_id in self._connections:
                del self._connections[client_id]
                logger.info(f"WebSocket connection removed from {client_id}. Total connections: {len(self._connections)}")
    
    async def broadcast(self, event: str, data: Any) -> None:
        """Broadcast data to all connected clients."""
        message = json.dumps({
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        dead_connections = set()
        
        for client_id, conn_info in self._connections.items():
            try:
                await conn_info.websocket.send_text(message)
                conn_info.messages_sent += 1
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                dead_connections.add(client_id)
        
        # Clean up dead connections
        if dead_connections:
            async with self._lock:
                for client_id in dead_connections:
                    if client_id in self._connections:
                        del self._connections[client_id]
                        logger.info(f"Removed dead connection {client_id}")
    
    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale connections."""
        while self._active:
            try:
                # Check connection health
                now = datetime.utcnow()
                dead_connections = set()
                
                for client_id, conn_info in self._connections.items():
                    # Remove connections that haven't received a ping in 2 minutes
                    if (now - conn_info.last_ping).total_seconds() > 120:
                        dead_connections.add(client_id)
                        logger.warning(f"Connection {client_id} timed out")
                
                if dead_connections:
                    async with self._lock:
                        for client_id in dead_connections:
                            if client_id in self._connections:
                                try:
                                    await self._connections[client_id].websocket.close()
                                except Exception:
                                    pass
                                del self._connections[client_id]
                                logger.info(f"Removed stale connection {client_id}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def handle_ping(self, websocket: WebSocket) -> None:
        """Handle ping message from client."""
        client_id = f"{websocket.client.host}:{websocket.client.port}"
        if client_id in self._connections:
            conn_info = self._connections[client_id]
            conn_info.last_ping = datetime.utcnow()
            conn_info.messages_received += 1
    
    @property
    def connection_count(self) -> int:
        """Get the current number of active connections."""
        return len(self._connections)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed information about current connections."""
        return {
            "total_connections": len(self._connections),
            "connections": [
                {
                    "client_id": info.client_id,
                    "connected_at": info.connected_at.isoformat(),
                    "messages_sent": info.messages_sent,
                    "messages_received": info.messages_received,
                    "last_ping": info.last_ping.isoformat()
                }
                for info in self._connections.values()
            ]
        }

# Singleton instance
_ws_manager: Optional[WebSocketManager] = None

def get_ws_manager() -> WebSocketManager:
    """Get the WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager