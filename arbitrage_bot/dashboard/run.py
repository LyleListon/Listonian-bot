"""
Run the dashboard application.
"""

import os
import sys
import time
import logging

logger = logging.getLogger(__name__)
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from arbitrage_bot.dashboard.app import app

# Load environment variables from .env.production
load_dotenv('.env.production')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the dashboard application')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()

async def check_port(port):
    """Check if a port is available."""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0
    except:
        return False

async def find_available_websocket_port():
    """Find an available WebSocket port."""
    base_websocket_port = int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
    max_port_attempts = 10
    
    for port_offset in range(max_port_attempts):
        current_port = base_websocket_port + port_offset
        if await check_port(current_port):
            return current_port
    
    raise RuntimeError("No available ports found in range 8771-8780")

def configure_logging(debug_mode):
    """Configure logging settings."""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)',
        handlers=[logging.StreamHandler()]
    )

def create_hypercorn_config(host, port, debug_mode):
    """Create Hypercorn configuration."""
    config = Config()
    config.bind = [f"{host}:{port}"]
    config.use_reloader = False
    config.debug = debug_mode
    config.access_log_format = '%(h)s %(r)s %(s)s %(b)s %(D)s'
    config.startup_timeout = 300
    config.graceful_timeout = 300
    config.keep_alive_timeout = 300
    config.worker_class = "asyncio"
    config.error_logger = logging.getLogger("hypercorn.error")
    config.access_logger = logging.getLogger("hypercorn.access")
    config.h11_max_incomplete_size = 16384
    config.websocket_max_message_size = 16777216
    config.websocket_ping_interval = 20
    config.websocket_ping_timeout = 20
    config.insecure_bind = [f"{host}:{port}"]
    config.lifespan = "on"
    config.backlog = 100
    config.max_requests = 1000
    config.max_requests_jitter = 50
    return config

async def main():
    """Run the dashboard application."""
    args = parse_args()
    
    try:
        # Configure logging
        configure_logging(args.debug)
        
        # Log startup information
        logging.info("Starting dashboard application")
        logging.debug(f"Python executable: {sys.executable}")
        logging.debug(f"Python version: {sys.version}")
        logging.debug(f"Current directory: {os.getcwd()}")
        
        if args.debug:
            logging.debug("Environment variables:")
            for key, value in os.environ.items():
                if key.startswith(('DASHBOARD_', 'WEB3_', 'NETWORK_')):
                    logging.debug(f"  {key}={value}")
        
        # Get host and port from environment
        host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
        port = int(os.getenv('DASHBOARD_PORT', '5000'))
        
        # Find available WebSocket port
        websocket_port = await find_available_websocket_port()
        os.environ['DASHBOARD_WEBSOCKET_PORT'] = str(websocket_port)
        logger.info(f"Selected WebSocket port: {websocket_port}")
        
        # Configure and start Hypercorn
        config = create_hypercorn_config(host, port, args.debug)
        logging.info(f"Starting Hypercorn server on {host}:{port}")
        
        # Create startup confirmation event
        startup_complete = asyncio.Event()
        
        async def on_startup():
            try:
                await asyncio.sleep(2)
                if not startup_complete.is_set():
                    startup_complete.set()
                    logging.info("Server startup completed successfully")
            except Exception as e:
                logging.error(f"Startup error: {e}")
                raise
        
        # Add startup handler and start server
        app.before_serving(on_startup)
        await serve(app, config)
        
    except Exception as e:
        logging.error(f"Failed to start dashboard: {e}", exc_info=True)
        try:
            await app.cleanup()
        except:
            pass
        raise

if __name__ == '__main__':
    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("Shutting down dashboard...")
    finally:
        loop.close()
