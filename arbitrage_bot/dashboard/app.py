"""Quart application for the arbitrage bot dashboard."""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from quart import Quart, render_template
from quart_cors import cors
from decimal import Decimal
from datetime import datetime
from ..core.web3.web3_manager import Web3Manager, create_web3_manager
from ..core.analysis.market_analyzer import (
    MarketCondition,
    MarketTrend,
    create_market_analyzer,
)
from ..core.execution.arbitrage_executor import create_arbitrage_executor
from ..core.metrics.portfolio_tracker import create_portfolio_tracker
from ..core.analytics.analytics_system import create_analytics_system
from ..core.alerts.alert_system import create_alert_system
from ..core.ml.ml_system import create_ml_system, MLSystem
from ..core.monitoring.transaction_monitor import create_transaction_monitor
from ..core.gas.gas_optimizer import create_gas_optimizer
from ..core.dex.dex_manager import create_dex_manager, DEXManager
from ..core.backtesting.backtesting import create_backtesting_system
from ..core.backtesting.monte_carlo import create_monte_carlo_system
from ..core.benchmarking.benchmarking import create_benchmarking_system
from ..core.reporting.reporting import create_reporting_system
from ..core.reporting.scheduling import create_scheduling_system
from ..core.reporting.templates import create_template_system
from ..core.reporting.delivery import create_delivery_system
from ..core.integration.integration import create_integration_system
from .websocket_server import create_websocket_server
from ..utils.config_loader import load_config

