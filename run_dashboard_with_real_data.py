#!/usr/bin/env python3
"""
Run the dashboard with real data from the bot API server.
This script starts both the bot API server and a simple HTTP server for the dashboard.
"""

import subprocess
import threading
import time
import logging
import os
import webbrowser
import http.server
import socketserver
from pathlib import Path
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dashboard_launcher")

# Dashboard server port
DASHBOARD_PORT = 8080
# Bot API server port
BOT_API_PORT = 8081

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for the dashboard."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)

def start_bot_api_server():
    """Start the bot API server in a separate process."""
    try:
        logger.info("Starting bot API server on port %d...", BOT_API_PORT)
        
        # Use subprocess.Popen to start the API server
        process = subprocess.Popen(
            [sys.executable, "bot_api_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Start threads to read output
        def read_output(stream, prefix):
            for line in stream:
                if prefix == "API":
                    logger.info(f"{prefix}: {line.strip()}")
                else:
                    logger.error(f"{prefix}: {line.strip()}")
        
        threading.Thread(target=read_output, args=(process.stdout, "API"), daemon=True).start()
        threading.Thread(target=read_output, args=(process.stderr, "API ERROR"), daemon=True).start()
        
        # Wait for API server to start
        logger.info("Waiting for API server to initialize...")
        time.sleep(2)
        
        return process
    except Exception as e:
        logger.error(f"Failed to start bot API server: {e}")
        return None

def start_dashboard_server():
    """Start a simple HTTP server for the dashboard."""
    try:
        logger.info("Starting dashboard server on port %d...", DASHBOARD_PORT)
        
        # Create the server
        httpd = socketserver.TCPServer(("", DASHBOARD_PORT), DashboardHandler)
        
        # Start the server in a separate thread
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        
        logger.info(f"Dashboard server running at http://localhost:{DASHBOARD_PORT}")
        
        return httpd
    except Exception as e:
        logger.error(f"Failed to start dashboard server: {e}")
        return None

def open_dashboard():
    """Open the dashboard in the default web browser."""
    try:
        dashboard_url = f"http://localhost:{DASHBOARD_PORT}/dashboard.html"
        logger.info(f"Opening dashboard in browser: {dashboard_url}")
        webbrowser.open(dashboard_url)
    except Exception as e:
        logger.error(f"Failed to open dashboard in browser: {e}")

def main():
    """Main entry point."""
    try:
        logger.info("Starting dashboard with real data...")
        
        # Get the directory containing this script
        script_dir = Path(__file__).parent.absolute()
        
        # Change to the script directory
        os.chdir(script_dir)
        
        # Check if the dashboard file exists
        dashboard_file = Path("dashboard.html")
        if not dashboard_file.exists():
            logger.error(f"Dashboard file not found: {dashboard_file}")
            return
        
        # Start bot API server
        api_process = start_bot_api_server()
        if not api_process:
            logger.error("Failed to start bot API server")
            return
        
        # Start dashboard server
        dashboard_server = start_dashboard_server()
        if not dashboard_server:
            logger.error("Failed to start dashboard server")
            api_process.terminate()
            return
        
        # Open dashboard in browser
        open_dashboard()
        
        logger.info("Both servers are running. Press Ctrl+C to stop.")
        
        # Keep the main thread running
        try:
            while True:
                # Check if API process is still running
                if api_process.poll() is not None:
                    logger.error("Bot API server has stopped unexpectedly")
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping servers...")
        finally:
            # Clean up
            if api_process:
                api_process.terminate()
            
            if dashboard_server:
                dashboard_server.shutdown()
            
            logger.info("Servers stopped")
    
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()
