"""
Simple Arbitrage Dashboard
"""

import os
import logging
import json
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from web3.exceptions import Web3Exception

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard")

# Import WebSocket handler
from .websocket_handler import setup_websocket_routes, websocket_manager
from .arbitrage_monitor import ArbitrageMonitor

# Initialize templates
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Create FastAPI app
app = FastAPI(
    title="Arbitrage Dashboard",
    description="Dashboard for monitoring blockchain status",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

class DashboardState:
    """Global dashboard state."""
    def __init__(self):
        self.web3_client = None
        self.initialization_error: Optional[str] = None
        self.last_error_time: Optional[float] = None
        self.initialization_lock = asyncio.Lock()
        self.monitor = ArbitrageMonitor()
        self.metrics_task: Optional[asyncio.Task] = None
        self.retry_count = 0
        self.max_retries = 3

async def init_web3_client() -> Dict[str, Any]:
    """Initialize Web3 client."""
    state = app.state
    
    if state.web3_client and not state.initialization_error:
        logger.debug("Web3 client already initialized")
        return {"status": "success"}
        
    async with state.initialization_lock:
        try:
            # Load config
            logger.debug("Loading configuration from configs/production.json")
            with open("configs/production.json", "r") as f:
                config = json.load(f)
                
            rpc_url = config["web3"]["rpc_url"]
            logger.debug(f"Using RPC URL: {rpc_url}")
                
            # Initialize Web3 client
            logger.debug("Creating Web3 client instance")
            from arbitrage_bot.core.web3.client import Web3ClientImpl
            
            web3_client = Web3ClientImpl(
                rpc_endpoint=rpc_url,
                chain="base_mainnet"
            )
            
            # Initialize with timeout
            logger.debug("Starting Web3 client initialization")
            try:
                await asyncio.wait_for(web3_client.initialize(), timeout=30.0)
                logger.info("Web3 client initialized successfully")
                
                # Store client and clear error state
                state.web3_client = web3_client
                state.initialization_error = None
                state.last_error_time = None
                state.retry_count = 0
                
                return {"status": "success"}
                
            except asyncio.TimeoutError as e:
                error_msg = "Web3 client initialization timed out after 30 seconds"
                logger.error(error_msg)
                await web3_client.close()
                raise HTTPException(status_code=503, detail=error_msg)
                
        except FileNotFoundError:
            error_msg = "Configuration file not found at configs/production.json"
            logger.error(error_msg)
            state.initialization_error = error_msg
            raise HTTPException(status_code=500, detail=error_msg)
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file: {str(e)}"
            logger.error(error_msg)
            state.initialization_error = error_msg
            raise HTTPException(status_code=500, detail=error_msg)
            
        except Web3Exception as e:
            error_msg = f"Web3 error during initialization: {str(e)}"
            logger.error(error_msg)
            state.initialization_error = error_msg
            state.retry_count += 1
            raise HTTPException(status_code=503, detail=error_msg)
            
        except Exception as e:
            error_msg = f"Error initializing Web3 client: {str(e)}"
            logger.error(error_msg, exc_info=True)
            state.initialization_error = error_msg
            state.retry_count += 1
            raise HTTPException(status_code=500, detail=error_msg)

async def collect_and_broadcast_metrics():
    """Collect metrics and broadcast via WebSocket."""
    state = app.state
    while True:
        try:
            # Get latest metrics
            metrics = {
                'arbitrage': await state.monitor.get_arbitrage_metrics(),
                'flash_loan': await state.monitor.get_flash_loan_metrics(),
                'mev_protection': await state.monitor.get_mev_protection_metrics(),
                'gas': await state.monitor.get_gas_metrics(),
                'profit': await state.monitor.get_profit_metrics()
            }
            
            # Broadcast metrics
            await websocket_manager.broadcast_metrics(metrics)
            
            # Check for alerts
            await check_alerts(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}", exc_info=True)
            
        await asyncio.sleep(1)  # Update every second

async def check_alerts(metrics: Dict[str, Any]):
    """Check metrics for alert conditions."""
    try:
        # Check profit alerts
        if 'profit' in metrics:
            profit = metrics['profit']
            if profit.get('total_profit', 0) > 0.1:  # Alert on profits > 0.1 ETH
                await websocket_manager.broadcast_alert(
                    'profit',
                    f"High profit detected: {profit['total_profit']} ETH",
                    'success'
                )
        
        # Check MEV alerts
        if 'mev_protection' in metrics:
            mev = metrics['mev_protection']
            if mev.get('attacks_detected', 0) > 0:
                await websocket_manager.broadcast_alert(
                    'mev',
                    f"MEV attack detected! Risk level: {mev.get('risk_level', 'unknown')}",
                    'warning'
                )
        
        # Check gas alerts
        if 'gas' in metrics:
            gas = metrics['gas']
            if gas.get('average_gas_price', 0) > 100:  # Alert on high gas prices
                await websocket_manager.broadcast_alert(
                    'gas',
                    f"High gas price: {gas['average_gas_price']} GWEI",
                    'warning'
                )
                
    except Exception as e:
        logger.error(f"Error checking alerts: {e}", exc_info=True)

@app.on_event("startup")
async def startup_event():
    """Initialize the application."""
    logger.info("Starting arbitrage dashboard")
    
    # Initialize state and components
    app.state = DashboardState()
    
    try:
        # Initialize Web3 client
        await init_web3_client()
        
        # Initialize WebSocket routes
        await setup_websocket_routes(app)
        
        # Start metrics collection
        app.state.metrics_task = asyncio.create_task(collect_and_broadcast_metrics())
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}", exc_info=True)
        # Don't raise here - let the app start even if Web3 init fails
        # The status endpoint will show the error state

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources."""
    logger.info("Shutting down arbitrage dashboard")
    
    # Cancel metrics collection task
    if app.state.metrics_task:
        app.state.metrics_task.cancel()
        await asyncio.gather(app.state.metrics_task, return_exceptions=True)
    
    if app.state.web3_client:
        try:
            await app.state.web3_client.close()
            logger.info("Web3 client closed successfully")
        except Exception as e:
            logger.error(f"Error closing Web3 client: {str(e)}", exc_info=True)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the dashboard HTML page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.get("/api/status")
async def get_status():
    """Get blockchain connection status."""
    state = app.state
    
    try:
        # Check if we need to retry initialization
        if (state.initialization_error and 
            state.retry_count < state.max_retries):
            try:
                logger.info(f"Retrying Web3 initialization (attempt {state.retry_count + 1}/{state.max_retries})")
                await init_web3_client()
            except Exception as e:
                logger.error(f"Retry failed: {str(e)}")
        
        if not state.web3_client:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_connected",
                    "reason": state.initialization_error or "Web3 client not initialized",
                    "retries": state.retry_count,
                    "max_retries": state.max_retries
                }
            )
            
        try:
            # Get latest block with timeout
            logger.debug("Fetching latest block")
            block = await asyncio.wait_for(
                state.web3_client.get_block("latest"),
                timeout=10.0
            )
            
            # Get gas price with timeout
            logger.debug("Fetching gas price")
            gas_price = await asyncio.wait_for(
                state.web3_client.get_gas_price(),
                timeout=10.0
            )
            
            logger.info(f"Status check successful - Block: {block['number']}, Gas: {gas_price / 10**9} gwei")
            return JSONResponse(
                status_code=200,
                content={
                    "status": "connected",
                    "latest_block": block["number"],
                    "gas_price_gwei": gas_price / 10**9,
                    "chain": state.web3_client.chain
                }
            )
            
        except asyncio.TimeoutError:
            error_msg = "Blockchain request timed out after 10 seconds"
            logger.error(error_msg)
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "reason": error_msg
                }
            )
            
        except Web3Exception as e:
            error_msg = f"Web3 error: {str(e)}"
            logger.error(error_msg)
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "reason": error_msg
                }
            )
            
    except Exception as e:
        error_msg = f"Error getting status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "reason": error_msg
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
