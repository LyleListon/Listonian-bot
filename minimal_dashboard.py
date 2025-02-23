"""Minimal dashboard for monitoring arbitrage opportunities."""

import logging
import os
from datetime import datetime
import json
import asyncio
from decimal import Decimal
from aiohttp import web
import aiohttp_cors
from aiohttp_sse import sse_response
import aiohttp
import jinja2
import aiohttp_jinja2

from arbitrage_bot.utils.config_loader import load_config
from arbitrage_bot.core.memory import create_memory_bank, get_memory_bank
from arbitrage_bot.utils.secure_env import init_secure_environment
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.utils.gas_logger import GasLogger
from arbitrage_bot.core.market_analyzer import create_market_analyzer
from arbitrage_bot.core.dex.dex_manager import create_dex_manager

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Set up logging to file
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(logs_dir, 'dashboard_{}.log'.format(timestamp))
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
web3_manager = None

# Initialize DEX manager
logger.info("Initializing DEX manager...")
dex_manager = None

# Token symbol cache
token_symbols = {}

async def init_web3_manager():
    """Initialize Web3 manager asynchronously."""
    global web3_manager
    web3_manager = await create_web3_manager(
        provider_url=rpc_url,
        chain_id=config.get('network', {}).get('chainId')
    )
    logger.info("Web3 manager initialized")

async def init_dex_manager():
    """Initialize DEX manager asynchronously."""
    global dex_manager
    dex_manager = await create_dex_manager(web3_manager, config)
    logger.info("DEX manager initialized")

async def get_token_symbol(token_address: str) -> str:
    """Get human-readable token symbol."""
    if token_address in token_symbols:
        return token_symbols[token_address]
    
    try:
        token_contract = web3_manager.get_token_contract(token_address)
        symbol = await token_contract.functions.symbol().call()
        token_symbols[token_address] = symbol
        return symbol
    except Exception as e:
        logger.error("Error getting token symbol: {}".format(e))
        return token_address[:8]

