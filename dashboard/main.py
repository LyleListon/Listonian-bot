"""
Arbitrage Dashboard FastAPI Application

This module provides the main FastAPI application for the arbitrage dashboard.
"""

import os
import asyncio
import logging
import json
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Import our arbitrage API module
from dashboard.api import arbitrage_api

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/dashboard.log")
    ]
)

logger = logging.getLogger("dashboard")

# Create FastAPI app
app = FastAPI(
    title="Listonian Arbitrage Dashboard",
    description="Dashboard for monitoring and controlling the arbitrage system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="dashboard/templates")

# Include our API router
app.include_router(arbitrage_api.router)

@app.on_event("startup")
async def startup_event():
    """
    Initialize the application on startup.
    
    This will:
    1. Create necessary directories
    2. Load configuration
    3. Initialize the arbitrage system
    """
    logger.info("Starting arbitrage dashboard")
    
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Load configuration
    try:
        config_path = os.environ.get("CONFIG_PATH", "configs/production.json")
        if not os.path.exists(config_path):
            logger.warning(f"Configuration file {config_path} not found, using default")
            config_path = "configs/default_config.json"
            
            # If default config doesn't exist either, create a minimal one
            if not os.path.exists(config_path):
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, "w") as f:
                    json.dump({
                        "general": {"network": "base_mainnet", "log_level": "INFO"},
                        "arbitrage": {"min_profit_threshold_eth": 0.005}
                    }, f, indent=2)
        
        with open(config_path, "r") as f:
            config = json.load(f)
            
        logger.info(f"Loaded configuration from {config_path}")
        
        # Initialize arbitrage system
        await initialize_arbitrage_system(config, config_path)
        
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        # Continue startup even if there's an error, but the API will return errors
        # until the arbitrage system is properly initialized

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on shutdown.
    """
    logger.info("Shutting down arbitrage dashboard")
    
    # Get arbitrage system if it's initialized
    try:
        arbitrage_system = arbitrage_api.get_arbitrage_system()
        if arbitrage_system and arbitrage_system.is_running:
            logger.info("Stopping arbitrage system")
            await arbitrage_system.stop()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

async def initialize_arbitrage_system(config: Dict[str, Any], config_path: str):
    """
    Initialize the arbitrage system with the provided configuration.
    
    Args:
        config: Configuration dictionary
        config_path: Path to the config file
    """
    try:
        # Validate required config fields
        network_config = config.get("network", {})
        rpc_endpoints = network_config.get("rpc_endpoints", [])
        flashbots_rpc = network_config.get("flashbots_rpc")
        chain = network_config.get("chain")

        if not rpc_endpoints:
            raise ValueError("No RPC endpoints configured")
        if not flashbots_rpc:
            raise ValueError("Flashbots RPC endpoint not configured")
        if not chain:
            raise ValueError("Chain not configured")

        from arbitrage_bot.core.arbitrage.factory import create_arbitrage_system
        from arbitrage_bot.core.web3.client import Web3ClientImpl
        
        # Create Web3 client
        logger.info("Creating Web3 client")
        web3_client = Web3ClientImpl(
            rpc_endpoint=rpc_endpoints[0],
            chain=chain
        )
        await web3_client.initialize()
        
        # Create arbitrage system
        logger.info("Creating arbitrage system")
        arbitrage_system = await create_arbitrage_system(
            web3_client=web3_client,
            config=config
        )
        
        # Initialize the system
        logger.info("Initializing arbitrage system")
        await arbitrage_system.initialize()
        
        arbitrage_api.set_arbitrage_system(arbitrage_system)
        logger.info("Arbitrage system initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing arbitrage system: {e}", exc_info=True)
        # API will return errors until arbitrage system is properly initialized

@app.get("/")
async def root(request: Request):
    """Serve the main dashboard page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/opportunities")
async def opportunities_page(request: Request):
    """Serve the opportunities page."""
    return templates.TemplateResponse("opportunities.html", {"request": request})

@app.get("/executions")
async def executions_page(request: Request):
    """Serve the executions page."""
    return templates.TemplateResponse("executions.html", {"request": request})

@app.get("/metrics")
async def metrics_page(request: Request):
    """Serve the metrics page."""
    return templates.TemplateResponse("metrics.html", {"request": request})

@app.get("/settings")
async def settings_page(request: Request):
    """Serve the settings page."""
    return templates.TemplateResponse("settings.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Try to get arbitrage system to check if it's initialized
        arbitrage_api.get_arbitrage_system()
        return {"status": "healthy"}
    except HTTPException:
        # Return degraded if arbitrage system is not initialized
        return {"status": "degraded", "reason": "arbitrage_system_not_initialized"}
    except Exception as e:
        return {"status": "unhealthy", "reason": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)