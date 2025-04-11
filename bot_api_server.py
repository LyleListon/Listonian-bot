#!/usr/bin/env python3
"""
Bot API Server

This script creates a simple API server that exposes data from the arbitrage bot.
It reads data from the memory-bank directory and serves it via HTTP endpoints.
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import json
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bot_api_server")

# Memory bank paths
MEMORY_BANK_PATH = Path("memory-bank")
TRADES_PATH = MEMORY_BANK_PATH / "trades"
METRICS_PATH = MEMORY_BANK_PATH / "metrics"
STATE_PATH = MEMORY_BANK_PATH / "state"

# API port
API_PORT = 8081

# Cache for data
data_cache = {
    "state": {},
    "metrics": {},
    "token_prices": {},
    "dex_stats": {},
    "performance": {},
    "trades": [],
    "last_updated": None
}

# Lock for thread safety
cache_lock = threading.Lock()

class DataReader:
    """Reads data from the bot's memory bank files."""

    @staticmethod
    def read_json_file(file_path):
        """Read a JSON file and return its contents."""
        try:
            if not Path(file_path).exists():
                logger.warning(f"File not found: {file_path}")
                return {}

            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return {}

    @staticmethod
    def read_state():
        """Read the bot's state data."""
        state_file = STATE_PATH / "state.json"
        return DataReader.read_json_file(state_file)

    @staticmethod
    def read_metrics():
        """Read the bot's metrics data."""
        metrics_file = METRICS_PATH / "metrics.json"
        return DataReader.read_json_file(metrics_file)

    @staticmethod
    def read_token_metrics():
        """Read token metrics data."""
        token_metrics_file = METRICS_PATH / "token_metrics.json"
        return DataReader.read_json_file(token_metrics_file)

    @staticmethod
    def read_dex_performance():
        """Read DEX performance data."""
        dex_performance_file = METRICS_PATH / "dex_performance.json"
        return DataReader.read_json_file(dex_performance_file)

    @staticmethod
    def read_performance():
        """Read performance metrics."""
        performance_file = METRICS_PATH / "performance.json"
        return DataReader.read_json_file(performance_file)

    @staticmethod
    def read_trades(limit=100):
        """Read recent trades from individual trade files."""
        trades = []

        try:
            # Get all trade files
            trade_files = list(TRADES_PATH.glob("trade_*.json"))

            if not trade_files:
                logger.warning("No trade files found in directory: %s", TRADES_PATH)
                return []

            # Sort by modification time (newest first)
            trade_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            logger.info(f"Found {len(trade_files)} trade files, reading {min(limit, len(trade_files))}")

            # Read the most recent trades
            for file_path in trade_files[:limit]:
                try:
                    trade_data = DataReader.read_json_file(file_path)
                    if trade_data:
                        trades.append(trade_data)
                except Exception as file_error:
                    logger.error(f"Error reading trade file {file_path}: {file_error}")
                    # Continue with other files
                    continue

            logger.info(f"Successfully read {len(trades)} trade files")
            return trades
        except Exception as e:
            logger.error(f"Error reading trades: {e}")
            return []

    @staticmethod
    def read_recent_trades():
        """Read recent trades from the consolidated file."""
        recent_trades_file = TRADES_PATH / "recent_trades.json"
        trades_data = DataReader.read_json_file(recent_trades_file)
        return trades_data.get("trades", [])

    @staticmethod
    def read_all_data():
        """Read all data from the bot's memory bank."""
        try:
            # Read state
            state = DataReader.read_state()

            # Read metrics
            metrics = DataReader.read_metrics()

            # Read token metrics
            token_metrics = DataReader.read_token_metrics()

            # Read DEX performance
            dex_performance = DataReader.read_dex_performance()

            # Read performance
            performance = DataReader.read_performance()

            # Read trades - try individual files first as they're more reliable
            trades = DataReader.read_trades()

            # If no trades from individual files, try the consolidated file
            if not trades:
                logger.warning("No trades found in individual files, trying consolidated file")
                trades = DataReader.read_recent_trades()

            # Combine all data
            return {
                "state": state,
                "metrics": metrics,
                "token_prices": token_metrics,
                "dex_stats": dex_performance,
                "performance": performance,
                "trades": trades,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error reading all data: {e}")
            # Return at least empty structures to prevent crashes
            return {
                "state": {},
                "metrics": {},
                "token_prices": {},
                "dex_stats": {},
                "performance": {},
                "trades": [],
                "timestamp": datetime.now().isoformat()
            }

class BotAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the bot API."""

    def _set_headers(self, content_type="application/json"):
        """Set the response headers."""
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")  # Allow CORS
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        try:
            # Parse URL path
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path

            # API endpoints
            if path == "/api/data":
                # Return all data
                with cache_lock:
                    response = json.dumps(data_cache)

                self._set_headers()
                self.wfile.write(response.encode())

            elif path == "/api/state":
                # Return state data
                with cache_lock:
                    response = json.dumps(data_cache["state"])

                self._set_headers()
                self.wfile.write(response.encode())

            elif path == "/api/metrics":
                # Return metrics data
                with cache_lock:
                    response = json.dumps(data_cache["metrics"])

                self._set_headers()
                self.wfile.write(response.encode())

            elif path == "/api/token_prices":
                # Return token prices
                with cache_lock:
                    response = json.dumps(data_cache["token_prices"])

                self._set_headers()
                self.wfile.write(response.encode())

            elif path == "/api/dex_stats":
                # Return DEX statistics
                with cache_lock:
                    response = json.dumps(data_cache["dex_stats"])

                self._set_headers()
                self.wfile.write(response.encode())

            elif path == "/api/performance":
                # Return performance metrics
                with cache_lock:
                    response = json.dumps(data_cache["performance"])

                self._set_headers()
                self.wfile.write(response.encode())

            elif path == "/api/trades":
                # Return trades data
                with cache_lock:
                    response = json.dumps(data_cache["trades"])

                self._set_headers()
                self.wfile.write(response.encode())

            elif path == "/":
                # Return a simple status page
                status_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Bot API Server</title>
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
                    <h1>Bot API Server</h1>
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
                            <a href="/api/state">/api/state</a> - Bot state
                        </div>
                        <div class="endpoint">
                            <a href="/api/metrics">/api/metrics</a> - Metrics data
                        </div>
                        <div class="endpoint">
                            <a href="/api/token_prices">/api/token_prices</a> - Token prices
                        </div>
                        <div class="endpoint">
                            <a href="/api/dex_stats">/api/dex_stats</a> - DEX statistics
                        </div>
                        <div class="endpoint">
                            <a href="/api/performance">/api/performance</a> - Performance metrics
                        </div>
                        <div class="endpoint">
                            <a href="/api/trades">/api/trades</a> - Recent trades
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
        # Read all data
        data = DataReader.read_all_data()

        # Update cache
        with cache_lock:
            data_cache["state"] = data["state"]
            data_cache["metrics"] = data["metrics"]
            data_cache["token_prices"] = data["token_prices"]
            data_cache["dex_stats"] = data["dex_stats"]
            data_cache["performance"] = data["performance"]
            data_cache["trades"] = data["trades"]
            data_cache["last_updated"] = data["timestamp"]

        logger.info(f"Data cache updated successfully with {len(data['trades'])} trades")
        return True
    except Exception as e:
        logger.error(f"Error updating data cache: {e}")
        return False

def cache_updater():
    """Background thread to update the cache periodically."""
    consecutive_failures = 0
    while True:
        try:
            success = update_cache()
            if success:
                consecutive_failures = 0
                time.sleep(2)  # Update every 2 seconds when successful
            else:
                consecutive_failures += 1
                logger.warning(f"Cache update failed, consecutive failures: {consecutive_failures}")
                time.sleep(5)  # Wait longer after a failure
        except Exception as e:
            consecutive_failures += 1
            logger.error(f"Error in cache updater: {e}, consecutive failures: {consecutive_failures}")
            time.sleep(5)  # Wait before retrying

        # If too many consecutive failures, log a critical error but keep trying
        if consecutive_failures >= 5:
            logger.critical(f"Multiple consecutive failures ({consecutive_failures}) in cache updater!")
            # But don't exit - keep trying

def main():
    """Main entry point."""
    try:
        logger.info("Starting Bot API Server...")

        # Ensure memory bank directories exist
        MEMORY_BANK_PATH.mkdir(exist_ok=True)
        TRADES_PATH.mkdir(exist_ok=True)
        METRICS_PATH.mkdir(exist_ok=True)
        STATE_PATH.mkdir(exist_ok=True)

        # Check if we have trade files
        trade_files = list(TRADES_PATH.glob("trade_*.json"))
        logger.info(f"Found {len(trade_files)} trade files in {TRADES_PATH}")

        # Initial data collection
        success = update_cache()
        if not success:
            logger.warning("Initial data collection failed, but continuing anyway")

        # Start cache updater thread
        updater_thread = threading.Thread(target=cache_updater, daemon=True)
        updater_thread.start()

        # Start API server with error handling
        server_address = ("", API_PORT)
        try:
            httpd = ThreadedHTTPServer(server_address, BotAPIHandler)
            httpd.allow_reuse_address = True  # Allow port reuse

            logger.info(f"API server running at http://localhost:{API_PORT}")
            logger.info("Press Ctrl+C to stop")

            # Run the server
            httpd.serve_forever()
        except OSError as e:
            if e.errno == 98:  # Address already in use
                logger.error(f"Port {API_PORT} is already in use. Another instance may be running.")
                logger.info("Trying to continue anyway - the existing server might be working")
                # Don't exit - let the cache updater continue running
                while True:
                    time.sleep(60)  # Just keep the process alive
            else:
                raise

    except KeyboardInterrupt:
        logger.info("Bot API Server stopped by user")
    except Exception as e:
        logger.error(f"Error in Bot API Server: {e}")
        # Don't exit immediately - give the user a chance to see the error
        logger.info("Press Ctrl+C to exit")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
