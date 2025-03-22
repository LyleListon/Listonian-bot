"""WebSocket routes for real-time updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Any, List, Set
import asyncio
import json
from datetime import datetime

from ..core.logging import get_logger
from ..core.dependencies import (
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
        self._lock = asyncio.Lock()
        self.logger = get_logger("connection_manager")

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        self.logger.info(f"New connection. Active connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        self.logger.info(f"Connection closed. Active connections: {len(self.active_connections)}")

    async def send_message(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            await self.disconnect(websocket)
            raise

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    memory_service=Depends(get_memory_service),
    metrics_service=Depends(get_metrics_service),
    system_service=Depends(get_system_service)
):
    """Handle WebSocket connections for real-time updates."""
    await manager.connect(websocket)
    update_tasks: List[asyncio.Task] = []
    
    try:
        # Send initial state
        initial_state = {
            "type": "initial_state",
            "data": {
                "memory": await memory_service.get_current_state(),
                "metrics": await metrics_service.get_current_metrics(),
                "system": await system_service.get_system_status()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await manager.send_message(websocket, initial_state)
        
        # Start update tasks
        update_tasks = [
            asyncio.create_task(memory_updates(websocket, memory_service)),
            asyncio.create_task(metrics_updates(websocket, metrics_service)),
            asyncio.create_task(system_updates(websocket, system_service))
        ]
        
        # Handle client messages
        while True:
            try:
                data = await websocket.receive_json()
                await handle_client_message(websocket, data)
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
            if not task.done():
                task.cancel()
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)

async def memory_updates(websocket: WebSocket, memory_service: Any) -> None:
    """Send memory state updates."""
    try:
        while True:
            state = await memory_service.get_current_state()
            await manager.send_message(websocket, {
                "type": "memory_update",
                "data": state,
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(5)  # Update every 5 seconds
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in memory updates: {e}")

async def metrics_updates(websocket: WebSocket, metrics_service: Any) -> None:
    """Send metrics updates."""
    try:
        while True:
            metrics = await metrics_service.get_current_metrics()
            await manager.send_message(websocket, {
                "type": "metrics_update",
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(10)  # Update every 10 seconds
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in metrics updates: {e}")

async def system_updates(websocket: WebSocket, system_service: Any) -> None:
    """Send system status updates."""
    try:
        while True:
            status = await system_service.get_system_status()
            await manager.send_message(websocket, {
                "type": "system_update",
                "data": status,
                "timestamp": datetime.utcnow().isoformat()
            })
            await asyncio.sleep(15)  # Update every 15 seconds
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error in system updates: {e}")

async def handle_client_message(websocket: WebSocket, data: Dict[str, Any]) -> None:
    """Handle messages from clients."""
    try:
        message_type = data.get('type')
        if message_type == 'ping':
            await manager.send_message(websocket, {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
    except Exception as e:
        logger.error(f"Error handling client message: {e}")

@router.get("/stats")
async def get_connection_stats() -> Dict[str, Any]:
    """Get WebSocket connection statistics."""
    return {
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.utcnow().isoformat()
    }