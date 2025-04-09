#!/usr/bin/env python3
"""
Robust Bot API Server
Serves bot data from memory-bank with improved error handling and stability.
"""

import http.server
import socketserver
import json
import os
import glob
import logging
import time
import threading
import signal
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("bot_api_server")

# Server configuration
HOST = "localhost"
PORT = 8081
MEMORY_BANK_DIR = "memory-bank"

# Ensure memory-bank directory exists
os.makedirs(os.path.join(MEMORY_BANK_DIR, "trades"), exist_ok=True)
os.makedirs(os.path.join(MEMORY_BANK_DIR, "metrics"), exist_ok=True)
os.makedirs(os.path.join(MEMORY_BANK_DIR, "state"), exist_ok=True)

class BotAPIHandler(http.server.BaseHTTPRequestHandler):
    """Handler for bot API requests."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)
    
    def send_cors_headers(self):
        """Send CORS headers to allow cross-origin requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
    
    def send_json_response(self, data, status=200):
        """Send a JSON response with the given data and status code."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def send_error_response(self, message, status=500):
        """Send an error response with the given message and status code."""
        self.send_json_response({"error": message}, status)
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            # Parse the path
            path = self.path.strip("/")
            parts = path.split("/")
            
            # Handle different API endpoints
            if path == "api/trades":
                self.handle_trades()
            elif path == "api/metrics":
                self.handle_metrics()
            elif path == "api/state":
                self.handle_state()
            elif path == "api/health":
                self.handle_health()
            elif path == "":
                # Root path - show API info
                self.send_json_response({
                    "name": "Bot API Server",
                    "version": "1.0.0",
                    "endpoints": [
                        "/api/trades",
                        "/api/metrics",
                        "/api/state",
                        "/api/health"
                    ],
                    "status": "running",
                    "time": datetime.now().isoformat()
                })
            else:
                self.send_error_response(f"Unknown endpoint: {path}", 404)
        
        except Exception as e:
            logger.error(f"Error handling request: {e}", exc_info=True)
            self.send_error_response(f"Server error: {str(e)}")
    
    def handle_trades(self):
        """Handle /api/trades endpoint."""
        try:
            # Get all trade files
            trade_files = glob.glob(os.path.join(MEMORY_BANK_DIR, "trades", "*.json"))
            
            # If no trade files found, create a sample trade
            if not trade_files:
                logger.warning("No trade files found, creating sample trade")
                self.create_sample_trade()
                trade_files = glob.glob(os.path.join(MEMORY_BANK_DIR, "trades", "*.json"))
            
            # Sort by modification time (newest first)
            trade_files.sort(key=os.path.getmtime, reverse=True)
            
            # Load trades from files (up to 50 most recent)
            trades = []
            for file_path in trade_files[:50]:
                try:
                    with open(file_path, "r") as f:
                        trade_data = json.load(f)
                        trades.append(trade_data)
                except Exception as e:
                    logger.error(f"Error loading trade file {file_path}: {e}")
            
            # Send response
            self.send_json_response(trades)
        
        except Exception as e:
            logger.error(f"Error handling trades request: {e}", exc_info=True)
            self.send_error_response(f"Error retrieving trades: {str(e)}")
    
    def handle_metrics(self):
        """Handle /api/metrics endpoint."""
        try:
            # Get all metric files
            metric_files = glob.glob(os.path.join(MEMORY_BANK_DIR, "metrics", "*.json"))
            
            # Sort by modification time (newest first)
            metric_files.sort(key=os.path.getmtime, reverse=True)
            
            # Load metrics from most recent file
            metrics = {}
            if metric_files:
                try:
                    with open(metric_files[0], "r") as f:
                        metrics = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metrics file {metric_files[0]}: {e}")
            
            # Send response
            self.send_json_response(metrics)
        
        except Exception as e:
            logger.error(f"Error handling metrics request: {e}", exc_info=True)
            self.send_error_response(f"Error retrieving metrics: {str(e)}")
    
    def handle_state(self):
        """Handle /api/state endpoint."""
        try:
            # Get all state files
            state_files = glob.glob(os.path.join(MEMORY_BANK_DIR, "state", "*.json"))
            
            # Sort by modification time (newest first)
            state_files.sort(key=os.path.getmtime, reverse=True)
            
            # Load state from most recent file
            state = {}
            if state_files:
                try:
                    with open(state_files[0], "r") as f:
                        state = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading state file {state_files[0]}: {e}")
            
            # Send response
            self.send_json_response(state)
        
        except Exception as e:
            logger.error(f"Error handling state request: {e}", exc_info=True)
            self.send_error_response(f"Error retrieving state: {str(e)}")
    
    def handle_health(self):
        """Handle /api/health endpoint."""
        self.send_json_response({
            "status": "healthy",
            "uptime": time.time() - server_start_time,
            "memory_bank": os.path.exists(MEMORY_BANK_DIR),
            "time": datetime.now().isoformat()
        })
    
    def create_sample_trade(self):
        """Create a sample trade file for testing."""
        try:
            # Create sample trade data
            sample_trades = []
            
            # Add some sample trades
            for i in range(10):
                timestamp = datetime.now().isoformat()
                
                sample_trade = {
                    "timestamp": timestamp,
                    "opportunity": {
                        "token_pair": "WETH-USDbC",
                        "dex_1": "aerodrome",
                        "dex_2": "pancakeswap",
                        "potential_profit": 0.03 + (i * 0.005),
                        "confidence": 0.9
                    },
                    "amount": 1.5,
                    "profit": 0.025 + (i * 0.002),
                    "gas_cost": 0.005,
                    "success": True
                }
                
                sample_trades.append(sample_trade)
            
            # Save each trade to a separate file
            for i, trade in enumerate(sample_trades):
                file_path = os.path.join(MEMORY_BANK_DIR, "trades", f"sample_trade_{i}.json")
                with open(file_path, "w") as f:
                    json.dump(trade, f, indent=2)
            
            logger.info(f"Created {len(sample_trades)} sample trades")
        
        except Exception as e:
            logger.error(f"Error creating sample trade: {e}", exc_info=True)

class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threaded HTTP server to handle multiple requests."""
    allow_reuse_address = True

def signal_handler(sig, frame):
    """Handle signals to gracefully shut down the server."""
    logger.info("Shutting down server...")
    server.shutdown()
    sys.exit(0)

# Track server start time
server_start_time = time.time()

def run_server():
    """Run the API server."""
    global server
    
    try:
        logger.info(f"Starting Bot API Server on {HOST}:{PORT}")
        server = ThreadedHTTPServer((HOST, PORT), BotAPIHandler)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start server
        server.serve_forever()
    
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_server()
