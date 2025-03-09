"""FastAPI application for the dashboard."""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from pathlib import Path
import traceback

from dashboard.core.logging import setup_logging, get_logger
from dashboard.routes.test import router as test_router

# Set up logging
setup_logging(level="DEBUG")
logger = get_logger("app")

# Create FastAPI application
app = FastAPI(
    title="Dashboard",
    description="Real-time monitoring dashboard for arbitrage bot",
    version="2.0.0"
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

# Include routers
app.include_router(test_router)

@app.get("/")
async def root():
    """Redirect root to test page."""
    return RedirectResponse(url="/test")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    logger.error(f"404 error for {request.url}: {exc}")
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "detail": str(exc)}
    )

@app.exception_handler(500)
async def server_error_handler(request, exc):
    """Handle 500 errors."""
    logger.error(f"500 error for {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all other exceptions."""
    logger.error(f"Unhandled exception for {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )