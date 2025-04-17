#!/usr/bin/env python
"""
Run Test Server for Listonian Arbitrage Bot Dashboard

This script launches a FastAPI server that simulates real-time data for the
Listonian Arbitrage Bot dashboard. It generates mock data for testing the
dashboard UI without requiring a connection to the actual arbitrage bot.
"""

import os
import sys
import json
import time
import random
import asyncio
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
TEST_SERVER_PORT = 9050
TEST_SERVER_HOST = "0.0.0.0"
UPDATE_INTERVAL = 1.0  # seconds

# Initialize FastAPI app
app = FastAPI(title="Listonian Arbitrage Bot Test Dashboard")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup templates and static files
base_dir = Path(__file__).parent
templates = Jinja2Templates(
    directory=str(base_dir / "tests" / "dashboard" / "templates")
)
app.mount(
    "/static",
    StaticFiles(directory=str(base_dir / "tests" / "dashboard" / "static")),
    name="static",
)


# Mock data storage
class MockDataStore:
    def __init__(self):
        self.start_time = time.time()
        self.trade_history: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {
            "gas_price": 25.0,
            "network_status": "Connected",
            "uptime": 0,
            "performance": {
                "cpu_usage": 15.0,
                "memory_usage": 256.0,
                "scan_time": 120.0,
            },
        }
        self.dex_prices: Dict[str, float] = {
            "baseswap_v3": 42495201.744674,
            "uniswap_v3": 42498123.123456,
            "sushiswap_v2": 42490567.891234,
        }

    def update_metrics(self):
        """Update mock metrics with random variations"""
        # Update uptime
        self.metrics["uptime"] = int(time.time() - self.start_time)

        # Random variations for gas price (20-30 Gwei)
        self.metrics["gas_price"] = max(
            20.0, min(30.0, self.metrics["gas_price"] + random.uniform(-0.5, 0.5))
        )

        # Random variations for performance metrics
        self.metrics["performance"]["cpu_usage"] = max(
            5.0,
            min(
                95.0,
                self.metrics["performance"]["cpu_usage"] + random.uniform(-2.0, 2.0),
            ),
        )

        self.metrics["performance"]["memory_usage"] = max(
            128.0,
            min(
                512.0,
                self.metrics["performance"]["memory_usage"]
                + random.uniform(-10.0, 10.0),
            ),
        )

        self.metrics["performance"]["scan_time"] = max(
            50.0,
            min(
                200.0,
                self.metrics["performance"]["scan_time"] + random.uniform(-5.0, 5.0),
            ),
        )

        # Occasionally simulate network disconnection (1% chance)
        if random.random() < 0.01:
            self.metrics["network_status"] = (
                "Disconnected"
                if self.metrics["network_status"] == "Connected"
                else "Connected"
            )

    def update_prices(self):
        """Update mock DEX prices with small variations"""
        for dex in self.dex_prices:
            # Small price variations (±0.01%)
            variation = self.dex_prices[dex] * random.uniform(-0.0001, 0.0001)
            self.dex_prices[dex] += variation

    def generate_trade(self) -> Optional[Dict[str, Any]]:
        """Occasionally generate a mock trade (5% chance per update)"""
        if random.random() < 0.05:
            # Generate mock trade data
            timestamp = int(time.time())
            dexes = list(self.dex_prices.keys())
            path = f"{random.choice(dexes)} → {random.choice(dexes)}"

            # Trade parameters
            gas_used = random.randint(100000, 500000)
            gas_price = self.metrics["gas_price"]
            gas_cost_usd = (
                gas_used * gas_price * 1e-9
            ) * 2500  # Assuming ETH price of $2500

            # Profit calculation (70% chance of profitable trade)
            if random.random() < 0.7:
                profit = random.uniform(0.01, 0.5)  # $0.01 to $0.50
            else:
                profit = random.uniform(0.001, 0.01)  # Very small profit or break-even

            net_profit = profit - gas_cost_usd

            trade = {
                "timestamp": timestamp,
                "path": path,
                "profit": profit,
                "gas_used": gas_used,
                "gas_price": gas_price,
                "gas_cost_usd": gas_cost_usd,
                "net_profit": net_profit,
            }

            self.trade_history.append(trade)

            # Keep only the last 100 trades
            if len(self.trade_history) > 100:
                self.trade_history = self.trade_history[-100:]

            return trade

        return None

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all dashboard data for WebSocket updates"""
        return {
            "trade_history": self.trade_history,
            "metrics": self.metrics,
            "timestamp": datetime.datetime.now().isoformat(),
        }


# Initialize mock data store
mock_data = MockDataStore()


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            f"WebSocket client connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(
            f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}"
        )

    async def broadcast(self, data: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Error sending data to WebSocket: {e}")


# Initialize connection manager
manager = ConnectionManager()


# Background task to update and broadcast mock data
async def update_mock_data():
    while True:
        # Update mock data
        mock_data.update_metrics()
        mock_data.update_prices()
        trade = mock_data.generate_trade()

        # Log price updates (for debugging)
        if random.random() < 0.1:  # Only log occasionally to avoid spam
            dex = random.choice(list(mock_data.dex_prices.keys()))
            logger.debug(
                f"Received price update event (not processed): {{'dex': '{dex}', 'old_price': {mock_data.dex_prices[dex]}, 'new_price': {mock_data.dex_prices[dex]}}}"
            )

        # Log new trades
        if trade:
            logger.info(
                f"Generated mock trade: {trade['path']} with net profit: ${trade['net_profit']:.4f}"
            )

        # Broadcast updated data to all connected clients
        dashboard_data = mock_data.get_dashboard_data()

        # Log memory updates
        logger.debug(f"--- Handling Memory Update ---")
        logger.debug(f"Received update keys: {list(dashboard_data.keys())}")
        logger.debug(
            f"Received trade_history length: {len(dashboard_data['trade_history'])}"
        )
        logger.debug(
            f"Received memory_metrics keys: {list(dashboard_data['metrics'].keys())}"
        )
        logger.debug(f"Received memory update: {dashboard_data['timestamp']}")

        # Calculate some derived metrics (for logging only)
        net_profit_by_pair = {}
        avg_roi_by_trade_type = {}
        profit_per_gas = 0
        profit_distribution_by_strategy = {}

        logger.debug(f"Calculated net_profit_by_pair: {net_profit_by_pair}")
        logger.debug(f"Calculated avg_roi_by_trade_type: {avg_roi_by_trade_type}")
        logger.debug(f"Calculated profit_per_gas: {profit_per_gas}")
        logger.debug(
            f"Calculated profit_distribution_by_strategy: {profit_distribution_by_strategy}"
        )
        logger.debug(f"--- Finished Handling Memory Update ---")

        await manager.broadcast(dashboard_data)

        # Wait for the next update interval
        await asyncio.sleep(UPDATE_INTERVAL)


# Routes
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request):
    """Serve the dashboard HTML page"""
    return templates.TemplateResponse("test.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        # Send initial data
        await websocket.send_json(mock_data.get_dashboard_data())

        # Keep the connection open
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup_event():
    """Start the background task on server startup"""
    asyncio.create_task(update_mock_data())
    logger.info(f"Test server started on http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}")


# Main function to run the server
def main():
    """Run the FastAPI server using Uvicorn"""
    try:
        # Ensure directories exist
        templates_dir = base_dir / "tests" / "dashboard" / "templates"
        static_dir = base_dir / "tests" / "dashboard" / "static"

        templates_dir.mkdir(parents=True, exist_ok=True)
        static_dir.mkdir(parents=True, exist_ok=True)

        # Create empty CSS file if it doesn't exist
        css_file = static_dir / "styles.css"
        if not css_file.exists():
            with open(css_file, "w") as f:
                f.write(
                    """
