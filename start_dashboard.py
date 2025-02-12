"""Start the arbitrage bot dashboard."""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from arbitrage_bot.dashboard.app import create_app

# Create logs directory if it doesn't exist
logs_dir = os.path.join(project_root, 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configure root logger with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout
        RotatingFileHandler(  # Also log to file
            os.path.join(logs_dir, 'dashboard.log'),
            maxBytes=10000000,
            backupCount=5
        )
    ]
)

# Set specific loggers to DEBUG
loggers = [
    'werkzeug',
    'socketio',
    'engineio',
    'websockets',
    'arbitrage_bot.core.memory',
    'arbitrage_bot.core.web3',
    'arbitrage_bot.dashboard',
    'arbitrage_bot.core.storage',
    'arbitrage_bot.core.distribution',
    'arbitrage_bot.core.execution'
]

for logger_name in loggers:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    # Ensure logger propagates to root
    logger.propagate = True

# Configure application logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def main():
    """Start dashboard application."""
    try:
        # Load config to get port
        config_path = os.path.join(os.path.dirname(__file__), 'configs', 'config.json')
        with open(config_path) as f:
            import json
            config = json.load(f)
            
        # Get port from config, environment, or default
        port = int(os.getenv('DASHBOARD_PORT', config.get('dashboard', {}).get('port', 5001)))
        
        # Create and start dashboard
        logger.info(f"Starting dashboard on port {port}...")
        app, socketio = create_app()

        # Log key configuration details
        logger.info(f"SocketIO async mode: {socketio.async_mode}")
        logger.info(f"Eventlet monkey patched: {bool(socketio.server.eio.async_mode == 'eventlet')}")
        
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=True,  # Enable debug mode
            use_reloader=False,
            log_output=True,
            allow_unsafe_werkzeug=True  # Allow Werkzeug in development
        )
        
    except Exception as e:
        logger.exception(f"Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