# Configure logging
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Quart application."""
    app = Quart(__name__, static_folder='static', static_url_path='/static')
    app = cors(app, allow_origin="*", allow_headers=["*"], allow_methods=["*"])
    
    # Enable debug mode for development
    app.debug = True
    
    # Configure logging with more detailed format
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)8s] %(name)s: %(message)s (%(filename)s:%(lineno)d)'
    )
    logger.setLevel(logging.INFO)

    # Track initialization state
    app.startup_complete = asyncio.Event()
    app.shutdown_complete = asyncio.Event()
    
    @app.before_serving
    async def on_startup():
        """Handle ASGI lifespan startup event."""
        logger.info("ASGI lifespan startup event received")
        try:
            await initialize_components()
            app.startup_complete.set()
            logger.info("ASGI lifespan startup completed successfully")
        except Exception as e:
            logger.error(f"ASGI lifespan startup failed: {e}", exc_info=True)
            app.startup_complete.set()  # Set even on failure to prevent hanging
            raise

    async def cleanup_resources():
        """Clean up any remaining resources."""
        try:
            # Close any remaining event loops
            loop = asyncio.get_running_loop()
            pending = asyncio.all_tasks(loop)
            for task in pending:
                if not task.done() and not task.cancelled():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            logger.info("Cleaned up pending tasks")

            # Close any client sessions
            for component in app.components.values():
                if hasattr(component, '_session'):
                    await component._session.close()
                if hasattr(component, '_connector'):
                    await component._connector.close()
        except Exception as e:
            logger.error(f"Error cleaning up resources: {e}")

    @app.after_serving
    async def on_shutdown():
        """Handle ASGI lifespan shutdown event."""
        logger.info("ASGI lifespan shutdown event received")
        try:
            await cleanup_components()
            await cleanup_resources()
            app.shutdown_complete.set()
            logger.info("ASGI lifespan shutdown completed successfully")
        except Exception as e:
            logger.error(f"ASGI lifespan shutdown failed: {e}", exc_info=True)
            app.shutdown_complete.set()
            raise

    async def initialize_components():
        """Initialize all application components with proper error handling."""
        logger.info("Starting component initialization")
        
        try:
            # Load configuration
            config = load_config()
            logger.info("Configuration loaded successfully")
            
            # Initialize core components first
            logger.info("Initializing core components")
            web3_manager = await create_web3_manager()
            await web3_manager.connect()
            app.components['web3_manager'] = web3_manager
            logger.info("Web3 manager initialized successfully")
            
            # Initialize market analyzer with timeout
            logger.info("Initializing market analyzer")
            market_analyzer = await asyncio.wait_for(
                initialize_component(
                    'market_analyzer',
                    create_market_analyzer,
                    web3_manager=web3_manager,
                    config=config
                ),
                timeout=30
            )
            app.components['market_analyzer'] = market_analyzer
            logger.info("Market analyzer initialized successfully")
            
            # Start monitoring in background
            logger.info("Starting market monitoring")
            app.monitoring_task = asyncio.create_task(market_analyzer.start_monitoring())
            
            # Initialize remaining components in parallel
            logger.info("Initializing remaining components")
            components = await asyncio.gather(
                initialize_component(
                    'executor',
                    create_arbitrage_executor,
                    web3_manager=web3_manager,
                    market_analyzer=market_analyzer
                ),
                initialize_component(
                    'ml_system',
                    create_ml_system,
                    analytics=None,
                    market_analyzer=market_analyzer,
                    config=config
                ),
                initialize_component(
                    'dex_manager',
                    create_dex_manager,
                    web3_manager=web3_manager,
                    configs=config.get('dexes', {})
                ),
                return_exceptions=True
            )
            
            # Check for any initialization errors
            for i, result in enumerate(['executor', 'ml_system', 'dex_manager']):
                if isinstance(components[i], Exception):
                    logger.error(f"Failed to initialize {result}: {components[i]}")
                    raise components[i]
                logger.info(f"{result} initialized successfully")
            
            # Initialize WebSocket server last
            logger.info("Initializing WebSocket server")
            websocket_server = await initialize_component(
                'websocket_server',
                create_websocket_server,
                analytics_system=market_analyzer,
                alert_system=None,
                metrics_manager=market_analyzer,
                host="0.0.0.0",
                port=int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
            )
            
            if websocket_server and websocket_server.is_running():
                app.config['WEBSOCKET_PORT'] = websocket_server.port
                app.components['websocket_server'] = websocket_server
                logger.info(f"WebSocket server running on port {websocket_server.port}")
            else:
                raise RuntimeError("Failed to start WebSocket server")
            
            logger.info("All components initialized successfully")
            
        except asyncio.TimeoutError as e:
            logger.error("Component initialization timed out")
            raise RuntimeError("Component initialization timed out") from e
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}", exc_info=True)
            raise
    
    # Global components
    app.components = {}

    async def initialize_component(name, create_func, *args, **kwargs):
        """Initialize a single component with error handling."""
        try:
            component = await create_func(*args, **kwargs)
            if not component:
                raise ValueError(f"Failed to create {name}")
            app.components[name] = component
            logger.info(f"Initialized {name}")
            return component
        except Exception as e:
            logger.error(f"Failed to initialize {name}: {e}")
            raise

    async def cleanup_components():
        """Cleanup all components on shutdown."""
        # Cancel monitoring task if it exists
        if hasattr(app, 'monitoring_task'):
            try:
                app.monitoring_task.cancel()
                try:
                    await app.monitoring_task
                except asyncio.CancelledError:
                    pass
                logger.info("Monitoring task cancelled")
            except Exception as e:
                logger.error(f"Error cancelling monitoring task: {e}")

        # Cleanup components in reverse dependency order
        cleanup_order = [
            'websocket_server',
            'executor',
            'analytics_system',
            'alert_system',
            'market_analyzer',
            'web3_manager'
        ]

        for name in cleanup_order:
            component = app.components.get(name)
            if component:
                try:
                    if hasattr(component, 'cleanup'):
                        await component.cleanup()
                    elif hasattr(component, 'close'):
                        await component.close()
                    logger.info(f"Cleaned up {name}")
                except Exception as e:
                    logger.error(f"Error cleaning up {name}: {e}")

        # Clear components
        app.components.clear()

    async def initialize_remaining_components(web3_manager, config):
        """Initialize remaining components after core startup."""
        try:
            # Initialize market analyzer
            market_analyzer = await initialize_component(
                'market_analyzer',
                create_market_analyzer,
                web3_manager=web3_manager,
                config=config
            )
            app.components['market_analyzer'] = market_analyzer

            # Start monitoring in background
            app.monitoring_task = asyncio.create_task(
                market_analyzer.start_monitoring()
            )

            # Initialize other components in parallel
            components = await asyncio.gather(
                initialize_component(
                    'executor',
                    create_arbitrage_executor,
                    web3_manager=web3_manager,
                    market_analyzer=market_analyzer
                ),
                initialize_component(
                    'ml_system',
                    create_ml_system,
                    analytics=None,
                    market_analyzer=market_analyzer,
                    config=config
                ),
                initialize_component(
                    'dex_manager',
                    create_dex_manager,
                    web3_manager=web3_manager,
                    configs=config.get('dexes', {})
                )
            )

            executor, ml_system, dex_manager = components
            await executor.initialize()

            # Initialize WebSocket server with market analyzer
            websocket_server = await initialize_component(
                'websocket_server',
                create_websocket_server,
                analytics_system=market_analyzer,
                alert_system=None,
                metrics_manager=market_analyzer,
                host="0.0.0.0",
                port=int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
            )

            if websocket_server and websocket_server.is_running():
                app.config['WEBSOCKET_PORT'] = websocket_server.port
                app.components['websocket_server'] = websocket_server
                logger.info(f"WebSocket server running on port {websocket_server.port}")
            else:
                raise RuntimeError("Failed to start WebSocket server")

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize remaining components: {e}")
            await cleanup_components()
            raise

    @app.before_serving
    async def startup():
        """Initialize components before serving."""
        startup_complete = asyncio.Event()
        
        async def initialize_all():
            try:
                # Load configuration
                config = load_config()
                
                # Initialize core components first
                web3_manager = await create_web3_manager()
                await web3_manager.connect()
                app.components['web3_manager'] = web3_manager
                
                # Set startup complete
                startup_complete.set()
                
                # Continue with other initializations
                await initialize_remaining_components(web3_manager, config)
                
            except Exception as e:
                logger.error(f"Startup error: {e}", exc_info=True)
                if not startup_complete.is_set():
                    startup_complete.set()  # Ensure we don't hang
                raise
        
        # Start initialization in background
        init_task = asyncio.create_task(initialize_all())
        
        # Wait for core components
        try:
            await asyncio.wait_for(startup_complete.wait(), timeout=30)
            # Wait for full initialization
            await init_task
        except asyncio.TimeoutError:
            logger.error("Startup timeout waiting for core components")
            raise
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise
            
            # Initialize components in dependency order
            web3_manager = await create_web3_manager()
            await web3_manager.connect()
            app.components['web3_manager'] = web3_manager
            
            # Initialize market analyzer
            from ..core.analysis.market_analyzer import create_market_analyzer
            market_analyzer = await initialize_component(
                'market_analyzer',
                create_market_analyzer,
                web3_manager=web3_manager,
                config=config
            )
            app.components['market_analyzer'] = market_analyzer
            
            # Start monitoring with error handling
            async def monitor_with_retry():
                while True:
                    try:
                        await market_analyzer.start_monitoring()
                    except Exception as e:
                        logger.error(f"Market monitoring failed: {e}")
                        await asyncio.sleep(5)  # Wait before retrying
                        continue

            # Create but don't start the monitoring task yet
            app.monitoring_task = asyncio.create_task(monitor_with_retry())
            
            # Wait for initial monitoring setup
            try:
                await asyncio.wait_for(asyncio.shield(app.monitoring_task), timeout=30)
            except asyncio.TimeoutError:
                logger.warning("Monitoring task setup timeout, continuing with initialization")
            except Exception as e:
                logger.error(f"Error in monitoring task setup: {e}")
            
            # Wait for initial data with timeout
            timeout = 30  # seconds
            start_time = time.time()
            while not market_analyzer.market_conditions and time.time() - start_time < timeout:
                await asyncio.sleep(1)
                
            # Wait for initial market data
            if not market_analyzer.market_conditions:
                logger.warning("No initial market data, waiting for MCP updates")
                # Let the monitoring task handle data population
                pass
            
            # Initialize other components
            app.components['executor'] = await initialize_component(
                'executor',
                create_arbitrage_executor,
                web3_manager=web3_manager,
                market_analyzer=market_analyzer
            )
            await app.components['executor'].initialize()
            
            # Initialize ML system with required dependencies
            ml_system = await initialize_component(
                'ml_system',
                create_ml_system,
                analytics=None,  # Will be set after analytics system is created
                market_analyzer=market_analyzer,
                config=config
            )

            # Initialize DEX manager with configs from config
            dex_manager = await initialize_component(
                'dex_manager',
                create_dex_manager,
                web3_manager=web3_manager,
                configs=config.get('dexes', {})
            )

            # Initialize transaction monitor with required dependencies
            tx_monitor = await initialize_component(
                'tx_monitor',
                create_transaction_monitor,
                web3_manager=web3_manager,
                analytics=None,  # Will be set after analytics system is created
                ml_system=ml_system,
                dex_manager=dex_manager
            )

            # Get wallet address from config or environment
            wallet_address = os.getenv('WALLET_ADDRESS') or config.get('wallet', {}).get('wallet_address')
            if not wallet_address or wallet_address.startswith('${'):
                raise ValueError("Valid wallet address not found in config or environment")

            portfolio_tracker = await initialize_component(
                'portfolio_tracker',
                create_portfolio_tracker,
                web3_manager=web3_manager,
                wallet_address=wallet_address,
                config=config
            )

            # Get gas parameters from config
            gas_config = config.get('gas', {})
            gas_optimizer = await initialize_component(
                'gas_optimizer',
                create_gas_optimizer,
                web3_manager=web3_manager,
                dex_manager=dex_manager,
                base_gas_limit=300000,  # Default from config
                max_gas_price=int(gas_config.get('max_fee', 100) * 1e9),  # Convert to wei
                min_gas_price=int(gas_config.get('min_base_fee', 0.1) * 1e9),  # Convert to wei
                gas_price_buffer=1.1
            )
            # Initialize analytics system with all required dependencies
            analytics_system = await initialize_component(
                'analytics_system',
                create_analytics_system,
                web3_manager=web3_manager,
                tx_monitor=tx_monitor,
                market_analyzer=market_analyzer,
                portfolio_tracker=portfolio_tracker,
                gas_optimizer=gas_optimizer,
                config=config
            )

            # Set analytics reference in dependent components
            if tx_monitor:
                tx_monitor.analytics = analytics_system
            if ml_system:
                ml_system.analytics = analytics_system

            alert_system = await initialize_component(
                'alert_system',
                create_alert_system
            )

            # Initialize WebSocket server with port conflict handling and proper cleanup
            base_websocket_port = int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
            max_port_attempts = 10
            websocket_server = None
            
            async def try_start_websocket(port: int) -> Optional[WebSocketServer]:
                try:
                    logger.info(f"Starting WebSocket server initialization on port {port}")
                    ws_server = await initialize_component(
                        'websocket_server',
                        create_websocket_server,
                        analytics_system=analytics_system,
                        alert_system=alert_system,
                        metrics_manager=analytics_system,  # Use analytics system as metrics manager
                        host="0.0.0.0",
                        port=port
                    )
                    
                    # Wait for server to be fully running
                    start_time = time.time()
                    while time.time() - start_time < 10:  # Try for 10 seconds
                        if ws_server and ws_server.is_running():
                            logger.info(f"WebSocket server successfully running on port {port}")
                            return ws_server
                        await asyncio.sleep(0.5)
                        logger.debug(f"Waiting for WebSocket server to start on port {port}...")
                    
                    # If we get here, server didn't start properly
                    logger.error(f"WebSocket server failed to start on port {port} within timeout")
                    if ws_server:
                        await ws_server.stop()
                    return None
                    
                except Exception as e:
                    logger.warning(f"Failed to start WebSocket server on port {port}: {e}")
                    return None

            # Try ports sequentially
            for port_offset in range(max_port_attempts):
                current_port = base_websocket_port + port_offset
                logger.info(f"Attempting to start WebSocket server on port {current_port}")
                
                websocket_server = await try_start_websocket(current_port)
                if websocket_server:
                    logger.info(f"WebSocket server successfully started on port {current_port}")
                    app.config['WEBSOCKET_PORT'] = current_port
                    app.components['websocket_server'] = websocket_server
                    break
            
            if not websocket_server or not websocket_server.is_running():
                raise RuntimeError("Failed to start WebSocket server after exhausting all ports")
            
            # Add components to app context
            app.web3_manager = web3_manager
            app.market_analyzer = market_analyzer
            app.executor = app.components['executor']
            app.websocket_server = websocket_server
            
            logger.info(f"All components initialized successfully. WebSocket running on port {app.config['WEBSOCKET_PORT']}")
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            await cleanup_components()
            raise

    @app.after_serving
    async def shutdown():
        """Cleanup components after serving."""
        await cleanup_components()

    @app.context_processor
    async def inject_websocket_port():
        """Inject WebSocket port into all templates."""
        port = app.config.get('WEBSOCKET_PORT', None)
        if not port:
            logger.error("WebSocket port not found in app config")
            port = os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771')
        logger.info(f"Injecting WebSocket port: {port}")  # Changed to info for better visibility
        return {'websocket_port': port}

    @app.before_request
    async def update_websocket_port():
        """Update WebSocket port before each request."""
        if 'websocket_server' in app.components:
            app.config['WEBSOCKET_PORT'] = app.components['websocket_server'].port

    @app.route('/opportunities')
    async def opportunities():
        """Render opportunities page."""
        try:
            metrics = {}
            if hasattr(app, 'market_analyzer'):
                performance = await app.market_analyzer.get_performance_metrics()
                if performance and len(performance) > 0:
                    metrics = performance[0]
            return await render_template('opportunities.html', metrics=metrics)
        except Exception as e:
            logger.error(f"Error rendering opportunities: {e}", exc_info=True)
            return await render_template('opportunities.html', metrics={})

    @app.route('/performance')
    async def performance():
        """Render performance page."""
        try:
            metrics = {}
            if hasattr(app, 'market_analyzer'):
                performance = await app.market_analyzer.get_performance_metrics()
                if performance and len(performance) > 0:
                    metrics = performance[0]
            return await render_template('performance.html', metrics=metrics)
        except Exception as e:
            logger.error(f"Error rendering performance: {e}", exc_info=True)
            return await render_template('performance.html', metrics={})

    @app.route('/')
    async def index():
        """Render dashboard home page."""
        try:
            metrics = {
                'total_trades': 0,
                'trades_24h': 0,
                'success_rate': 0,
                'total_profit': 0.0,
                'profit_24h': 0.0,
                'active_opportunities': 0
            }
            
            if hasattr(app, 'market_analyzer'):
                performance = await app.market_analyzer.get_performance_metrics()
                if performance and len(performance) > 0:
                    latest = performance[0]
                    metrics.update({
                        'total_trades': latest['total_trades'],
                        'trades_24h': latest['trades_24h'],
                        'success_rate': latest['success_rate'],
                        'total_profit': latest['total_profit_usd'],
                        'profit_24h': latest['portfolio_change_24h'],
                        'active_opportunities': latest['active_opportunities']
                    })
                    logger.debug(f"Updated metrics: {metrics}")
            else:
                logger.warning("Market analyzer not available")
            
            return await render_template('index.html', metrics=metrics)
        except Exception as e:
            logger.error(f"Error rendering index: {e}", exc_info=True)
            return await render_template('index.html', metrics={})

    @app.route('/settings')
    async def settings():
        """Render settings page."""
        try:
            settings = {
                'min_profit_threshold': float(os.getenv('MIN_PROFIT_THRESHOLD', '0.5')),
                'max_gas_price': int(os.getenv('MAX_GAS_PRICE', '100')),
                'max_slippage': float(os.getenv('MAX_SLIPPAGE', '0.005')),
                'log_level': os.getenv('LOG_LEVEL', 'INFO'),
                'alert_email': os.getenv('ALERT_EMAIL', ''),
                'discord_webhook_url': os.getenv('DISCORD_WEBHOOK_URL', '')
            }
            return await render_template('settings.html', settings=settings)
        except Exception as e:
            logger.error(f"Error rendering settings: {e}", exc_info=True)
            return await render_template('settings.html', settings={})

    @app.route('/favicon.ico')
    async def favicon():
        """Handle favicon request."""
        return '', 204

    @app.route('/health')
    async def health():
        """Health check endpoint for WebSocket port discovery."""
        try:
            # Check if WebSocket server is running
            if not app.components.get('websocket_server') or not app.components['websocket_server'].is_running():
                return {'status': 'error', 'message': 'WebSocket server not running'}, 503

            # Get actual WebSocket port
            ws_port = app.config.get('WEBSOCKET_PORT')
            if not ws_port:
                return {'status': 'error', 'message': 'WebSocket port not configured'}, 503

            response = {
                'status': 'ok',
                'websocket_port': ws_port,
                'uptime': time.time() - app.components['websocket_server'].start_time,
                'connections': len(app.components['websocket_server'].clients)
            }

            # Add CORS headers
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Max-Age': '86400',  # 24 hours
            }

            return response, 200, headers

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {'status': 'error', 'message': str(e)}, 503, {'Access-Control-Allow-Origin': '*'}

    @app.after_request
    async def after_request(response):
        """Add CORS headers to all responses."""
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = '*'
        response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
        return response

    return app

# Create app instance for Hypercorn
app = create_app()
