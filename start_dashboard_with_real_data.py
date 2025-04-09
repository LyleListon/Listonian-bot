#!/usr/bin/env python3
"""
Start both the bot API server and dashboard server to display real data.
"""

import subprocess
import threading
import time
import logging
import os
import webbrowser
from pathlib import Path

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

def start_bot_api_server():
    """Start the bot API server in a separate process."""
    try:
        logger.info("Starting bot API server...")
        process = subprocess.Popen(
            ["python", "bot_api_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Log output from the process
        for line in process.stdout:
            logger.info(f"Bot API: {line.strip()}")
        
        # Log errors
        for line in process.stderr:
            logger.error(f"Bot API Error: {line.strip()}")
            
        return process
    except Exception as e:
        logger.error(f"Failed to start bot API server: {e}")
        return None

def start_dashboard_server():
    """Start the dashboard server."""
    try:
        logger.info("Starting dashboard server...")
        # Use the existing serve_dashboard.py script
        process = subprocess.Popen(
            ["python", "serve_dashboard.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Log output from the process
        for line in process.stdout:
            logger.info(f"Dashboard: {line.strip()}")
        
        # Log errors
        for line in process.stderr:
            logger.error(f"Dashboard Error: {line.strip()}")
            
        return process
    except Exception as e:
        logger.error(f"Failed to start dashboard server: {e}")
        return None

def main():
    """Main entry point."""
    logger.info("Starting dashboard with real data...")
    
    # Start bot API server in a separate thread
    api_thread = threading.Thread(target=start_bot_api_server)
    api_thread.daemon = True
    api_thread.start()
    
    # Wait for API server to start
    logger.info("Waiting for bot API server to start...")
    time.sleep(2)
    
    # Start dashboard server
    dashboard_process = start_dashboard_server()
    
    if dashboard_process:
        logger.info(f"Dashboard available at http://localhost:{DASHBOARD_PORT}/dashboard.html")
        
        # Wait for the dashboard server to exit
        try:
            dashboard_process.wait()
        except KeyboardInterrupt:
            logger.info("Stopping servers...")
            dashboard_process.terminate()
    
    logger.info("Dashboard launcher exiting...")

if __name__ == "__main__":
    main()
