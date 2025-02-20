"""Minimal dashboard for monitoring arbitrage opportunities."""

import logging
import os
from datetime import datetime
import json
import asyncio
from decimal import Decimal

# Import eventlet and patch first
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO
from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.memory import get_memory_bank, init_memory_bank
from arbitrage_bot.utils.secure_env import init_secure_environment
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.utils.gas_logger import GasLogger
from arbitrage_bot.core.market_analyzer import create_market_analyzer
from arbitrage_bot.core.dex.dex_manager import create_dex_manager

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Set up logging to file
log_file = os.path.join(logs_dir, f'dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

# Log startup
logger.info("Starting minimal dashboard...")

# Get absolute paths
root_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join('minimal_dashboard', 'templates')
static_dir = os.path.join('minimal_dashboard', 'static')

# Create static directory if it doesn't exist
os.makedirs(static_dir, exist_ok=True)

# Initialize Flask app
app = Flask(__name__, 
           template_folder=template_dir,
           static_folder=static_dir)

# Initialize SocketIO with eventlet
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=10,
    max_http_buffer_size=1000000,
    transport=['websocket', 'polling'],
    path='/socket.io/'
)

# Initialize secure environment
secure_env = init_secure_environment()

# Load configuration
config = load_config()

# Verify gas configuration
if 'gas' not in config:
    raise ValueError("Gas configuration not found in config")
if 'max_priority_fee' not in config['gas'] or 'max_fee' not in config['gas']:
    raise ValueError("Missing gas fee configuration")

# Get RPC URL from secure environment
rpc_url = secure_env.secure_load('BASE_RPC_URL')
if not rpc_url:
    raise ValueError("BASE_RPC_URL not found in secure environment")

# Initialize Web3 manager
web3_manager = create_web3_manager(
    provider_url=rpc_url,
    chain_id=config.get('network', {}).get('chainId')
)

# Initialize DEX manager
logger.info("Initializing DEX manager...")
dex_manager = None

async def init_dex_manager():
    """Initialize DEX manager asynchronously."""
    global dex_manager
    dex_manager = await create_dex_manager(web3_manager, config)
    logger.info("DEX manager initialized")

# Run the initialization in the background
eventlet.spawn(lambda: asyncio.run(init_dex_manager()))

# Initialize market analyzer
market_analyzer = create_market_analyzer(dex_manager=dex_manager)

# Initialize gas logger
gas_logger = GasLogger()

# Initialize memory bank
init_memory_bank()
memory_bank = get_memory_bank()

# Token symbol cache
token_symbols = {}

def get_token_symbol(token_address: str) -> str:
    """Get human-readable token symbol."""
    if token_address in token_symbols:
        return token_symbols[token_address]
    
    try:
        token_contract = web3_manager.get_token_contract(token_address)
        symbol = token_contract.functions.symbol().call()
        token_symbols[token_address] = symbol
        return symbol
    except Exception as e:
        logger.error(f"Error getting token symbol: {e}")
        return token_address[:8]

@app.route('/')
def index():
    """Render dashboard template."""
    return render_template('index.html')

def emit_memory_stats():
    """Emit memory bank statistics."""
    try:
        stats = memory_bank.get_stats()
        socketio.emit('memory_update', stats)
        logger.debug(f"Emitted memory stats: {stats}")
    except Exception as e:
        logger.error(f"Error emitting memory stats: {e}")
        socketio.emit('memory_update', {'error': str(e)})

