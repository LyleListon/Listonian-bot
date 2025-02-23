"""Flask application for arbitrage bot dashboard."""

# Import eventlet patch first to ensure monkey patching is done before any other imports
import asyncio
from ..utils.eventlet_patch import manager as eventlet_manager, init

import os
import json
import logging
import time
from datetime import datetime
from typing import Any, Optional, Tuple
from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
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
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

INIT_WAIT = 2  # Wait 2 seconds between component initializations

async def create_app(memory_bank=None, storage_hub=None) -> Tuple[Flask, SocketIO]:
    """Create Flask application."""
    try:
        # Initialize eventlet synchronously
        try:
            eventlet = eventlet_manager.eventlet or init()
        except Exception as e:
            logger.error("Failed to initialize eventlet: " + str(e))
            raise
        
        # Initialize Flask app with absolute paths
        dashboard_dir = os.path.dirname(os.path.abspath(__file__))
        app = Flask(__name__, 
            template_folder=os.path.join(dashboard_dir, 'templates'),
            static_folder=os.path.join(dashboard_dir, 'static'),
            static_url_path='/static'
        )
        app.config['SECRET_KEY'] = os.urandom(24)
        
        # Configure CORS
        CORS(app, resources={
            r"/*": {"origins": "*"},
            r"/socket.io/*": {"origins": "*"}
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
        eventlet.sleep(INIT_WAIT)

        # Use provided memory_bank or create new one
        if memory_bank is None:
            memory_bank = create_memory_bank()
        eventlet.sleep(INIT_WAIT)

        # Use provided storage_hub or create new one
        if storage_hub is None:
            storage_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'storage')
            os.makedirs(storage_path, exist_ok=True)
            storage_hub = create_storage_hub(base_path=storage_path, memory_bank=memory_bank)
        eventlet.sleep(INIT_WAIT)

        market_analyzer = create_memory_market_analyzer(web3_manager, config)
        eventlet.sleep(INIT_WAIT)

        portfolio_tracker = create_portfolio_tracker(
            web3_manager=web3_manager,
            wallet_address=web3_manager.wallet_address,
            config=config
        )
        eventlet.sleep(INIT_WAIT)

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
            storage_hub=storage_hub  # Pass the storage_hub here
        )
        distribution_manager.initialize()
        eventlet.sleep(INIT_WAIT)
        
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
        execution_manager.initialize()
        eventlet.sleep(INIT_WAIT)
        
        # Initialize gas optimizer
        gas_optimizer = await create_gas_optimizer(
            dex_manager=None,  # Not needed for dashboard
            web3_manager=web3_manager
        )
        logger.info("Initializing gas optimizer...")
        await gas_optimizer.initialize()
        eventlet.sleep(INIT_WAIT)

        # Initialize SocketIO with eventlet
        socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            async_mode='aiohttp',  # Use aiohttp instead of eventlet
            ping_timeout=60,
            ping_interval=25,
            max_http_buffer_size=1000000,
            transport=['websocket', 'polling'],
            path='/socket.io/'
        )

        # Routes
        @app.route('/')
        def index():
            """Render dashboard index page."""
            return render_template('index.html')

        @app.route('/static/<path:path>')
        def send_static(path):
            """Serve static files."""
            return send_from_directory(os.path.join(dashboard_dir, 'static'), path)

        @app.route('/metrics')
        def metrics():
            """Render metrics dashboard page."""
            return render_template('metrics.html')

        @app.route('/opportunities')
        def opportunities():
            """Render opportunities page."""
            return render_template('opportunities.html')

        @app.route('/history')
        def history():
            """Render history page."""
            return render_template('history.html')

        @app.route('/analytics')
        def analytics():
            """Render analytics page."""
            return render_template('analytics.html')

        @app.route('/memory')
        def memory():
            """Render memory page."""
            return render_template('memory.html')

        @app.route('/storage')
        def storage():
            """Render storage page."""
            return render_template('storage.html')

        @app.route('/distribution')
        def distribution():
            """Render distribution page."""
            return render_template('distribution.html')

        @app.route('/execution')
        def execution():
            """Render execution page."""
            return render_template('execution.html')

        @app.route('/settings')
        def settings():
            """Render settings page."""
            return render_template('settings.html')

        # Initialize WebSocket server
        ws_server = WebSocketServer(
            socketio=socketio,
            market_analyzer=market_analyzer,
            portfolio_tracker=portfolio_tracker,
            memory_bank=memory_bank,
            storage_hub=storage_hub,
            distribution_manager=distribution_manager,
            execution_manager=execution_manager,
            gas_optimizer=gas_optimizer
        )
        ws_server.initialize()
        eventlet.sleep(INIT_WAIT)

        # Start WebSocket server
        ws_server.start()
        logger.info("WebSocket server started")

        return app, socketio

    except Exception as e:
        logger.error("Failed to create application: " + str(e))
        raise
