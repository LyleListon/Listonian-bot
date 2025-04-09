#!/usr/bin/env python3
"""
Bot Data Bridge

This script acts as a bridge between the arbitrage bot and the dashboard.
It collects data from the bot's memory bank and exposes it via a simple API.
"""

import os
import sys
import json
import time
import logging
import random
import threading
from pathlib import Path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot_data_bridge")

# Memory bank paths
MEMORY_BANK_PATH = Path("memory-bank")
TRADES_PATH = MEMORY_BANK_PATH / "trades"
METRICS_PATH = MEMORY_BANK_PATH / "metrics"
STATE_PATH = MEMORY_BANK_PATH / "state"

# API port
API_PORT = 8081

# Cache for data
data_cache = {
    "metrics": {},
    "state": {},
    "trades": {},
    "last_updated": None
}

# Lock for thread safety
cache_lock = threading.Lock()

class DataCollector:
    """Collects data from the bot's memory bank."""
    
    @staticmethod
    def ensure_directories():
        """Ensure all required directories exist."""
        for path in [MEMORY_BANK_PATH, TRADES_PATH, METRICS_PATH, STATE_PATH]:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
    
    @staticmethod
    def read_json_file(file_path):
        """Read a JSON file and return its contents."""
        try:
            if not file_path.exists():
                logger.warning(f"File not found: {file_path}")
                return {}
            
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {}
    
    @staticmethod
    def collect_metrics():
        """Collect metrics data from the memory bank."""
        metrics_file = METRICS_PATH / "metrics.json"
        return DataCollector.read_json_file(metrics_file)
    
    @staticmethod
    def collect_state():
        """Collect state data from the memory bank."""
        state_file = STATE_PATH / "state.json"
        return DataCollector.read_json_file(state_file)
    
    @staticmethod
    def collect_trades():
        """Collect trades data from the memory bank."""
        trades_file = TRADES_PATH / "recent_trades.json"
        return DataCollector.read_json_file(trades_file)
    
    @staticmethod
    def collect_all_data():
        """Collect all data from the memory bank."""
        metrics = DataCollector.collect_metrics()
        state = DataCollector.collect_state()
        trades = DataCollector.collect_trades()
        
        return {
            "metrics": metrics,
            "state": state,
            "trades": trades,
            "timestamp": datetime.now().isoformat()
        }

class DataBridgeHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the data bridge API."""
    
    def _set_headers(self, content_type="application/json"):
        """Set the response headers."""
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")  # Allow CORS
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            # API endpoints
            if self.path == "/api/data":
                # Return all data
                with cache_lock:
                    response = json.dumps(data_cache)
                
                self._set_headers()
                self.wfile.write(response.encode())
            
            elif self.path == "/api/metrics":
                # Return metrics data
                with cache_lock:
                    response = json.dumps(data_cache["metrics"])
                
                self._set_headers()
                self.wfile.write(response.encode())
            
            elif self.path == "/api/state":
                # Return state data
                with cache_lock:
                    response = json.dumps(data_cache["state"])
                
                self._set_headers()
                self.wfile.write(response.encode())
            
            elif self.path == "/api/trades":
                # Return trades data
                with cache_lock:
                    response = json.dumps(data_cache["trades"])
                
                self._set_headers()
                self.wfile.write(response.encode())
            
            elif self.path == "/":
                # Return a simple status page
                status_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Bot Data Bridge</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        h1 {{ color: #333; }}
                        .status {{ padding: 10px; background-color: #d4edda; color: #155724; border-radius: 4px; }}
                        .endpoints {{ margin-top: 20px; }}
                        .endpoint {{ margin-bottom: 10px; }}
                        .endpoint a {{ color: #007bff; text-decoration: none; }}
                        .endpoint a:hover {{ text-decoration: underline; }}
                    </style>
                </head>
                <body>
                    <h1>Bot Data Bridge</h1>
                    <div class="status">
                        Status: Running<br>
                        Last Updated: {data_cache["last_updated"] or "Never"}
                    </div>
                    <div class="endpoints">
                        <h2>API Endpoints:</h2>
                        <div class="endpoint">
                            <a href="/api/data">/api/data</a> - All data
                        </div>
                        <div class="endpoint">
                            <a href="/api/metrics">/api/metrics</a> - Metrics data
                        </div>
                        <div class="endpoint">
                            <a href="/api/state">/api/state</a> - State data
                        </div>
                        <div class="endpoint">
                            <a href="/api/trades">/api/trades</a> - Trades data
                        </div>
                    </div>
                </body>
                </html>
                """
                
                self._set_headers("text/html")
                self.wfile.write(status_html.encode())
            
            else:
                # Return 404 for unknown paths
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
        
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

def update_cache():
    """Update the data cache with fresh data."""
    try:
        # Collect data
        data = DataCollector.collect_all_data()
        
        # Update cache
        with cache_lock:
            data_cache["metrics"] = data["metrics"]
            data_cache["state"] = data["state"]
            data_cache["trades"] = data["trades"]
            data_cache["last_updated"] = data["timestamp"]
        
        logger.debug("Data cache updated successfully")
    except Exception as e:
        logger.error(f"Error updating data cache: {e}")

def cache_updater():
    """Background thread to update the cache periodically."""
    while True:
        try:
            update_cache()
            time.sleep(5)  # Update every 5 seconds
        except Exception as e:
            logger.error(f"Error in cache updater: {e}")
            time.sleep(5)  # Wait before retrying

def main():
    """Main entry point."""
    try:
        logger.info("Starting Bot Data Bridge...")
        
        # Ensure directories exist
        DataCollector.ensure_directories()
        
        # Initial data collection
        update_cache()
        
        # Start cache updater thread
        updater_thread = threading.Thread(target=cache_updater, daemon=True)
        updater_thread.start()
        
        # Start API server
        server_address = ("", API_PORT)
        httpd = ThreadedHTTPServer(server_address, DataBridgeHandler)
        
        logger.info(f"API server running at http://localhost:{API_PORT}")
        logger.info("Press Ctrl+C to stop")
        
        # Run the server
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("Bot Data Bridge stopped by user")
    except Exception as e:
        logger.error(f"Error in Bot Data Bridge: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
