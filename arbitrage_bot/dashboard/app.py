"""
FastAPI dashboard application.

This module provides:
1. WebSocket endpoint for real-time updates
2. REST endpoints for static data
3. Error handling middleware
4. CORS configuration
"""

import os
import asyncio
import logging
from typing import Any, Dict
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from ..core import (
    get_cache,
    get_ws_manager,
    get_metrics_collector,
    get_web3_manager,
    Web3Error
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Arbitrage Bot Dashboard",
    description="Real-time monitoring dashboard for arbitrage bot",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize core components
logger.info(f"Initializing with RPC URL: {os.getenv('RPC_URL')}")
cache = get_cache()
ws_manager = get_ws_manager()
metrics_collector = get_metrics_collector()
web3 = get_web3_manager()

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    try:
        # Initialize Web3 first
        await web3.initialize()
        
        # Then start other components
        await ws_manager.start()
        await metrics_collector.start()
        await cache.start_cleanup_task()
        
        logger.info("Dashboard components initialized")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
        await ws_manager.stop()
        await metrics_collector.stop()
        await cache.stop_cleanup_task()
        logger.info("Dashboard components stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        raise

@app.get("/")
async def root():
    """Serve the dashboard frontend."""
    return FileResponse(str(static_dir / "index.html"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    try:
        await websocket.accept()
        await ws_manager.add_connection(websocket)
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()
                if data == "ping":
                    await ws_manager.handle_ping(websocket)
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        finally:
            await ws_manager.remove_connection(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if not websocket.client_state.is_disconnected:
            await websocket.close(code=1011)  # Internal error

@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Get current system status."""
    try:
        status = {
            "status": "running",
            "uptime": str(datetime.utcnow() - metrics_collector._start_time),
            "connections": ws_manager.connection_count,
            "connection_details": ws_manager.get_connection_info(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Try to get blockchain data
        try:
            status["block_number"] = await web3.get_block_number()
            status["blockchain_connected"] = True
        except Web3Error as e:
            logger.warning(f"Blockchain data unavailable: {e}")
            status["blockchain_connected"] = False
            status["blockchain_error"] = str(e)
            
        return status
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        metrics = {
            "system": await metrics_collector.get_system_metrics(),
            "performance": await metrics_collector.get_performance_metrics(),
            "errors": await metrics_collector.get_error_metrics(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Try to get blockchain metrics
        try:
            metrics["blockchain"] = await metrics_collector.get_blockchain_metrics()
        except Web3Error as e:
            logger.warning(f"Blockchain metrics unavailable: {e}")
            metrics["blockchain"] = {
                "error": str(e),
                "current_block": None,
                "blocks_per_minute": None
            }
            
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/errors")
async def get_errors() -> Dict[str, Any]:
    """Get error metrics."""
    try:
        return await metrics_collector.get_error_metrics()
    except Exception as e:
        logger.error(f"Error getting error metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/performance")
async def get_performance() -> Dict[str, Any]:
    """Get performance metrics."""
    try:
        return await metrics_collector.get_performance_metrics()
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/api/connections")
async def get_connections() -> Dict[str, Any]:
    """Get WebSocket connection details."""
    try:
        return ws_manager.get_connection_info()
    except Exception as e:
        logger.error(f"Error getting connection info: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
