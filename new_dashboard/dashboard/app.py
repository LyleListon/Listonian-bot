"""Main FastAPI application module."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import json
import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path

from .core.logging import configure_logging, get_logger
from .core.dependencies import get_memory_service
from .routes import metrics, system
from .services import service_manager
from .services.memory_service import MemoryService

# Configure logging
configure_logging()
logger = get_logger("dashboard")

# Global connection manager
manager = None

# WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.memory_service = None
        self.update_task = None
        self._initialized = False

    async def initialize(self):
        """Initialize the connection manager."""
        if not self._initialized:
            await service_manager.initialize()

            self.memory_service = service_manager.memory_service
            self.update_task = asyncio.create_task(self._broadcast_updates())
            self._initialized = True
            logger.info("Connection manager initialized")

    async def cleanup(self):
        """Cleanup resources."""
        if not self._initialized:
            return
            
        # Cancel update task if running
        if self.update_task and not self.update_task.done():
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        # Close all WebSocket connections
        for connection in self.active_connections[:]:
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket connection: {e}")
            self.active_connections.remove(connection)
        
        # Cleanup memory service
        await self.memory_service.cleanup()
        self._initialized = False
        logger.info("Connection manager cleaned up")

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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
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
                await self.disconnect(connection)

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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    global manager
    
    # Startup
    try:
        logger.info("Initializing dashboard...")
        manager = ConnectionManager()
        await service_manager.initialize()
        manager.memory_service = service_manager.memory_service
        await manager.initialize()
        logger.info("Dashboard initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Shutdown
        if manager:
            try:
                await manager.cleanup()
                await service_manager.shutdown()
                logger.info("Dashboard cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Arbitrage Bot Dashboard", lifespan=lifespan)

    # Configure static files and templates
    static_dir = Path(__file__).parent / "static"
    templates_dir = Path(__file__).parent / "templates"

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    templates = Jinja2Templates(directory=str(templates_dir))

    # Debug middleware to log all requests
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        logger.debug(f"Incoming request: {request.method} {request.url.path}")
        response = await call_next(request)
        logger.debug(f"Response status: {response.status_code}")
        return response

    # Register API routers with debug logging
    logger.info("Registering metrics router at /api/metrics")
    app.include_router(
        metrics.router,
        prefix="/api/metrics",
        tags=["metrics"]
    )
    app.include_router(system.router, prefix="/api/system", tags=["system"], include_in_schema=True)
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        logger.info("Initializing services on startup...")
        await service_manager.initialize()
        logger.info("Services initialized successfully")
    
    @app.middleware("http")
    async def initialize_services(request: Request, call_next):
        """Ensure services are initialized before handling requests."""
        if not service_manager._initialized:
            await service_manager.initialize()
        response = await call_next(request)
        return response

    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Serve dashboard frontend."""
        if not service_manager._initialized:
            await service_manager.initialize()
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

    return app