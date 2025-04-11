"""
Production Dashboard Backend Application

Provides:
- WebSocket for real-time updates
- API endpoints for configuration
- System metrics and status
"""

import asyncio
import logging
from datetime import datetime
import os
from decimal import Decimal
from typing import Dict, Any, Set
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# --- Integration Imports ---
from typing import Optional  # Add Optional for global type hint

# Remove conflicting import from arbitrage_bot.dashboard.metrics_service
from .core.dependencies import register_services, lifespan  # Import registry functions
from .dashboard.routes import websocket as websocket_router  # Import the router

# --- End Integration Imports ---


# Initialize logger first
logger = logging.getLogger(__name__)

logger.info("=== About to register services BEFORE App Creation ===")
register_services()
# --- End Register Services ---

from arbitrage_bot.utils.config_loader import load_config, save_config
from .components import create_production_components


logger.info("=== About to create FastAPI app with lifespan context manager ===")
logger.info("lifespan type: %s", type(lifespan).__name__)

app = FastAPI(lifespan=lifespan)

# --- Include WebSocket Routes ---
app.include_router(websocket_router.router)  # Remove prefix to match static files
# --- End Include WebSocket Routes ---

# Get the directory containing this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Mount static files
app.mount(
    "/static", StaticFiles(directory=os.path.join(current_dir, "static")), name="static"
)


class TradingConfig(BaseModel):
    """Trading configuration parameters."""

    slippage: float
    maxLiquidity: int
    minProfit: float
    maxGasPrice: int


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.update_task = None

    async def connect(self, websocket: WebSocket):
        """Handle new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        if not self.update_task:
            self.update_task = asyncio.create_task(self.periodic_updates())

    async def disconnect(self, websocket: WebSocket):
        """Handle disconnection."""
        self.active_connections.remove(websocket)
        if not self.active_connections and self.update_task:
            self.update_task.cancel()
            self.update_task = None

    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead_connections.add(connection)

        # Cleanup dead connections
        for dead in dead_connections:
            self.active_connections.remove(dead)

    async def periodic_updates(self):
        """Send periodic updates to all clients."""
        try:
            while True:
                if not self.active_connections:
                    break

                # Get latest metrics
                metrics = await get_metrics()
                status = await get_status()

                # Broadcast update
                await self.broadcast(
                    {"type": "update", "metrics": metrics, "status": status}
                )

                await asyncio.sleep(1)  # Update every second
        except asyncio.CancelledError:
            pass


class SystemComponents:
    """Holds system component instances."""

    def __init__(self):
        """Initialize system components."""
        self.web3_manager = None
        self.market_analyzer = None
        self.arbitrage_executor = None
        self.memory_bank = None
        self.system_service = None


system = SystemComponents()
manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Initialize system components on startup."""
    logger.info("=== Running startup_event ===")
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()
        logger.info("Loaded configuration from file")

        # Initialize production components
        logger.info("Creating production components...")
        components = create_production_components(config)
        logger.info("Production components created.")

        # Set components
        logger.info("Assigning components...")
        system.web3_manager = components["web3_manager"]
        system.flash_loan_manager = components["flash_loan_manager"]
        system.market_analyzer = components["market_analyzer"]
        system.arbitrage_executor = components["arbitrage_executor"]
        system.system_service = components.get("system_service")
        system.memory_bank = components["memory_bank"]
        logger.info("Components assigned.")

        # Initialize components
        logger.info("Initializing Web3Manager...")
        await system.web3_manager.initialize()
        logger.info("Web3Manager initialized.")
        logger.info("Initializing MemoryBank...")
        await system.memory_bank.initialize()
        logger.info("MemoryBank initialized.")

        logger.info("System components initialized successfully")
        logger.info("=== startup_event finished ===")

    except Exception as e:
        logger.error(
            f"Failed to initialize components during startup: {e}", exc_info=True
        )
        # Optionally re-raise or handle differently depending on desired behavior
        raise  # Re-raise the exception to halt startup on error


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any incoming messages if needed
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


@app.get("/")
async def read_root():
    """Serve the dashboard HTML."""
    return FileResponse(os.path.join(current_dir, "static/index.html"))


