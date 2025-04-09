#!/usr/bin/env python3
"""
Run Real-Time Dashboard

This script starts both the direct data bridge and serves the real-time dashboard.
"""

import os
import sys
import time
import logging
import threading
import subprocess
import http.server
import socketserver
import webbrowser
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("real_time_dashboard_runner")

# Dashboard port
DASHBOARD_PORT = 8080

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for the dashboard."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)

def start_data_bridge():
    """Start the data bridge in a separate process."""
    logger.info("Starting direct data bridge...")
    
    try:
        # Start the data bridge script
        process = subprocess.Popen(
            [sys.executable, "direct_data_bridge.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info("Direct data bridge started with PID: %d", process.pid)
        return process
    except Exception as e:
        logger.error("Error starting direct data bridge: %s", e)
        return None

def start_dashboard_server():
    """Start the dashboard server."""
    logger.info("Starting dashboard server...")
    
    try:
        # Get the directory containing this script
        script_dir = Path(__file__).parent.absolute()
        
        # Change to the script directory
        os.chdir(script_dir)
        
        # Check if the dashboard file exists
        dashboard_file = Path("real_time_dashboard.html")
        if not dashboard_file.exists():
            logger.error("Dashboard file not found: %s", dashboard_file)
            return None
        
        # Create the server
        server = socketserver.TCPServer(("", DASHBOARD_PORT), DashboardHandler)
        
        logger.info("Dashboard server running at http://localhost:%d", DASHBOARD_PORT)
        return server
    except Exception as e:
        logger.error("Error starting dashboard server: %s", e)
        return None

def run_dashboard_server(server):
    """Run the dashboard server in a separate thread."""
    try:
        server.serve_forever()
    except Exception as e:
        logger.error("Error in dashboard server: %s", e)

def main():
    """Main entry point."""
    try:
        logger.info("Starting Real-Time Dashboard System...")
        
        # Start data bridge
        bridge_process = start_data_bridge()
        if not bridge_process:
            logger.error("Failed to start direct data bridge")
            return
        
        # Wait for data bridge to initialize
        logger.info("Waiting for direct data bridge to initialize...")
        time.sleep(2)
        
        # Start dashboard server
        dashboard_server = start_dashboard_server()
        if not dashboard_server:
            logger.error("Failed to start dashboard server")
            if bridge_process:
                bridge_process.terminate()
            return
        
        # Start dashboard server in a separate thread
        server_thread = threading.Thread(target=run_dashboard_server, args=(dashboard_server,))
        server_thread.daemon = True
        server_thread.start()
        
        # Open dashboard in browser
        dashboard_url = f"http://localhost:{DASHBOARD_PORT}/real_time_dashboard.html"
        logger.info("Opening dashboard in browser: %s", dashboard_url)
        webbrowser.open(dashboard_url)
        
        # Keep the main thread running
        logger.info("Press Ctrl+C to stop the system")
        while True:
            time.sleep(1)
            
            # Check if data bridge is still running
            if bridge_process.poll() is not None:
                logger.error("Direct data bridge process has terminated")
                break
    
    except KeyboardInterrupt:
        logger.info("System stopped by user")
    except Exception as e:
        logger.error("Error in Real-Time Dashboard System: %s", e)
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        
        # Stop data bridge if running
        if 'bridge_process' in locals() and bridge_process:
            logger.info("Terminating direct data bridge process...")
            bridge_process.terminate()
        
        # Stop dashboard server if running
        if 'dashboard_server' in locals() and dashboard_server:
            logger.info("Shutting down dashboard server...")
            dashboard_server.shutdown()
        
        logger.info("Cleanup complete")

if __name__ == "__main__":
    main()
