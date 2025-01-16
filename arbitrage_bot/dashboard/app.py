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
from ..core.analysis.market_analyzer import MarketCondition, MarketTrend
from ..core.execution.arbitrage_executor import create_arbitrage_executor
from ..core.metrics.portfolio_tracker import create_portfolio_tracker
from ..core.analytics.analytics_system import create_analytics_system
from ..core.alerts.alert_system import create_alert_system
from ..core.ml.ml_system import create_ml_system
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
        for name, component in app.components.items():
            if component and name not in ['template_system', 'delivery_system', 'integration_system']:
                try:
                    if hasattr(component, 'cleanup'):
                        await component.cleanup()
                    elif hasattr(component, 'close'):
                        await component.close()
                    logger.info(f"Cleaned up {name}")
                except Exception as e:
                    logger.error(f"Error cleaning up {name}: {e}")

    @app.before_serving
    async def startup():
        """Initialize components before serving."""
        try:
            # Load configuration
            config = load_config()
            
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
            
            # Start monitoring and wait for initial data
            app.monitoring_task = asyncio.create_task(market_analyzer.start_monitoring())
            
            # Initialize with empty data if needed
            if not market_analyzer.market_conditions:
                logger.warning("No initial market data, initializing with default values")
                market_analyzer.market_conditions = {
                    "WETH": MarketCondition(
                        price=Decimal("1000.0"),  # Mock price
                        trend=MarketTrend(
                            direction="sideways",
                            strength=0.0,
                            duration=0.0,
                            volatility=0.1,
                            confidence=0.5
                        ),
                        volume_24h=Decimal("1000000"),
                        liquidity=Decimal("1000000"),
                        volatility_24h=0.1,
                        price_impact=0.001,
                        last_updated=float(datetime.now().timestamp())
                    )
                }
            
            # Initialize other components
            app.components['executor'] = await initialize_component(
                'executor',
                create_arbitrage_executor,
                web3_manager=web3_manager,
                market_analyzer=market_analyzer
            )
            await app.components['executor'].initialize()
            
            # Initialize WebSocket server with port conflict handling
            base_websocket_port = int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
            max_port_attempts = 10
            websocket_server = None
            
            for port_offset in range(max_port_attempts):
                try:
                    current_port = base_websocket_port + port_offset
                    logger.info(f"Attempting to start WebSocket server on port {current_port}")
                    
                    websocket_server = await initialize_component(
                        'websocket_server',
                        create_websocket_server,
                        analytics_system=market_analyzer,
                        alert_system=app.components.get('alert_system'),
                        metrics_manager=None,
                        host="0.0.0.0",
                        port=current_port
                    )
                    
                    if websocket_server and websocket_server.is_running():
                        logger.info(f"WebSocket server successfully started on port {current_port}")
                        # Store the actual port being used
                        app.config['WEBSOCKET_PORT'] = current_port
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to start WebSocket server on port {current_port}: {e}")
                    if port_offset == max_port_attempts - 1:
                        logger.error("Failed to find available port for WebSocket server")
                        raise
                    continue
            
            if not websocket_server or not websocket_server.is_running():
                raise RuntimeError("Failed to start WebSocket server")
            
            app.components['websocket_server'] = websocket_server
            
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