@app.get("/api/config")
async def get_config():
    """Get current trading configuration."""
    config = load_config()
    return {
        "slippage": config.get("trading", {}).get("max_slippage", 0.5),
        "maxLiquidity": config.get("trading", {}).get("max_liquidity_usage", 30),
        "minProfit": config.get("trading", {}).get("min_profit_threshold", 0.01),
        "maxGasPrice": config.get("trading", {}).get("max_gas_price", 500),
    }


@app.post("/api/config")
async def update_config(trading_config: TradingConfig):
    """Update trading configuration."""
    try:
        # Load current config
        config = load_config()

        # Update trading parameters
        if "trading" not in config:
            config["trading"] = {}

        config["trading"].update(
            {
                "max_slippage": trading_config.slippage,
                "max_liquidity_usage": trading_config.maxLiquidity,
                "min_profit_threshold": trading_config.minProfit,
                "max_gas_price": trading_config.maxGasPrice,
            }
        )

        # Save updated config
        await save_config(config)

        # Update component configurations
        if system.flash_loan_manager:
            await system.flash_loan_manager.update_settings(
                max_slippage=Decimal(str(trading_config.slippage / 100)),
                min_profit_threshold=system.web3_manager.to_wei(
                    trading_config.minProfit, "ether"
                ),
            )

        if system.market_analyzer:
            await system.market_analyzer.update_settings(
                max_price_impact=Decimal(str(trading_config.slippage / 100))
            )

        if system.arbitrage_executor:
            await system.arbitrage_executor.update_settings(
                max_gas_price=system.web3_manager.to_wei(
                    trading_config.maxGasPrice, "gwei"
                )
            )

        # Update memory bank metrics
        await system.memory_bank.update_system_metrics(
            {
                "config_updated": True,
                "settings": {
                    "slippage": trading_config.slippage,
                    "max_liquidity": trading_config.maxLiquidity,
                    "min_profit": trading_config.minProfit,
                    "max_gas_price": trading_config.maxGasPrice,
                },
            }
        )

        # Broadcast update to all connected clients
        await manager.broadcast(
            {"type": "config_update", "config": trading_config.dict()}
        )

        logger.info("Trading configuration updated successfully")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_metrics():
    """Get real-time system metrics."""
    try:
        # Get wallet balance
        wallet_balance = await system.web3_manager.get_balance(
            system.web3_manager.wallet_address
        )
        wallet_balance_eth = system.web3_manager.from_wei(wallet_balance, "ether")

        # Get execution stats
        execution_stats = await system.arbitrage_executor.get_execution_stats()

        # Get current state
        current_state = await system.arbitrage_executor.get_current_state()

        # Get memory bank metrics
        metrics = await system.memory_bank.get_system_metrics()

        return {
            "walletBalance": float(wallet_balance_eth),
            "totalProfit": execution_stats.total_profit,
            "successRate": execution_stats.success_rate * 100,
            "averageGas": execution_stats.average_gas,
            "averageProfit": execution_stats.average_profit,
            "totalExecutions": execution_stats.total_executions,
            "currentState": current_state,
            "metrics": metrics,
        }

    except Exception as e:
        logger.error(f"Failed to fetch metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_status():
    """Get system status and health check."""
    try:
        # Get memory bank status
        memory_bank_status = await system.memory_bank.get_status()

        return {
            "status": "running",
            "web3_connected": await system.web3_manager.is_connected(),
            "components_initialized": all(
                [
                    system.web3_manager,
                    system.flash_loan_manager,
                    system.market_analyzer,
                    system.arbitrage_executor,
                ]
            ),
            "current_block": await system.web3_manager.get_block_number(),
            "memory_bank_status": memory_bank_status,
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/system/detailed")
async def get_detailed_system_metrics():
    """Get detailed system metrics."""
    try:
        # Get detailed metrics from system service
        detailed_metrics = await system.system_service.get_detailed_metrics()

        # Get resource usage
        resource_usage = await system.system_service.get_resource_usage()

        # Get health check
        health_check = await system.system_service.get_health_check()

        return {
            "detailed_metrics": detailed_metrics,
            "resource_usage": resource_usage,
            "health_check": health_check,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get detailed system metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trades")
async def get_trades():
    """Get recent trades."""
    try:
        # Get trades from memory bank
        state = await system.memory_bank.get_current_state()
        trades = state.get("trade_history", [])

        return {"trades": trades, "timestamp": datetime.utcnow().isoformat()}

    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=9050)
