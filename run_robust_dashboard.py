#!/usr/bin/env python3
"""
Run the robust dashboard system.
This script starts both the API server and a simple HTTP server for the dashboard.
"""

import subprocess
import threading
import time
import logging
import os
import webbrowser
import sys
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

def start_api_server():
    """Start the robust API server in a separate process."""
    try:
        logger.info("Starting robust API server on port %d...", BOT_API_PORT)
        
        # Use subprocess.Popen to start the API server
        process = subprocess.Popen(
            [sys.executable, "robust_bot_api_server.py"],
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
        time.sleep(5)
        
        return process
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        return None

def start_http_server():
    """Start a simple HTTP server for the dashboard."""
    try:
        logger.info("Starting HTTP server on port %d...", DASHBOARD_PORT)
        
        # Use subprocess.Popen to start the HTTP server
        process = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(DASHBOARD_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Start threads to read output
        def read_output(stream, prefix):
            for line in stream:
                if prefix == "HTTP":
                    logger.info(f"{prefix}: {line.strip()}")
                else:
                    logger.error(f"{prefix}: {line.strip()}")
        
        threading.Thread(target=read_output, args=(process.stdout, "HTTP"), daemon=True).start()
        threading.Thread(target=read_output, args=(process.stderr, "HTTP ERROR"), daemon=True).start()
        
        # Wait for HTTP server to start
        logger.info("Waiting for HTTP server to initialize...")
        time.sleep(2)
        
        return process
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}")
        return None

def open_dashboard():
    """Open the dashboard in the default web browser."""
    try:
        dashboard_url = f"http://localhost:{DASHBOARD_PORT}/robust_dashboard.html"
        logger.info(f"Opening dashboard in browser: {dashboard_url}")
        webbrowser.open(dashboard_url)
    except Exception as e:
        logger.error(f"Failed to open dashboard in browser: {e}")

def main():
    """Main entry point."""
    try:
        print("Starting Robust Bot Dashboard System")
        print("===================================")
        print("")
        
        # Get the directory containing this script
        script_dir = Path(__file__).parent.absolute()
        
        # Change to the script directory
        os.chdir(script_dir)
        
        # Check if the dashboard file exists
        dashboard_file = Path("robust_dashboard.html")
        if not dashboard_file.exists():
            logger.error(f"Dashboard file not found: {dashboard_file}")
            return
        
        # Check if the API server file exists
        api_server_file = Path("robust_bot_api_server.py")
        if not api_server_file.exists():
            logger.error(f"API server file not found: {api_server_file}")
            return
        
        # Start API server
        print("Step 1: Starting robust API server...")
        api_process = start_api_server()
        if not api_process:
            logger.error("Failed to start API server")
            return
        
        # Start HTTP server
        print("Step 2: Starting HTTP server for dashboard...")
        http_process = start_http_server()
        if not http_process:
            logger.error("Failed to start HTTP server")
            api_process.terminate()
            return
        
        # Open dashboard in browser
        print("Step 3: Opening dashboard in browser...")
        open_dashboard()
        
        print("")
        print("Dashboard system started successfully!")
        print(f"API Server: http://localhost:{BOT_API_PORT}")
        print(f"Dashboard: http://localhost:{DASHBOARD_PORT}/robust_dashboard.html")
        print("")
        print("Press Ctrl+C to stop the servers...")
        
        # Keep the main thread running
        try:
            while True:
                # Check if processes are still running
                if api_process.poll() is not None:
                    logger.error("API server has stopped unexpectedly")
                    break
                
                if http_process.poll() is not None:
                    logger.error("HTTP server has stopped unexpectedly")
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping servers...")
        finally:
            # Clean up
            if api_process:
                api_process.terminate()
            
            if http_process:
                http_process.terminate()
            
            print("Servers stopped")
    
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()