class Dashboard:
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.clients = set()
        self.gas_logger = GasLogger()
        self.memory_bank = None
        self.market_analyzer = None
        self.update_task = None
        self._init_lock = asyncio.Lock()
        self._initialized = False

    def setup_routes(self):
        """Set up application routes."""
        aiohttp_jinja2.setup(
            self.app,
            loader=jinja2.FileSystemLoader(template_dir)
        )
        
        self.app.router.add_static('/static', static_dir)
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/events', self.events)

        # Set up CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*"
            )
        })

        # Configure CORS on all routes
        for route in list(self.app.router.routes()):
            cors.add(route)

    async def initialize(self):
        """Initialize dashboard components."""
        async with self._init_lock:
            if self._initialized:
                return
            
            # Initialize memory bank
            self.memory_bank = await create_memory_bank(config)
            logger.info("Memory bank initialized")
            
            self._initialized = True

    @aiohttp_jinja2.template('index.html')
    async def index(self, request):
        """Render dashboard template."""
        return {}

    async def events(self, request):
        """Server-sent events endpoint."""
        async with sse_response(request) as resp:
            self.clients.add(resp)
            try:
                while True:
                    await self.send_updates(resp)
                    await asyncio.sleep(5)
            finally:
                self.clients.remove(resp)
            return resp

    async def send_updates(self, resp):
        """Send updates to connected clients."""
        try:
            await self.send_memory_stats(resp)
            await self.send_gas_prices(resp)
            await self.send_market_data(resp)
        except Exception as e:
            logger.error("Error sending updates: {}".format(e))

    async def send_memory_stats(self, resp):
        """Send memory bank statistics."""
        try:
            stats = await self.memory_bank.get_memory_stats()
            await resp.send_json({'type': 'memory_update', 'data': stats})
        except Exception as e:
            logger.error("Error sending memory stats: {}".format(e))

    async def send_gas_prices(self, resp):
        """Send current gas prices."""
        try:
            gas_price = await web3_manager.w3.eth.gas_price / 1e9
            latest_block = await web3_manager.w3.eth.get_block('latest')
            base_fee = latest_block.get('base_fee_per_gas', 0) / 1e9

            monthly_summary = self.gas_logger.get_monthly_summary()
            
            gas_data = {
                'current_gas_price': "{:.2f}".format(gas_price),
                'base_fee': "{:.2f}".format(base_fee),
                'max_priority_fee': config['gas']['max_priority_fee'],
                'max_fee': config['gas']['max_fee'],
                'monthly_stats': {
                    'total_gas_used': monthly_summary['total_gas_used'],
                    'total_gas_cost': "{:.6f} ETH".format(monthly_summary['total_gas_cost_eth']),
                    'average_gas_price': "{:.2f} gwei".format(monthly_summary['average_gas_price_gwei']),
                    'transfers_to_recipient': monthly_summary['transfers_to_recipient'],
                    'kept_in_wallet': monthly_summary['kept_in_wallet'],
                    'highest_gas_price': "{:.2f} gwei".format(monthly_summary['highest_gas_price_gwei']),
                    'lowest_gas_price': "{:.2f} gwei".format(monthly_summary['lowest_gas_price_gwei'])
                },
                'estimated_next_cost': "${:.2f}".format(config['trading']['min_profit_usd']),
                'timestamp': datetime.now().timestamp()
            }
            await resp.send_json({'type': 'gas_update', 'data': gas_data})
        except Exception as e:
            logger.error("Error sending gas prices: {}".format(e))

    async def send_market_data(self, resp):
        """Send real market data from market analyzer."""
        try:
            if not dex_manager or not dex_manager.initialized:
                logger.warning("DEX manager not initialized yet")
                return

            opportunities = await self.market_analyzer.get_opportunities()
            
            formatted_opportunities = []
            for opp in opportunities:
                token_in_symbol = await get_token_symbol(opp['token'])
                token_out_symbol = await get_token_symbol(opp['dex_to_path'][-1])
                
                status = 'profitable' if opp['profit_usd'] > config['trading']['min_profit_usd'] else 'monitoring'
                
                formatted_opp = {
                    'pair': "{}/{}".format(token_in_symbol, token_out_symbol),
                    'dex': "{} → {}".format(opp['dex_from'], opp['dex_to']),
                    'size': "${:.2f}".format(float(opp['amount_in'])),
                    'gross_profit': "${:.2f}".format(float(opp['profit_usd'])),
                    'net_profit': "${:.2f}".format(max(0, float(opp['profit_usd']) - float(config['trading']['min_profit_usd']))),
                    'price_diff': "{:.2f}%".format(float(opp['price_diff']) * 100),
                    'liquidity': "${:.2f}".format(float(min(opp['liquidity_from'], opp['liquidity_to']))),
                    'status': status,
                    'timestamp': datetime.fromtimestamp(opp['timestamp']).strftime('%H:%M:%S')
                }
                formatted_opportunities.append(formatted_opp)
            
            formatted_opportunities.sort(
                key=lambda x: float(x['net_profit'].lstrip('$')), 
                reverse=True
            )
            
            market_data = {
                'opportunities': formatted_opportunities,
                'gas_cost': "${:.2f}".format(config['trading']['min_profit_usd']),
                'dex_status': {
                    name: 'active' if dex.is_enabled() else 'inactive'
                    for name, dex in dex_manager.dex_instances.items()
                }
            }
            await resp.send_json({'type': 'market_update', 'data': market_data})
        except Exception as e:
            logger.error("Error sending market data: {}".format(e))

    async def start(self):
        """Start the dashboard application."""
        try:
            # Initialize components
            await init_web3_manager()
            await self.initialize()
            await init_dex_manager()
            self.market_analyzer = create_market_analyzer(dex_manager=dex_manager)
            
            # Start update task
            self.update_task = asyncio.create_task(self.update_loop())
            
            # Start web server
            runner = web.AppRunner(self.app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', 5000)
            await site.start()
            
            logger.info("Dashboard started at http://localhost:5000")
            
            # Keep the server running
            while True:
                await asyncio.sleep(3600)  # Sleep for an hour
                
        except Exception as e:
            logger.error("Error starting dashboard: {}".format(e))
            raise
        finally:
            if self.update_task:
                self.update_task.cancel()

    async def update_loop(self):
        """Background task to update connected clients."""
        while True:
            try:
                for client in self.clients:
                    await self.send_updates(client)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error("Error in update loop: {}".format(e))
                await asyncio.sleep(5)

async def main():
    """Main entry point."""
    dashboard = Dashboard()
    await dashboard.start()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
    except Exception as e:
        logger.error("Dashboard error: {}".format(e))
        raise