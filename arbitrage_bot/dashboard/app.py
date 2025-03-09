"""Flask application for arbitrage bot dashboard."""

import asyncio
from ..utils.async_manager import manager, async_init

import os
import json
import logging
import time
from datetime import datetime
from typing import Any, Optional, Tuple
from aiohttp import web
import aiohttp_cors
from aiohttp_sse import sse_response
import aiohttp_jinja2
import jinja2
from ..core.memory.bank import create_memory_bank
from ..core.storage.factory import create_storage_hub
from ..core.distribution.manager import DistributionManager
from ..core.distribution.config import DistributionConfig
from ..core.execution.manager import ExecutionManager
from ..core.execution.config import ExecutionConfig
from ..core.web3.web3_manager import create_web3_manager
from ..core.metrics.portfolio_tracker import create_portfolio_tracker
from ..core.gas.gas_optimizer import create_gas_optimizer
from ..core.analysis import create_memory_market_analyzer
from ..utils.config_loader import resolve_secure_values
from decimal import Decimal
from .websocket_server import WebSocketServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

INIT_WAIT = 2  # Wait 2 seconds between component initializations

async def create_app(memory_bank=None, storage_hub=None) -> Tuple[web.Application, WebSocketServer]:
    """Create aiohttp application."""
    try:
        # Initialize async manager
        try:
            await async_init()
            if not manager._initialized:
                raise RuntimeError("Failed to initialize async manager")
            logger.info("Successfully initialized async event loop")
        except Exception as e:
            logger.error("Failed to initialize async manager: %s", str(e))
            raise
        
        # Initialize aiohttp app with absolute paths
        dashboard_dir = os.path.dirname(os.path.abspath(__file__))
        app = web.Application()
        
        # Set up jinja2 templates
        aiohttp_jinja2.setup(
            app,
            loader=jinja2.FileSystemLoader(os.path.join(dashboard_dir, 'templates'))
        )
        
        # Set up static files
        app.router.add_static('/static', os.path.join(dashboard_dir, 'static'))
        
        # Configure CORS
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*"
            )
        })

        # Load config
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'config.json')
        with open(config_path) as f:
            config = json.load(f)

        # Resolve secure values in config
        config = resolve_secure_values(config)
        logger.info("Resolved secure values in config")

        # Initialize components with delays between each
        web3_manager = await create_web3_manager(
            provider_url=os.getenv('BASE_RPC_URL'),
            chain_id=config['network']['chainId']
        )
        await asyncio.sleep(INIT_WAIT)

        # Use provided memory_bank or create new one
        if memory_bank is None:
            memory_bank = await create_memory_bank()
        await asyncio.sleep(INIT_WAIT)

        # Use provided storage_hub or create new one
        if storage_hub is None:
            storage_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'storage')
            os.makedirs(storage_path, exist_ok=True)
            storage_hub = await create_storage_hub(base_path=storage_path, memory_bank=memory_bank)
        await asyncio.sleep(INIT_WAIT)

        market_analyzer = await create_memory_market_analyzer(web3_manager, config)
        await asyncio.sleep(INIT_WAIT)

        portfolio_tracker = await create_portfolio_tracker(
            web3_manager=web3_manager,
            wallet_address=web3_manager.wallet_address,
            config=config
        )
        await asyncio.sleep(INIT_WAIT)

        # Initialize distribution manager
        distribution_config = DistributionConfig(
            max_exposure_per_dex=Decimal('1.0'),
            max_exposure_per_pair=Decimal('0.5'),
            min_liquidity_threshold=Decimal('10000'),
            rebalance_threshold=Decimal('0.2'),
            gas_price_weight=0.3,
            liquidity_weight=0.3,
            volume_weight=0.2,
            success_rate_weight=0.2
        )
        distribution_manager = DistributionManager(
            config=distribution_config,
            memory_bank=memory_bank,
            storage_hub=storage_hub
        )
        await distribution_manager.initialize()
        await asyncio.sleep(INIT_WAIT)
        
        # Initialize execution manager
        execution_config = ExecutionConfig(
            max_slippage=Decimal("0.005"),
            gas_limit=300000,
            max_gas_price=Decimal("100"),
            retry_attempts=3,
            retry_delay=5,
            confirmation_blocks=2,
            timeout=60
        )
        execution_manager = ExecutionManager(
            config=execution_config,
            web3=web3_manager.w3,
            distribution_manager=distribution_manager,
            memory_bank=memory_bank
        )
        await execution_manager.initialize()
        await asyncio.sleep(INIT_WAIT)
        
        # Initialize gas optimizer
        gas_optimizer = await create_gas_optimizer(
            dex_manager=None,  # Not needed for dashboard
            web3_manager=web3_manager
        )
        logger.info("Initializing gas optimizer...")
        await gas_optimizer.initialize()
        await asyncio.sleep(INIT_WAIT)

        # Routes
        @aiohttp_jinja2.template('index.html')
        async def index(request):
            """Render dashboard index page."""
            return {}

        @aiohttp_jinja2.template('metrics.html')
        async def metrics(request):
            """Render metrics dashboard page."""
            return {}

        @aiohttp_jinja2.template('opportunities.html')
        async def opportunities(request):
            """Render opportunities page."""
            return {}

        @aiohttp_jinja2.template('history.html')
        async def history(request):
            """Render history page."""
            return {}

        @aiohttp_jinja2.template('analytics.html')
        async def analytics(request):
            """Render analytics page."""
            return {}

        @aiohttp_jinja2.template('memory.html')
        async def memory(request):
            """Render memory page."""
            return {}

        @aiohttp_jinja2.template('storage.html')
        async def storage(request):
            """Render storage page."""
            return {}

        @aiohttp_jinja2.template('distribution.html')
        async def distribution(request):
            """Render distribution page."""
            return {}

        @aiohttp_jinja2.template('execution.html')
        async def execution(request):
            """Render execution page."""
            return {}

        @aiohttp_jinja2.template('settings.html')
        async def settings(request):
            """Render settings page."""
            return {}

        # Add routes
        app.router.add_get('/', index)
        app.router.add_get('/metrics', metrics)
        app.router.add_get('/opportunities', opportunities)
        app.router.add_get('/history', history)
        app.router.add_get('/analytics', analytics)
        app.router.add_get('/memory', memory)
        app.router.add_get('/storage', storage)
        app.router.add_get('/distribution', distribution)
        app.router.add_get('/execution', execution)
        app.router.add_get('/settings', settings)

        # Initialize WebSocket server
        ws_server = WebSocketServer(
            app=app,
            market_analyzer=market_analyzer,
            portfolio_tracker=portfolio_tracker,
            memory_bank=memory_bank,
            storage_hub=storage_hub,
            distribution_manager=distribution_manager,
            execution_manager=execution_manager,
            gas_optimizer=gas_optimizer
        )
        await ws_server.initialize()
        await asyncio.sleep(INIT_WAIT)

        # Start WebSocket server
        await ws_server.start()
        logger.info("WebSocket server started")

        return app, ws_server

    except Exception as e:
        logger.error("Failed to create application: %s", str(e))
        raise
