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

from web3 import AsyncWeb3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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

# Web3 configuration
rpc_url = os.getenv('RPC_URL', 'https://mainnet.base.org')
chain_id = int(os.getenv('CHAIN_ID', '8453'))  # Base network
web3: AsyncWeb3 = None

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    try:
        # Initialize Web3
        global web3
        web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(rpc_url))
        
        # Test Web3 connection
        chain = await web3.eth.chain_id
        if chain != chain_id:
            raise ValueError(f"Chain ID mismatch: expected {chain_id}, got {chain}")
            
        logger.info(f"Connected to Base network (Chain ID: {chain})")
        logger.info("Dashboard components initialized")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    try:
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
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
            
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
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Get blockchain data
        try:
            if web3 and web3.eth:
                status["block_number"] = await web3.eth.block_number
                status["blockchain_connected"] = True
                status["gas_price"] = await web3.eth.gas_price
            else:
                status["blockchain_connected"] = False
                status["blockchain_error"] = "Web3 not initialized"
        except Exception as e:
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

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }