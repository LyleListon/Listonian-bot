#!/usr/bin/env python3
"""
Simple HTTP server to serve the standalone dashboard.
"""

import http.server
import socketserver
import webbrowser
import os
import logging
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("standalone_dashboard")

# Port for the server
PORT = 8080

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for the dashboard."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)

def main():
    """Main entry point."""
    # Get the directory containing this script
    script_dir = Path(__file__).parent.absolute()
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Check if the dashboard file exists
    dashboard_file = Path("standalone_dashboard.html")
    if not dashboard_file.exists():
        logger.error(f"Dashboard file not found: {dashboard_file}")
        return
    
    # Create the server
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        logger.info(f"Serving dashboard at http://localhost:{PORT}")
        
        # Open the dashboard in the default browser
        dashboard_url = f"http://localhost:{PORT}/standalone_dashboard.html"
        logger.info(f"Opening dashboard in browser: {dashboard_url}")
        webbrowser.open(dashboard_url)
        
        # Serve until interrupted
        try:
            logger.info("Press Ctrl+C to stop the server")
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")

if __name__ == "__main__":
    main()
