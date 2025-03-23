"""Main FastAPI application module."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
import json
import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path

from .core.logging import configure_logging, get_logger
from .core.dependencies import get_memory_service
from .routes import metrics, system
from .services.memory_service import MemoryService

# Configure logging
configure_logging()
logger = get_logger("dashboard")

# Initialize FastAPI app
app = FastAPI(title="Arbitrage Bot Dashboard")

# Configure static files and templates
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Include routers
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(system.router, prefix="/api/system", tags=["system"])

# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.memory_service = MemoryService()
        self.update_task = None

    async def initialize(self):
        """Initialize the connection manager."""
        await self.memory_service.initialize()
        self.update_task = asyncio.create_task(self._broadcast_updates())
        logger.info("Connection manager initialized")

    async def connect(self, websocket: WebSocket):
        """Handle new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")

        # Send initial state
        try:
            initial_state = await self.memory_service.get_current_state()
            await websocket.send_json({
                "type": "initial_state",
                "data": initial_state
            })
        except Exception as e:
            logger.error(f"Error sending initial state: {e}")

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection."""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def _broadcast_updates(self):
        """Background task to broadcast memory updates."""
        try:
            queue = await self.memory_service.subscribe()
            while True:
                try:
                    state = await queue.get()
                    await self.broadcast({
                        "type": "memory_update",
                        "data": state
                    })
                except Exception as e:
                    logger.error(f"Error in broadcast loop: {e}")
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.memory_service.unsubscribe(queue)
            raise
        except Exception as e:
            logger.error(f"Fatal error in broadcast task: {e}")

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    await manager.initialize()
    logger.info("Dashboard started")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve dashboard frontend."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections."""
    await manager.connect(websocket)
    try:
        while True:
            try:
                # Handle incoming messages (e.g., time range updates)
                data = await websocket.receive_json()
                if data["type"] == "update_time_range":
                    # Handle time range update
                    pass
            except WebSocketDisconnect:
                await manager.disconnect(websocket)
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    finally:
        if websocket in manager.active_connections:
            await manager.disconnect(websocket)