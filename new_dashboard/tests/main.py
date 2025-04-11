"""Main FastAPI application for the dashboard."""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from core.config import settings
from core.logging import setup_logging, get_logger
from core.dependencies import lifespan, register_services

# Set up logging
setup_logging(level=settings.log_level, log_file=settings.log_file)

logger = get_logger("main")

# Create FastAPI application
app = FastAPI(
    title="Arbitrage Bot Dashboard",
    description="Real-time monitoring dashboard for the arbitrage bot",
    version="2.0.0",
    lifespan=lifespan,
)

# Mount static files
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Set up templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Register services
register_services()

# Import and include routers
from api.routes import websocket, metrics, system

app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(system.router, prefix="/api/system", tags=["system"])


@app.on_event("startup")
async def startup_event():
    """Handle application startup."""
    logger.info(f"Starting dashboard on http://{settings.host}:{settings.port}")


@app.on_event("shutdown")
async def shutdown_event():
    """Handle application shutdown."""
    logger.info("Shutting down dashboard")


def start():
    """Start the dashboard application."""
    import uvicorn

    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        workers=1,  # Single worker for WebSocket support
        loop="auto",
        timeout_keep_alive=settings.ws_ping_timeout,
    )

    # Start server
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    start()
