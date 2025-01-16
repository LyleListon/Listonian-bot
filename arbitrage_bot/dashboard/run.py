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

async def main():
    """Run the dashboard application."""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Run the dashboard application')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode')
        args = parser.parse_args()

        # Configure logging based on debug flag
        log_level = logging.DEBUG if args.debug else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)',
            handlers=[
                logging.StreamHandler()
            ]
        )
        
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
        
        # Get host and port from environment or use defaults
        host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
        port = int(os.getenv('DASHBOARD_PORT', '5000'))
        
        # Set initial WebSocket port range
        base_websocket_port = int(os.getenv('DASHBOARD_WEBSOCKET_PORT', '8771'))
        max_port_attempts = 10
        
        # Function to check port availability
        async def check_port(port):
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                return result != 0
            except:
                return False

        # Find available port
        websocket_port = None
        for port_offset in range(max_port_attempts):
            current_port = base_websocket_port + port_offset
            if await check_port(current_port):
                websocket_port = current_port
                break
        
        if websocket_port is None:
            raise RuntimeError("No available ports found in range 8771-8780")
            
        os.environ['DASHBOARD_WEBSOCKET_PORT'] = str(websocket_port)
        logger.info(f"Selected WebSocket port: {websocket_port}")
        
        # Configure Hypercorn without SSL for development
        config = Config()
        config.bind = [f"{host}:{port}"]
        config.use_reloader = False
        config.debug = args.debug
        config.access_log_format = '%(h)s %(r)s %(s)s %(b)s %(D)s'
        
        # Start server
        logging.info(f"Starting Hypercorn server on {host}:{port}")
        await serve(app, config)
            
    except Exception as e:
        logging.error(f"Failed to start dashboard: {e}", exc_info=True)
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
