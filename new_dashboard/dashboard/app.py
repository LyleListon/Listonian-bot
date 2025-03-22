"""FastAPI application for the dashboard."""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from .core.logging import setup_logging, get_logger
from .routes import api_router, websocket_router
from .services.service_manager import service_manager

# Set up logging
setup_logging(level="DEBUG")
logger = get_logger("app")

# Create FastAPI application
app = FastAPI(
    title="Dashboard",
    description="Real-time monitoring dashboard for arbitrage bot",
    version="2.0.0"
)

# Set up CORS middleware with WebSocket support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Set up paths
base_dir = Path(__file__).parent
static_path = base_dir / "static"
templates_path = base_dir / "templates"

logger.debug(f"Base directory: {base_dir}")
logger.debug(f"Static path: {static_path}")
logger.debug(f"Templates path: {templates_path}")
logger.debug(f"Static path exists: {static_path.exists()}")
logger.debug(f"Templates path exists: {templates_path.exists()}")

# Set up static files
if not static_path.exists():
    static_path.mkdir(parents=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Set up templates
templates = Jinja2Templates(directory=str(templates_path))

# Include API routes
app.include_router(api_router, prefix="/api")

# Include WebSocket routes at root level
app.include_router(websocket_router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        await service_manager.initialize()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown services on application shutdown."""
    try:
        await service_manager.shutdown()
        logger.info("Services shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down services: {e}")

@app.get("/")
async def root(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/metrics")
async def metrics_page(request: Request):
    """Serve the metrics page."""
    return templates.TemplateResponse("metrics.html", {"request": request})

@app.get("/system")
async def system_page(request: Request):
    """Serve the system page."""
    return templates.TemplateResponse("system.html", {"request": request})

@app.get("/history")
async def history_page(request: Request):
    """Serve the history page."""
    return templates.TemplateResponse("history.html", {"request": request})

@app.get("/opportunities")
async def opportunities_page(request: Request):
    """Serve the opportunities page."""
    return templates.TemplateResponse("opportunities.html", {"request": request})