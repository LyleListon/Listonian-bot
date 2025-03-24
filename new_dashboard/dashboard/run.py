"""Main entry point for running the dashboard."""

import sys
import asyncio
import uvicorn
import logging
import argparse
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from .utils.logging import configure_logging, get_logger
from .routes import metrics, system, main
from .services.service_manager import service_manager

# Configure logging
configure_logging()
logger = get_logger("dashboard")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    try:
        await service_manager.initialize()
        logger.info("Dashboard initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize dashboard: {e}")
        raise
    finally:
        try:
            await service_manager.shutdown()
            logger.info("Dashboard shut down successfully")
        except Exception as e:
            logger.error(f"Error during dashboard shutdown: {e}")

def create_app():
    """Create and configure the FastAPI application."""
    # Create FastAPI app
    app = FastAPI(
        title="Arbitrage Bot Dashboard",
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["GET", "POST"],  # Specify allowed methods
        expose_headers=["*"],  # Expose all headers
        allow_headers=["*"],  # Allow all headers
    )

    # Configure directories
    base_dir = Path(__file__).parent.resolve()
    templates_dir = base_dir / "templates"
    static_dir = base_dir / "static"
    js_dir = static_dir / "js"
    css_dir = static_dir / "css"

    logger.info("Base directory: %s", base_dir)
    logger.info("Templates directory: %s", templates_dir)
    logger.info("Static directory: %s", static_dir)

    # Create required directories
    logger.info("Creating required directories...")
    templates_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)
    css_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Directories created successfully")

    # Verify template files
    template_files = list(templates_dir.glob("*.html"))
    logger.info("Template files found: %s", template_files)

    # Configure static files and templates
    logger.info("Mounting static files from: %s", static_dir)
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")

    logger.info("Initializing templates with directory: %s", templates_dir)
    templates = Jinja2Templates(directory=str(templates_dir))

    # Share templates with routes
    logger.info("Setting up templates for routes...")
    main.templates = templates
    logger.info("Templates shared with main routes")

    # Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        # Allow necessary resources while maintaining security
        response.headers["Content-Security-Policy"] = (
            "default-src 'self';"
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net;"
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
            "img-src 'self' data:;"
            "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*;"
            "font-src 'self' https://cdn.jsdelivr.net;"
        )
        return response

    # Include routers
    app.include_router(main.router)  # Root router
    app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
    app.include_router(system.router, prefix="/api/system", tags=["system"])

    return app

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the dashboard application")
    parser.add_argument("--port", type=int, default=9095, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    return parser.parse_args()

# Create the app instance at module level for uvicorn
app = create_app()

def main():
    """Run the dashboard application."""
    try:
        args = parse_args()
        logger.info("Starting dashboard on %s:%d...", args.host, args.port)
        
        # Configure uvicorn logging to handle redirected stdout
        log_config = uvicorn.config.LOGGING_CONFIG
        log_config["formatters"]["default"]["use_colors"] = False
        log_config["formatters"]["access"]["use_colors"] = False
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=True,
            log_config=log_config
        )
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()