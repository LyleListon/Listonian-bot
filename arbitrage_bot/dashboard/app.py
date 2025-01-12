"""Flask application for the arbitrage bot dashboard."""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from flask import Flask, render_template, g, send_from_directory
from werkzeug.serving import is_running_from_reloader
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

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Global components
components = {}

async def initialize_component(name, create_func, *args, **kwargs):
    """Initialize a single component with error handling."""
    try:
        component = await create_func(*args, **kwargs)
        if not component:
            raise ValueError(f"Failed to create {name}")
        components[name] = component
        logger.info(f"Initialized {name}")
        return component
    except Exception as e:
        logger.error(f"Failed to initialize {name}: {e}")
        raise

import threading
import signal
import psutil

# Global lock for thread-safe cleanup
_cleanup_lock = threading.Lock()
_cleanup_done = False

async def cleanup_components():
    """Cleanup all components on shutdown."""
    global _cleanup_done
    
    # Use lock to ensure thread-safe cleanup
    with _cleanup_lock:
        if _cleanup_done:
            return
            
        # Monitor resources before cleanup
        process = psutil.Process()
        before_cleanup = {
            'memory': process.memory_info().rss,
            'threads': process.num_threads(),
            'files': len(process.open_files()),
            'connections': len(process.connections())
        }
        
        logger.info(f"Resource usage before cleanup: {before_cleanup}")
        
        # Perform cleanup
        for name, component in components.items():
            if component and name not in ['template_system', 'delivery_system', 'integration_system']:
                try:
                    if hasattr(component, 'cleanup'):
                        await component.cleanup()
                    elif hasattr(component, 'close'):
                        await component.close()
                    logger.info(f"Cleaned up {name}")
                except Exception as e:
                    logger.error(f"Error cleaning up {name}: {e}")
                    
        # Monitor resources after cleanup
        after_cleanup = {
            'memory': process.memory_info().rss,
            'threads': process.num_threads(),
            'files': len(process.open_files()),
            'connections': len(process.connections())
        }
        
        logger.info(f"Resource usage after cleanup: {after_cleanup}")
        
        # Log resource changes
        for key in before_cleanup:
            diff = after_cleanup[key] - before_cleanup[key]
            if diff != 0:
                logger.info(f"{key} change during cleanup: {diff}")
                
        _cleanup_done = True

