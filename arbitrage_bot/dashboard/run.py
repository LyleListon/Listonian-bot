"""
Run the dashboard application.
"""

import os
import sys
import time
import logging
import asyncio
from threading import Thread, Event
from flask import Flask
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from arbitrage_bot.dashboard.app import create_app

# Load environment variables from .env
load_dotenv('.env')

# Global flag for server status
server_ready = Event()

def run_flask(app, host, port):
    """Run Flask in a separate thread."""
    try:
        # Add more detailed logging
        logging.info(f"Starting Flask server thread on {host}:{port}")
        
        # Configure Flask server
        app.config['PROPAGATE_EXCEPTIONS'] = True  # Ensure exceptions are logged
        app.config['JSON_SORT_KEYS'] = False  # Preserve metric order
        app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True  # Pretty print JSON
        
        # Wait for components to be ready
        logging.info("Waiting for components to initialize...")
        start_time = time.time()
        while not hasattr(app, 'market_analyzer') and time.time() - start_time < 30:
            time.sleep(1)
        
        if not hasattr(app, 'market_analyzer'):
            raise RuntimeError("Market analyzer not initialized after 30 seconds")
            
        # Log component status
        components = [
            'market_analyzer', 'analytics_system', 'websocket_server',
            'portfolio_tracker', 'gas_optimizer'
        ]
        for component in components:
            if hasattr(app, component):
                logging.info(f"{component} initialized successfully")
            else:
                logging.warning(f"{component} not initialized")
        
        # Start Flask
        app.run(
            host=host,
            port=port,
            debug=False,  # Disable debug mode since we're running in a thread
            use_reloader=False,  # Disable reloader to avoid conflicts
            threaded=True  # Enable threading
        )
        
        logging.info("Flask server started successfully")
        server_ready.set()
    except Exception as e:
        logging.error(f"Flask server error: {e}")
        server_ready.set()  # Set event even on error to unblock main thread
        raise

def main():
    """Run the dashboard application."""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/dashboard.log')
            ]
        )
        
        # Log startup information
        logging.info("Starting dashboard application")
        logging.info(f"Python version: {sys.version}")
        logging.info(f"Current directory: {os.getcwd()}")
        
        # Create Flask app
        app = create_app()
        
        # Get host and port from environment or use defaults
        host = os.getenv('DASHBOARD_HOST', '0.0.0.0')
        port = int(os.getenv('DASHBOARD_PORT', '5000'))
        
        # Start Flask in a separate thread
        logging.info(f"Starting Flask server on {host}:{port}")
        flask_thread = Thread(target=run_flask, args=(app, host, port))
        flask_thread.daemon = True
        flask_thread.start()
        
        # Keep the main thread running
        try:
            while True:
                time.sleep(1)
                if not flask_thread.is_alive():
                    logging.error("Flask server thread died unexpectedly")
                    sys.exit(1)
        except KeyboardInterrupt:
            logging.info("Shutting down dashboard...")
            sys.exit(0)
            
    except Exception as e:
        logging.error(f"Failed to start dashboard: {e}")
        raise

if __name__ == '__main__':
    main()
