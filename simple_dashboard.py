#!/usr/bin/env python
"""Simple dashboard server for testing."""

import argparse
import logging
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("simple_dashboard")

class DashboardHandler(SimpleHTTPRequestHandler):
    """Custom request handler for the dashboard server."""
    
    def __init__(self, *args, **kwargs):
        self.static_dir = os.path.abspath("arbitrage_bot/dashboard/frontend/static")
        super().__init__(*args, **kwargs)
    
    def translate_path(self, path):
        """Translate URL path to filesystem path."""
        # Remove query parameters
        path = path.split('?', 1)[0]
        path = path.split('#', 1)[0]
        
        # Normalize path
        path = path.strip('/')
        
        # Default to index.html for root path
        if not path:
            path = 'index.html'
        
        # Join with static directory
        return os.path.join(self.static_dir, path)
    
    def log_message(self, format, *args):
        """Log messages to our logger instead of stderr."""
        logger.info("%s - - [%s] %s" % (
            self.address_string(),
            self.log_date_time_string(),
            format % args
        ))

def run_server(host="0.0.0.0", port=8081):
    """Run the dashboard server.
    
    Args:
        host: Host to bind to.
        port: Port to bind to.
    """
    # Create server
    server = HTTPServer((host, port), DashboardHandler)
    
    # Log server information
    logger.info(f"Dashboard server started on http://{host}:{port}")
    logger.info(f"Static directory: {os.path.abspath('arbitrage_bot/dashboard/frontend/static')}")
    logger.info(f"Static directory exists: {os.path.exists(os.path.abspath('arbitrage_bot/dashboard/frontend/static'))}")
    
    try:
        # Start server
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down server")
        server.server_close()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Simple dashboard server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8081, help="Port to bind to")
    args = parser.parse_args()
    
    run_server(args.host, args.port)

if __name__ == "__main__":
    main()