def emit_gas_prices():
    """Emit current gas prices."""
    try:
        # Get current gas prices
        gas_price = web3_manager.w3.eth.gas_price / 1e9  # Convert to gwei
        latest_block = web3_manager.w3.eth.get_block('latest')
        base_fee = latest_block.get('base_fee_per_gas', 0) / 1e9  # Convert to gwei

        # Get monthly gas usage summary
        monthly_summary = gas_logger.get_monthly_summary()
        
        gas_data = {
            'current_gas_price': f"{gas_price:.2f}",
            'base_fee': f"{base_fee:.2f}",
            'max_priority_fee': config['gas']['max_priority_fee'],
            'max_fee': config['gas']['max_fee'],
            'monthly_stats': {
                'total_gas_used': monthly_summary['total_gas_used'],
                'total_gas_cost': f"{monthly_summary['total_gas_cost_eth']:.6f} ETH",
                'average_gas_price': f"{monthly_summary['average_gas_price_gwei']:.2f} gwei",
                'transfers_to_recipient': monthly_summary['transfers_to_recipient'],
                'kept_in_wallet': monthly_summary['kept_in_wallet'],
                'highest_gas_price': f"{monthly_summary['highest_gas_price_gwei']:.2f} gwei",
                'lowest_gas_price': f"{monthly_summary['lowest_gas_price_gwei']:.2f} gwei"
            },
            'estimated_next_cost': f"${config['trading']['min_profit_usd']:.2f}",
            'timestamp': datetime.now().timestamp()
        }
        socketio.emit('gas_update', gas_data)
        logger.debug(f"Emitted gas prices: {gas_data}")
    except Exception as e:
        logger.error(f"Error emitting gas prices: {e}")
        socketio.emit('gas_update', {'error': str(e)})

def emit_market_data():
    """Emit real market data from market analyzer."""
    try:
        if not dex_manager or not dex_manager.initialized:
            logger.warning("DEX manager not initialized yet")
            return

        # Get real opportunities from market analyzer
        logger.debug("Fetching market opportunities...")
        opportunities = market_analyzer.get_opportunities()
        
        # Format opportunities for display
        formatted_opportunities = []
        for opp in opportunities:
            # Get human-readable token symbols
            token_in_symbol = get_token_symbol(opp['token'])
            token_out_symbol = get_token_symbol(opp['dex_to_path'][-1])
            
            # Calculate status based on profitability
            status = 'profitable' if opp['profit_usd'] > config['trading']['min_profit_usd'] else 'monitoring'
            
            formatted_opp = {
                'pair': f"{token_in_symbol}/{token_out_symbol}",
                'dex': f"{opp['dex_from']} → {opp['dex_to']}",
                'size': f"${float(opp['amount_in']):.2f}",
                'gross_profit': f"${float(opp['profit_usd']):.2f}",
                'net_profit': f"${max(0, float(opp['profit_usd']) - float(config['trading']['min_profit_usd'])):.2f}",
                'price_diff': f"{float(opp['price_diff']) * 100:.2f}%",
                'liquidity': f"${float(min(opp['liquidity_from'], opp['liquidity_to'])):.2f}",
                'status': status,
                'timestamp': datetime.fromtimestamp(opp['timestamp']).strftime('%H:%M:%S')
            }
            formatted_opportunities.append(formatted_opp)
        
        # Sort by net profit (descending)
        formatted_opportunities.sort(
            key=lambda x: float(x['net_profit'].lstrip('$')), 
            reverse=True
        )
        
        market_data = {
            'opportunities': formatted_opportunities,
            'gas_cost': f"${config['trading']['min_profit_usd']:.2f}",
            'dex_status': {
                name: 'active' if dex.is_enabled() else 'inactive'
                for name, dex in dex_manager.dex_instances.items()
            }
        }
        socketio.emit('market_update', market_data)
        logger.debug(f"Emitted market data with {len(formatted_opportunities)} opportunities")
    except Exception as e:
        logger.error(f"Error emitting market data: {e}")
        socketio.emit('market_update', {'error': str(e)})

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info("Client connected")
    eventlet.sleep(1)  # Brief delay to ensure components are ready
    emit_memory_stats()
    emit_gas_prices()
    emit_market_data()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info("Client disconnected")

def update_dashboard():
    """Update dashboard components."""
    while True:
        try:
            logger.debug("Updating dashboard data...")
            emit_memory_stats()
            emit_gas_prices()
            emit_market_data()
            eventlet.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            eventlet.sleep(5)

if __name__ == '__main__':
    try:
        logger.info(f"Template directory: {template_dir}")
        logger.info(f"Static directory: {static_dir}")
        
        # Start update thread
        eventlet.spawn(update_dashboard)
        logger.info("Started update thread")
        logger.info(f"Server starting at http://localhost:5000")
        
        # Start server
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")