async def initialize_components():
    """Initialize dashboard components."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize components in dependency order
        # Initialize and connect web3_manager
        web3_manager = await create_web3_manager()
        if not isinstance(web3_manager, Web3Manager):
            raise ValueError(f"Expected Web3Manager instance, got {type(web3_manager)}")
        await web3_manager.connect()
        components['web3_manager'] = web3_manager
        logger.info(f"Initialized web3_manager of type {type(web3_manager)}")
        
        # Create executor with connected web3_manager
        components['executor'] = await initialize_component(
            'executor',
            create_arbitrage_executor,
            web3_manager=components['web3_manager']
        )
        await components['executor'].initialize()
        
        # Wait for market analyzer to initialize
        market_analyzer = components['executor'].market_analyzer
        if not hasattr(market_analyzer, '_monitoring_started'):
            logger.info("Starting market analyzer monitoring...")
            await market_analyzer.start_monitoring()
            market_analyzer._monitoring_started = True
        
        # Wait for initial market data with progress logging
        start_time = time.time()
        dots = 0
        while not market_analyzer.market_conditions and time.time() - start_time < 30:
            dots = (dots + 1) % 4
            logger.info(f"Waiting for market data{'.' * dots}")
            await asyncio.sleep(1)
            
            # Try to force an update
            try:
                await market_analyzer._update_market_conditions()
            except Exception as e:
                logger.warning(f"Error during market update: {e}")
        
        if not market_analyzer.market_conditions:
            logger.warning("Market analyzer initialized but no data available yet")
        else:
            logger.info("Market analyzer initialized with data")
            logger.info(f"Initial market conditions: {market_analyzer.market_conditions}")
        
        components['portfolio_tracker'] = await initialize_component(
            'portfolio_tracker',
            create_portfolio_tracker,
            components['web3_manager'],
            components['executor'].wallet_address,
            config
        )
        
        components['analytics_system'] = await initialize_component(
            'analytics_system',
            create_analytics_system,
            components['web3_manager'],
            components['executor'].tx_monitor,
            components['executor'].market_analyzer,
            components['portfolio_tracker'],
            components['executor'].gas_optimizer,
            config
        )
        
        components['alert_system'] = await initialize_component(
            'alert_system',
            create_alert_system,
            components['analytics_system'],
            components['executor'].tx_monitor,
            components['executor'].market_analyzer,
            config
        )
        
        components['ml_system'] = await initialize_component(
            'ml_system',
            create_ml_system,
            components['analytics_system'],
            components['executor'].market_analyzer,
            config
        )
        
        components['backtesting_system'] = await initialize_component(
            'backtesting_system',
            create_backtesting_system,
            components['analytics_system'],
            components['executor'].market_analyzer,
            components['ml_system'],
            config
        )
        
        components['monte_carlo_system'] = await initialize_component(
            'monte_carlo_system',
            create_monte_carlo_system,
            components['analytics_system'],
            components['executor'].market_analyzer,
            components['ml_system'],
            config
        )
        
        components['benchmarking_system'] = await initialize_component(
            'benchmarking_system',
            create_benchmarking_system,
            components['analytics_system'],
            components['executor'].market_analyzer,
            components['ml_system'],
            config
        )
        
        components['reporting_system'] = await initialize_component(
            'reporting_system',
            create_reporting_system,
            components['analytics_system'],
            components['executor'].market_analyzer,
            components['ml_system'],
            components['benchmarking_system'],
            config
        )
        
        components['scheduling_system'] = await initialize_component(
            'scheduling_system',
            create_scheduling_system,
            components['analytics_system'],
            components['executor'].market_analyzer,
            components['ml_system'],
            components['benchmarking_system'],
            components['reporting_system'],
            config
        )
        
        # Initialize non-async systems
        components['template_system'] = create_template_system(config)
        logger.info("Initialized template_system")
        
        components['delivery_system'] = create_delivery_system(config)
        logger.info("Initialized delivery_system")
        
        components['integration_system'] = create_integration_system(config)
        logger.info("Initialized integration_system")
        
        # Initialize WebSocket server last with retry logic
        try:
            websocket_port = int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))  # Use different port from production bot
            logger.info(f"Creating WebSocket server on port {websocket_port}")
            
            components['websocket_server'] = await initialize_component(
                'websocket_server',
                create_websocket_server,
                analytics_system=components['analytics_system'],
                alert_system=components['alert_system'],
                metrics_manager=app.config.get("metrics_manager"),
                host="0.0.0.0",
                port=websocket_port
            )
            
            # Set WebSocket server reference in analytics system
            components['analytics_system'].set_websocket_server(components['websocket_server'])
            logger.info("Set WebSocket server reference in analytics system")
            
            # WebSocket server is now started in create_websocket_server
            logger.info(f"WebSocket server initialized on port {websocket_port}")
                
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket server: {e}")
            await cleanup_components()
            raise
        
        logger.info("All dashboard components initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize dashboard components: {e}")
        await cleanup_components()
        raise

# Register blueprints
from .routes.analytics import analytics_bp
from .routes.alerts import alerts_bp
from .routes.ml import ml_bp
from .routes.backtesting import backtesting_bp
from .routes.monte_carlo import monte_carlo_bp
from .routes.benchmarking import benchmarking_bp
from .routes.reporting import reporting_bp
from .routes.scheduling import scheduling_bp
from .routes.templates import templates_bp
from .routes.delivery import delivery_bp
from .routes.integration import integration_bp
from .routes.docs import docs_bp

# Register all blueprints
blueprints = [
    analytics_bp, alerts_bp, ml_bp, backtesting_bp,
    monte_carlo_bp, benchmarking_bp, reporting_bp,
    scheduling_bp, templates_bp, delivery_bp,
    integration_bp, docs_bp
]

for blueprint in blueprints:
    app.register_blueprint(blueprint)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

# Routes
@app.route('/')
def index():
    """Render dashboard home page."""
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    """Handle favicon request."""
    return '', 204  # Return empty response with "No Content" status

# Define all route handlers
routes = {
    '/analytics': 'analytics.html',
    '/alerts': 'alerts.html',
    '/predictions': 'predictions.html',
    '/backtesting': 'backtesting.html',
    '/benchmarking': 'benchmarking.html',
    '/reporting': 'reporting.html',
    '/scheduling': 'scheduling.html',
    '/templates': 'templates.html',
    '/delivery': 'delivery.html',
    '/integration': 'integration.html',
    '/api': 'api.html',
    '/docs': 'docs.html',
    '/metrics': 'metrics.html',
    '/history': 'history.html',
    '/opportunities': 'opportunities.html',
    '/settings': 'settings.html'
}

# Register all routes
for route, template in routes.items():
    app.add_url_rule(
        route,
        endpoint=template.replace('.html', ''),
        view_func=lambda t=template: render_template(t)
    )

def create_app():
    """Create and configure Flask application."""
    try:
        # Ensure required directories exist
        Path("logs").mkdir(exist_ok=True)
        Path("analytics").mkdir(exist_ok=True)
        
        # Create metrics manager
        from ..core.metrics.metrics_manager import create_metrics_manager
        config = load_config()
        metrics_manager = create_metrics_manager(config)
        if not metrics_manager:
            raise ValueError("Failed to create metrics_manager")
        app.config["metrics_manager"] = metrics_manager
        logger.info("Created metrics_manager")
        
        # Initialize components in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(initialize_components())
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
        
        # Add components to app context
        app.components = components
        
        # Add individual components as app attributes
        app.web3_manager = components['web3_manager']
        app.tx_monitor = components['executor'].tx_monitor
        app.market_analyzer = components['executor'].market_analyzer
        app.portfolio_tracker = components['portfolio_tracker']
        app.gas_optimizer = components['executor'].gas_optimizer
        app.analytics_system = components['analytics_system']
        app.alert_system = components['alert_system']
        app.ml_system = components['ml_system']
        app.backtesting_system = components['backtesting_system']
        app.monte_carlo_system = components['monte_carlo_system']
        app.benchmarking_system = components['benchmarking_system']
        app.reporting_system = components['reporting_system']
        app.scheduling_system = components['scheduling_system']
        app.template_system = components['template_system']
        app.delivery_system = components['delivery_system']
        app.integration_system = components['integration_system']
        app.websocket_server = components['websocket_server']
        
        # Register cleanup handlers
        @app.teardown_appcontext
        def shutdown_cleanup(exception=None):
            if exception is not None:  # Only cleanup on error
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(cleanup_components())
                finally:
                    loop.close()

        def signal_handler(signum, frame):
            """Handle termination signals."""
            logger.info(f"Received signal {signum}")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(cleanup_components())
            finally:
                loop.close()
            sys.exit(0)

        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Register cleanup on actual app shutdown
        import atexit
        def cleanup_on_shutdown():
            if not _cleanup_done:  # Only cleanup if not already done
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(cleanup_components())
                finally:
                    loop.close()
        atexit.register(cleanup_on_shutdown)
        
        return app
        
    except Exception as e:
        logger.error(f"Failed to create Flask app: {e}")
        raise

# Export create_app function
__all__ = ['create_app']
