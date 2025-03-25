"""Main FastAPI application module."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, Response
import json
import asyncio
import logging
from typing import List, Dict, Any
from pathlib import Path

from .core.logging import configure_logging, get_logger
from .core.dependencies import get_memory_service
from .routes import metrics, system, websocket
from .services import service_manager
from .services.memory_service import MemoryService

# Configure logging
configure_logging()
logger = get_logger("dashboard")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    
    # Startup
    try:
        logger.info("Initializing dashboard...")
        await service_manager.initialize()
        logger.info("Dashboard initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    finally:
        # Shutdown
        try:
            await service_manager.shutdown()
            logger.info("Dashboard cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

# Create and configure the FastAPI application
app = FastAPI(
    title="Arbitrage Bot Dashboard",
    lifespan=lifespan,
    debug=True
)

# Configure static files and templates
static_dir = Path(__file__).parent / "static"
templates_dir = Path(__file__).parent / "templates"

# Configure CORS with WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Debug middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.debug(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.debug(f"Response status: {response.status_code}")
    return response

# Register API routers with detailed logging
logger.debug("Available routes before registration:")
for route in app.routes:
    if hasattr(route, 'methods'):
        logger.debug(f"  {route.name}: {route.path} [{route.methods}]")
    elif hasattr(route, 'path'):
        logger.debug(f"  {route.__class__.__name__}: {route.path}")
    else:
        logger.debug(f"  {route.__class__.__name__}: {route}")

# Register routers
app.include_router(
    metrics.router,
    prefix="/api/metrics",
    tags=["metrics"]
)
app.include_router(
    system.router,
    prefix="/api/system",
    tags=["system"],
    include_in_schema=True
)
app.include_router(
    websocket.router,
    tags=["websocket"],
    include_in_schema=True
)

logger.debug("Available routes after registration:")
for route in app.routes:
    if hasattr(route, 'methods'):
        logger.debug(f"  {route.name}: {route.path} [{route.methods}]")
    elif hasattr(route, 'path'):
        logger.debug(f"  {route.__class__.__name__}: {route.path}")
    else:
        logger.debug(f"  {route.__class__.__name__}: {route}")

# Mount static files and templates after API routes
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

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

@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests."""
    return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve dashboard frontend."""
    if not service_manager._initialized:
        await service_manager.initialize()
    return templates.TemplateResponse(
        "base.html",
        {"request": request}
    )