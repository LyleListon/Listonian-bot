"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set, Any
import asyncio
import json
from datetime import datetime

from ...core.logging import get_logger, log_execution_time
from ...core.dependencies import (
    get_memory_service,
    get_metrics_service,
    get_system_service
)

router = APIRouter()
logger = get_logger("websocket")

class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self.logger = get_logger("ConnectionManager")

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            self.connection_info[websocket] = {
                "connected_at": datetime.utcnow(),
                "last_ping": datetime.utcnow(),
                "messages_sent": 0,
                "messages_received": 0
            }
        self.logger.info(
            f"New WebSocket connection. Active connections: {len(self.active_connections)}"
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]
        self.logger.info(
            f"WebSocket disconnected. Active connections: {len(self.active_connections)}"
        )

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
            
        # Convert message to JSON once for all clients
        json_message = json.dumps(message)
        
        # Create tasks for all sends
        tasks = []
        for websocket in self.active_connections:
            tasks.append(self.send_message(websocket, json_message))
            
        # Wait for all sends to complete
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any errors
            for websocket, result in zip(self.active_connections, results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Error sending message to client: {result}"
                    )
                    await self.disconnect(websocket)

    async def send_message(self, websocket: WebSocket, message: str) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_text(message)
            async with self._lock:
                if websocket in self.connection_info:
                    self.connection_info[websocket]["messages_sent"] += 1
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            await self.disconnect(websocket)
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "total_messages_sent": sum(
                info["messages_sent"]
                for info in self.connection_info.values()
            ),
            "total_messages_received": sum(
                info["messages_received"]
                for info in self.connection_info.values()
            ),
            "connections": [
                {
                    "connected_at": info["connected_at"].isoformat(),
                    "messages_sent": info["messages_sent"],
                    "messages_received": info["messages_received"],
                    "last_ping": info["last_ping"].isoformat()
                }
                for info in self.connection_info.values()
            ]
        }

# Global connection manager
manager = ConnectionManager()

@router.websocket("/")
@log_execution_time(logger)
async def websocket_endpoint(
    websocket: WebSocket,
    memory_service=Depends(get_memory_service),
    metrics_service=Depends(get_metrics_service),
    system_service=Depends(get_system_service)
):
    """Handle WebSocket connections for real-time updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial state
        initial_state = {
            "type": "initial_state",
            "data": {
                "memory": await memory_service.get_current_state(),
                "metrics": await metrics_service.get_current_metrics(),
                "system": await system_service.get_system_status()
            }
        }
        await manager.send_message(websocket, json.dumps(initial_state))
        
        # Start update tasks
        update_tasks = [
            asyncio.create_task(memory_updates(websocket, memory_service)),
            asyncio.create_task(metrics_updates(websocket, metrics_service)),
            asyncio.create_task(system_updates(websocket, system_service))
        ]
        
        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                await handle_client_message(websocket, message)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Clean up
        await manager.disconnect(websocket)
        for task in update_tasks:
            task.cancel()
        try:
            await asyncio.gather(*update_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error cleaning up tasks: {e}")

async def memory_updates(websocket: WebSocket, memory_service: Any):
    """Send memory updates to the client."""
    try:
        while True:
            state = await memory_service.get_current_state()
            await manager.send_message(
                websocket,
                json.dumps({
                    "type": "memory_update",
                    "data": state
                })
            )
            await asyncio.sleep(5)  # Update every 5 seconds
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in memory updates: {e}")

async def metrics_updates(websocket: WebSocket, metrics_service: Any):
    """Send metrics updates to the client."""
    try:
        while True:
            metrics = await metrics_service.get_current_metrics()
            await manager.send_message(
                websocket,
                json.dumps({
                    "type": "metrics_update",
                    "data": metrics
                })
            )
            await asyncio.sleep(10)  # Update every 10 seconds
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in metrics updates: {e}")

async def system_updates(websocket: WebSocket, system_service: Any):
    """Send system updates to the client."""
    try:
        while True:
            status = await system_service.get_system_status()
            await manager.send_message(
                websocket,
                json.dumps({
                    "type": "system_update",
                    "data": status
                })
            )
            await asyncio.sleep(15)  # Update every 15 seconds
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in system updates: {e}")

async def handle_client_message(websocket: WebSocket, message: str):
    """Handle messages received from the client."""
    try:
        data = json.loads(message)
        message_type = data.get('type')
        
        if message_type == 'ping':
            await manager.send_message(
                websocket,
                json.dumps({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            async with manager._lock:
                if websocket in manager.connection_info:
                    manager.connection_info[websocket]["last_ping"] = datetime.utcnow()
                    manager.connection_info[websocket]["messages_received"] += 1
        
        # Add more message type handlers as needed
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON message received")
    except Exception as e:
        logger.error(f"Error handling client message: {e}")

@router.get("/stats")
async def get_connection_stats():
    """Get WebSocket connection statistics."""
    return manager.get_stats()