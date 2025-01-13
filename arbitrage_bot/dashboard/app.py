"""Quart application for the arbitrage bot dashboard."""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from quart import Quart, render_template
from quart_cors import cors
from ..core.web3.web3_manager import Web3Manager, create_web3_manager
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
    app = cors(app, allow_origin="*")
    
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
            app.components['market_analyzer'] = await initialize_component(
                'market_analyzer',
                create_market_analyzer,
                web3_manager=web3_manager,
                config=config
            )
            
            # Wait for market data
            if not await app.components['market_analyzer'].wait_for_data(timeout=30):
                raise RuntimeError("Market analyzer failed to get initial data")
            
            # Start monitoring
            app.monitoring_task = asyncio.create_task(app.components['market_analyzer'].start_monitoring())
            
            # Initialize other components
            app.components['executor'] = await initialize_component(
                'executor',
                create_arbitrage_executor,
                web3_manager=web3_manager,
                market_analyzer=app.components['market_analyzer']
            )
            await app.components['executor'].initialize()
            
            # Initialize WebSocket server
            websocket_port = int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
            app.components['websocket_server'] = await initialize_component(
                'websocket_server',
                create_websocket_server,
                analytics_system=app.components.get('analytics_system'),
                alert_system=app.components.get('alert_system'),
                metrics_manager=app.config.get("metrics_manager"),
                host="0.0.0.0",
                port=websocket_port
            )
            
            # Add components to app context
            app.web3_manager = web3_manager
            app.market_analyzer = app.components['market_analyzer']
            app.executor = app.components['executor']
            app.websocket_server = app.components['websocket_server']
            
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
        port = os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771')
        logger.debug(f"Injecting WebSocket port: {port}")
        return {'websocket_port': port}

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
            
            if hasattr(app, 'analytics_system'):
                performance = await app.analytics_system.get_performance_metrics()
                if performance:
                    metrics.update({
                        'total_trades': len(performance),
                        'trades_24h': sum(1 for m in performance if m.timestamp > time.time() - 24*3600),
                        'success_rate': performance[-1].success_rate if performance else 0,
                        'total_profit': float(performance[-1].total_profit_usd) if performance else 0,
                        'profit_24h': float(performance[-1].portfolio_change_24h) if performance else 0
                    })
            
            return await render_template('index.html', metrics=metrics)
        except Exception as e:
            logger.error(f"Error rendering index: {e}")
            return await render_template('index.html', metrics={})

    @app.route('/favicon.ico')
    async def favicon():
        """Handle favicon request."""
        return '', 204

    return app

# Create app instance for Hypercorn
app = create_app()
