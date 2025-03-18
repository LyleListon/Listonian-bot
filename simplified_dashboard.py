"""
Simplified Arbitrage Bot Dashboard

This dashboard integrates with the arbitrage bot modules.
"""

import os
import sys
import json
import time
import logging
import asyncio
import importlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not installed, using environment variables as is")

# FastAPI imports
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import uvicorn
    print("Successfully imported FastAPI modules")
except ImportError as e:
    print(f"ERROR: FastAPI import failed - {e}")
    print("Please install required packages: pip install fastapi uvicorn jinja2")
    sys.exit(1)

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "simplified_dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("simplified_dashboard")

# Initialize FastAPI app
app = FastAPI(
    title="Arbitrage Bot Dashboard",
    description="Dashboard that integrates with arbitrage bot modules",
    version="0.1.0",
)

# Set up Jinja2 templates
templates_dir = Path("templates")
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

# Mount static files
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Global variables
start_time = time.time()
web3_connected = False
arbitrage_modules_loaded = False
web3 = None

# Try to import arbitrage bot modules
try:
    import arbitrage_bot
    from arbitrage_bot.core.web3.web3_manager import Web3Manager
    from arbitrage_bot.core.dex.dex_manager import DexManager
    from arbitrage_bot.core.monitoring import get_performance_metrics
    from arbitrage_bot.core.transaction_manager import get_recent_transactions
    from arbitrage_bot.core.opportunity_finder import get_current_opportunities
    from arbitrage_bot.core.dex_manager import get_dex_status
    
    arbitrage_modules_loaded = True
    logger.info("Successfully imported arbitrage bot modules")
except ImportError as e:
    logger.warning(f"Could not import arbitrage bot modules: {e}")

async def setup_web3():
    """Initialize Web3 connection."""
    global web3, web3_connected
    try:
        from web3 import Web3
        from web3.net import AsyncNet
        from web3.eth import AsyncEth
        
        # Get provider URL from environment variable
        provider_url = os.getenv('BASE_RPC_URL')
        if provider_url:
            web3 = Web3(Web3.AsyncHTTPProvider(provider_url), 
                        modules={'eth': (AsyncEth,), 'net': (AsyncNet,)})
            if await web3.is_connected():
                web3_connected = True
                logger.info(f"Connected to Web3 provider at {provider_url}")
            else:
                logger.warning(f"Failed to connect to Web3 provider at {provider_url}")
        else:
            logger.warning("No BASE_RPC_URL found in environment")
    except Exception as e:
        logger.warning(f"Web3 connection failed: {e}")

async def get_network_name() -> str:
    """Get the name of the connected network."""
    if not web3_connected:
        return "Not Connected"
    
    try:
        chain_id = await web3.eth.chain_id
        networks = {
            1: "Ethereum Mainnet",
            3: "Ropsten Testnet",
            4: "Rinkeby Testnet",
            5: "Goerli Testnet",
            42: "Kovan Testnet",
            56: "Binance Smart Chain",
            137: "Polygon Mainnet",
            42161: "Arbitrum",
            10: "Optimism",
            8453: "Base"
        }
        return networks.get(chain_id, f"Unknown Network (Chain ID: {chain_id})")
    except Exception as e:
        logger.error(f"Failed to get network name: {e}")
        return "Unknown"

async def get_wallet_balance() -> str:
    """Get wallet balance in ETH."""
    if not web3_connected:
        return "Not Connected"
    
    wallet_address = os.getenv('WALLET_ADDRESS', '')
    if not wallet_address:
        return "No Wallet Configured"
    
    try:
        if not web3.is_address(wallet_address):
            return "Invalid Wallet Address"
        
        balance_wei = await web3.eth.get_balance(Web3.to_checksum_address(wallet_address))
        balance_eth = web3.from_wei(balance_wei, 'ether')
        return f"{balance_eth:.4f} ETH"
    except Exception as e:
        logger.error(f"Failed to get wallet balance: {e}")
        return "Error"

@app.on_event("startup")
async def startup_event():
    """Initialize Web3 connection on startup."""
    await setup_web3()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render dashboard index page."""
    # Format uptime
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    # Get real data from arbitrage bot components
    if arbitrage_modules_loaded:
        logger.info("Using real data from arbitrage bot modules")
        try:
            data = {
                "performance": await get_performance_metrics(),
                "transactions": await get_recent_transactions(),
                "opportunities": await get_current_opportunities(),
                "dexes": await get_dex_status()
            }
        except Exception as e:
            logger.error(f"Error getting real data: {e}")
            data = {
                "performance": {},
                "transactions": [],
                "opportunities": [],
                "dexes": []
            }
    else:
        logger.warning("Arbitrage modules not loaded")
        data = {
            "performance": {},
            "transactions": [],
            "opportunities": [],
            "dexes": [
                {"name": "BaseSwap", "status": "Unknown", "priority": 1},
                {"name": "PancakeSwap", "status": "Unknown", "priority": 2},
                {"name": "SushiSwap", "status": "Unknown", "priority": 3},
                {"name": "RocketSwap", "status": "Unknown", "priority": 4}
            ]
        }
    
    # Render template
    return templates.TemplateResponse("index.html", {
        "request": request,
        "status": await get_network_name(),
        "uptime": uptime,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wallet_balance": await get_wallet_balance(),
        "network": await get_network_name(),
        "arbitrage_modules_loaded": arbitrage_modules_loaded,
        "web3_connected": web3_connected,
        **data
    })

@app.get("/api/status")
async def api_status():
    """API endpoint for dashboard status."""
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    return {
        "status": await get_network_name(),
        "uptime": uptime,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wallet_balance": await get_wallet_balance(),
        "network": await get_network_name(),
        "arbitrage_modules_loaded": arbitrage_modules_loaded,
        "web3_connected": web3_connected
    }

if __name__ == "__main__":
    uvicorn.run(
        "simplified_dashboard:app",
        host=os.getenv('HOST', 'localhost'),
        port=int(os.getenv('PORT', '8080')),
        reload=os.getenv('DEBUG', 'true').lower() == 'true',
        log_level="info"
    )