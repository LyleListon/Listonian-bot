#!/usr/bin/env python
"""
Arbitrage Bot Dashboard - FastAPI Version

A lightweight dashboard for monitoring the arbitrage bot system.
This implementation uses FastAPI and minimizes dependencies for reliability.
"""

import os
import sys
import json
import time
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add python-dotenv for environment variable loading
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from web3 import Web3, HTTPProvider
import uvicorn

# Import bot data module
import bot_data
import arbitrage_connector

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "new_dashboard.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("arbitrage_dashboard")

# Initialize FastAPI app
app = FastAPI(
    title="Arbitrage Bot Dashboard",
    description="Monitoring dashboard for the arbitrage bot system",
    version="1.0.0",
)

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global variables
web3 = None
wallet_address = None
view_address = None
start_time = time.time()
error_message = None
info_message = None
debug_info = None
connector_initialized = False

def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    try:
        config_paths = [
            "configs/production.json",
            "configs/config.json"
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                logger.info(f"Loading configuration from {path}")
                with open(path, "r") as f:
                    return json.load(f)
                    
        logger.warning("No configuration file found, using empty config")
        return {}
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return {}

def initialize_web3():
    """Initialize Web3 connection and arbitrage connector."""
    global web3, wallet_address, view_address, error_message, info_message, debug_info, connector_initialized
    
    debug_info = ""
    
    try:
        config = load_config()
        
        # Try to get provider URL from .env or config
        provider_url = os.getenv('BASE_RPC_URL')
        if not provider_url:
            # Try network section from config
            network_config = config.get('network', {})
            provider_url = network_config.get('rpc_url', '')
            
            # If rpc_url contains $SECURE:, it's a placeholder
            if provider_url and provider_url.startswith('$SECURE:'):
                env_name = provider_url.replace('$SECURE:', '')
                provider_url = os.getenv(env_name, '')
        
        # Mask provider URL for security (hide API key)
        if provider_url:
            masked_url = provider_url
            if '/' in provider_url and len(provider_url) > 30:
                parts = provider_url.split('/')
                if len(parts[-1]) > 8:
                    parts[-1] = parts[-1][:4] + "..." + parts[-1][-4:]
                masked_url = '/'.join(parts)
            debug_info += f"Provider URL: {masked_url}\n"
        else:
            debug_info += "Provider URL: Not configured\n"
            error_message = "ERROR: No valid provider URL configured. Please set BASE_RPC_URL in .env file or environment variable."
            logger.error(error_message)
            return
        
        # Get wallet address from config or environment
        wallet_config = config.get('wallet', {})
        view_address = os.getenv('WALLET_ADDRESS')
        if not view_address:
            view_address = wallet_config.get('wallet_address', '')
            # Handle secure placeholder
            if view_address and view_address.startswith('$SECURE:'):
                env_name = view_address.replace('$SECURE:', '')
                view_address = os.getenv(env_name, '')
                
        debug_info += f"View address: {view_address}\n" if view_address else "View address: Not configured\n"
        
        # Try to connect to Ethereum node with better error handling
        try:
            web3 = Web3(HTTPProvider(provider_url))
        except Exception as e:
            error_message = f"ERROR: Failed to create Web3 provider: {str(e)}"
            logger.error(error_message)
            debug_info += f"Web3 provider error: {str(e)}\n"
            return
            
        # Check connection
        if not web3.is_connected():
            error_message = "ERROR: Failed to connect to Ethereum node. Please check your provider URL."
            logger.error(error_message)
            return
        
        debug_info += f"Connected to Web3: {web3.is_connected()}\n"
        debug_info += f"Checking Web3 connection: Network ID: {web3.eth.chain_id}\n"
        
        # If no view address is set, show info message
        if not view_address:
            info_message = "WARNING: No wallet address configured. Some features may not be available."
        else:
            # Validate wallet address format
            try:
                wallet_address = Web3.to_checksum_address(view_address)
                logger.info(f"Using wallet address: {wallet_address}")
            except Exception as e:
                error_message = f"ERROR: Invalid wallet address format. Please check your wallet address."
                logger.error(f"Failed to validate wallet address: {e}")
                debug_info += f"Wallet validation error: {str(e)}\n"
                wallet_address = None
        
        # Initialize arbitrage connector
        try:
            success, message = arbitrage_connector.connector.initialize()
            if success:
                connector_initialized = True
                logger.info("Arbitrage connector initialized successfully")
                debug_info += f"Arbitrage connector: Initialized\n"
            else:
                logger.warning(f"Failed to initialize arbitrage connector: {message}")
                debug_info += f"Arbitrage connector: Failed to initialize - {message}\n"
                info_message = f"WARNING: {message}. Trading functions may be limited."
        except Exception as e:
            logger.error(f"Error initializing arbitrage connector: {e}")
            debug_info += f"Arbitrage connector error: {str(e)}\n"
        
    except Exception as e:
        error_message = f"ERROR: Failed to initialize Web3 connection: {str(e)}"
        logger.error(f"Failed to initialize Web3: {e}")
        debug_info += f"Web3 initialization error: {str(e)}\n"

def get_network_name() -> str:
    """Get the name of the connected network."""
    if not web3 or not web3.is_connected():
        return "Not Connected"
    
    try:
        chain_id = web3.eth.chain_id
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

def get_wallet_balance() -> str:
    """Get wallet balance in ETH."""
    if not web3 or not web3.is_connected() or not wallet_address:
        return "Not Available"
    
    try:
        balance_wei = web3.eth.get_balance(wallet_address)
        balance_eth = web3.from_wei(balance_wei, 'ether')
        return f"{balance_eth:.4f} ETH"
    except Exception as e:
        logger.error(f"Failed to get wallet balance: {e}")
        return "Error"

def get_gas_price() -> str:
    """Get current gas price in Gwei."""
    if not web3 or not web3.is_connected():
        return "Not Available"
    
    try:
        gas_price_wei = web3.eth.gas_price
        gas_price_gwei = web3.from_wei(gas_price_wei, 'gwei')
        return f"{gas_price_gwei:.2f}"
    except Exception as e:
        logger.error(f"Failed to get gas price: {e}")
        return "Error"

def get_block_number() -> str:
    """Get latest block number."""
    if not web3 or not web3.is_connected():
        return "Not Available"
    
    try:
        return str(web3.eth.block_number)
    except Exception as e:
        logger.error(f"Failed to get block number: {e}")
        return "Error"

def get_recent_transactions() -> str:
    """Get recent transactions."""
    return "Transaction data unavailable in simplified dashboard."

def get_total_profit() -> str:
    """Get total profit."""
    if connector_initialized:
        try:
            # Try to get profit from arbitrage connector
            wallet_info = arbitrage_connector.connector.get_wallet_balance()
            if "eth_balance" in wallet_info and "usd_value" in wallet_info:
                return f"{wallet_info['eth_balance']:.4f} ETH (${wallet_info['usd_value']:.2f})"
        except Exception as e:
            logger.error(f"Failed to get profit from connector: {e}")
    
    # Fallback to bot data
    try:
        profit_data = bot_data.get_dashboard_data().get("profit_summary", {})
        if profit_data.get("total_profit_eth", 0) > 0:
            return f"{profit_data['total_profit_eth']:.4f} ETH"
    except Exception:
        pass
    
    return "Not Tracked"

def get_dynamic_allocation():
    """Get dynamic allocation settings from config."""
    config = load_config()
    dynamic_allocation = config.get('dynamic_allocation', {})
    return {
        "min_percentage": dynamic_allocation.get('min_percentage', "N/A"),
        "max_percentage": dynamic_allocation.get('max_percentage', "N/A"),
        "concurrent_trades": dynamic_allocation.get('concurrent_trades', "N/A"),
        "reserve_percentage": dynamic_allocation.get('reserve_percentage', "N/A"),
    }

def get_active_dexes():
    """Get active DEXes from config."""
    config = load_config()
    dexes = config.get('dexes', {})
    active_dexes = []
    
    for dex_name, dex_config in dexes.items():
        if dex_config.get('enabled', False):
            active_dexes.append({
                "name": dex_name,
                "status": "Active",
                "priority": dex_config.get('priority', 0)
            })
    
    return sorted(active_dexes, key=lambda x: x["priority"])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render dashboard index page."""
    # Format uptime
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    # Get Web3 data
    wallet_balance = get_wallet_balance()
    network = get_network_name()
    gas_price = get_gas_price()
    block_number = get_block_number()
    transactions = get_recent_transactions()
    total_profit = get_total_profit()
    
    # Format wallet address for display
    wallet_address_short = wallet_address[:6] + "..." + wallet_address[-4:] if wallet_address else "Not Available"
    
    # Get dynamic allocation values
    allocation = get_dynamic_allocation()
    
    # Get active DEXes
    active_dexes = get_active_dexes()
    
    # Set status based on Web3 connection
    status = "Running" if web3 and web3.is_connected() else "Not Connected"
    
    # Get connector status
    connector_status = {}
    if connector_initialized:
        connector_status = arbitrage_connector.connector.get_connection_status()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "status": status,
        "uptime": uptime,
        "wallet_balance": wallet_balance,
        "total_profit": total_profit,
        "min_percentage": allocation["min_percentage"],
        "max_percentage": allocation["max_percentage"],
        "concurrent_trades": allocation["concurrent_trades"],
        "reserve_percentage": allocation["reserve_percentage"],
        "config_json": json.dumps(load_config(), indent=2),
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "network": network,
        "gas_price": gas_price,
        "block_number": block_number,
        "wallet_address_short": wallet_address_short,
        "transactions": transactions,
        "error_message": error_message,
        "info_message": info_message,
        "debug_info": debug_info,
        "active_dexes": active_dexes,
        "bot_data": bot_data.get_dashboard_data(),
        "connector_status": connector_status,
        "connector_initialized": connector_initialized
    })

@app.get("/api/status")
async def api_status():
    """API endpoint for dashboard status."""
    # Format uptime
    uptime_seconds = int(time.time() - start_time)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{days}d {hours}h {minutes}m {seconds}s"
    
    # Get Web3 data
    wallet_balance = get_wallet_balance()
    network = get_network_name()
    gas_price = get_gas_price()
    block_number = get_block_number()
    transactions = get_recent_transactions()
    total_profit = get_total_profit()
    
    # Format wallet address for display
    wallet_address_short = wallet_address[:6] + "..." + wallet_address[-4:] if wallet_address else "Not Available"
    
    # Set status based on Web3 connection
    status = "Running" if web3 and web3.is_connected() else "Not Connected"
    
    # Get connector status
    connector_status = {}
    if connector_initialized:
        connector_status = arbitrage_connector.connector.get_connection_status()
    
    return {
        "status": status,
        "uptime": uptime,
        "wallet_balance": wallet_balance,
        "total_profit": total_profit,
        "transactions": transactions,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "network": network,
        "gas_price": gas_price,
        "block_number": block_number,
        "wallet_address_short": wallet_address_short,
        "error_message": error_message,
        "info_message": info_message,
        "debug_info": debug_info,
        "active_dexes": get_active_dexes(),
        "bot_data": bot_data.get_dashboard_data(),
        "connector_status": connector_status,
        "connector_initialized": connector_initialized
    }

@app.get("/api/bot-data")
async def bot_data_endpoint():
    """API endpoint for bot data."""
    return bot_data.get_dashboard_data()

@app.get("/api/logs")
async def bot_logs(limit: int = 100):
    """API endpoint for bot logs."""
    return {"logs": bot_data.get_recent_log_entries(max_entries=limit)}

@app.get("/api/transactions")
async def bot_transactions(limit: int = 10):
    """API endpoint for bot transactions."""
    return {"transactions": bot_data.get_transaction_history(max_entries=limit)}

@app.get("/api/opportunities")
async def bot_opportunities(limit: int = 10):
    """API endpoint for arbitrage opportunities."""
    return {"opportunities": bot_data.get_arbitrage_opportunities(max_entries=limit)}

# Define Pydantic models for API requests
class TradeRequest(BaseModel):
    buy_dex: str
    sell_dex: str
    token_address: str
    amount: float

class ExecuteOpportunityRequest(BaseModel):
    opportunity_id: str

class GasSettingsUpdate(BaseModel):
    gas_price: Optional[int] = None
    max_fee_per_gas: Optional[int] = None
    max_priority_fee: Optional[int] = None
    gas_limit_multiplier: Optional[float] = None

@app.get("/api/connector-status")
async def connector_status():
    """API endpoint for arbitrage connector status."""
    if not connector_initialized:
        return {"initialized": False, "error": "Arbitrage connector not initialized"}
    
    return arbitrage_connector.connector.get_connection_status()

@app.get("/api/profit-opportunities")
async def profit_opportunities():
    """Get current profit opportunities across DEXes."""
    if not connector_initialized:
        raise HTTPException(status_code=400, detail="Arbitrage connector not initialized")
    
    try:
        opportunities = arbitrage_connector.connector.find_arbitrage_opportunities()
        return {"opportunities": opportunities}
    except Exception as e:
        logger.error(f"Error getting profit opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute-trade")
async def execute_trade(trade: TradeRequest, background_tasks: BackgroundTasks):
    """Execute a manual trade between two DEXes."""
    if not connector_initialized:
        raise HTTPException(status_code=400, detail="Arbitrage connector not initialized")
    
    # Start the trade in a background task
    background_tasks.add_task(
        arbitrage_connector.connector.manual_trade,
        trade.buy_dex,
        trade.sell_dex,
        trade.token_address,
        trade.amount
    )
    
    return {"status": "Trade execution started in background"}

@app.post("/api/execute-opportunity")
async def execute_opportunity(request: ExecuteOpportunityRequest, background_tasks: BackgroundTasks):
    """Execute a specific arbitrage opportunity."""
    if not connector_initialized:
        raise HTTPException(status_code=400, detail="Arbitrage connector not initialized")
    
    # Start the execution in a background task
    background_tasks.add_task(
        arbitrage_connector.connector.execute_arbitrage,
        request.opportunity_id
    )
    
    return {"status": "Opportunity execution started in background"}

@app.get("/api/dex-prices/{token_address}")
async def get_dex_prices(token_address: str):
    """Get token prices across DEXes."""
    if not connector_initialized:
        raise HTTPException(status_code=400, detail="Arbitrage connector not initialized")
    
    prices = arbitrage_connector.connector.get_dex_prices(token_address)
    return {"token": token_address, "prices": prices}

@app.get("/api/profit-analysis/{token_address}")
async def profit_analysis(token_address: str):
    """Analyze profit potential for a token."""
    if not connector_initialized:
        raise HTTPException(status_code=400, detail="Arbitrage connector not initialized")
    
    result = arbitrage_connector.connector.calculate_profit_potential(token_address)
    return result

@app.get("/api/gas-settings")
async def get_gas_settings():
    """Get current gas settings."""
    if not connector_initialized:
        raise HTTPException(status_code=400, detail="Arbitrage connector not initialized")
    
    settings = arbitrage_connector.connector.get_gas_settings()
    return settings

@app.post("/api/update-gas-settings")
async def update_gas_settings(settings: GasSettingsUpdate):
    """Update gas settings for transactions."""
    if not connector_initialized:
        raise HTTPException(status_code=400, detail="Arbitrage connector not initialized")
    
    # Convert to dict and remove None values
    settings_dict = {k: v for k, v in settings.dict().items() if v is not None}
    
    success = arbitrage_connector.connector.update_gas_settings(settings_dict)
    if success:
        return {"status": "Gas settings updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update gas settings")

def init():
    """Initialize the dashboard."""
    global start_time
    start_time = time.time()
    initialize_web3()

# Initialize on startup
init()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start the arbitrage system dashboard")
    parser.add_argument(
        "--host", 
        default="localhost", 
        help="Host to run the dashboard on (default: localhost)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080, 
        help="Port to run the dashboard on (default: 8080)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Run in debug mode"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("STARTING ARBITRAGE SYSTEM DASHBOARD")
    logger.info("=" * 70)
    logger.info(f"Dashboard URL: http://{args.host}:{args.port}")
    
    uvicorn.run(
        "app:app", 
        host=args.host, 
        port=args.port, 
        reload=args.debug,
        log_level="info"
    )