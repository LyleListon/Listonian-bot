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
from .app import create_app

# Load environment variables from .env.production
load_dotenv('.env.production')

# Global flag for server status
server_ready = Event()

def run_flask(app, host, port):
    """Run Flask in a separate thread."""
    try:
        # Add more detailed logging
        logging.info(f"Starting Flask server thread on {host}:{port}")
        
        # Configure Flask server
        app.config['PROPAGATE_EXCEPTIONS'] = True  # Ensure exceptions are logged
        
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
            format='%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)d)'
        )
        
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