/* Dashboard Styles */
body {
    background-color: #1e1e2f;
    color: #ffffff;
    font-family: 'Roboto', sans-serif;
}

.navbar {
    background-color: #1e1e2f;
    border-bottom: 1px solid #2e2e4f;
}

.card {
    background-color: #27293d;
    border: none;
    border-radius: 6px;
    margin-bottom: 20px;
    box-shadow: 0 1px 20px 0 rgba(0,0,0,.1);
}

.card-header {
    background-color: #2a2c42;
    border-bottom: 1px solid #2e2e4f;
    color: #ffffff;
    font-weight: 500;
}

.metric-label {
    color: #9a9a9a;
    font-size: 0.8rem;
    margin-bottom: 5px;
}

.metric-value {
    font-size: 1.2rem;
    font-weight: 500;
    margin-bottom: 10px;
}

.status-indicator {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 5px;
}

.status-connected {
    background-color: #00f2c3;
}

.status-disconnected {
    background-color: #fd5d93;
}

.chart-container {
    position: relative;
    height: 250px;
    width: 100%;
}

.trade-row {
    transition: background-color 0.3s;
}

.trade-row:hover {
    background-color: #2a2c42;
}

.profit-positive {
    color: #00f2c3;
}

.profit-negative {
    color: #fd5d93;
}

.progress {
    background-color: #2a2c42;
    height: 6px;
    margin-bottom: 15px;
}
                """
                )

        # Start the server
        uvicorn.run(
            "run_test_server:app",
            host=TEST_SERVER_HOST,
            port=TEST_SERVER_PORT,
            reload=False,
            log_level="info",
        )
    except Exception as e:
        logger.error(f"Error starting test server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
