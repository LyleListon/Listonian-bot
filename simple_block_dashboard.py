#!/usr/bin/env python3
"""
Simple dashboard to display the current block number on Base blockchain.
"""

import json
import time
import logging
import threading
import http.server
import socketserver
from pathlib import Path
from web3 import Web3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_block_dashboard")

# Base RPC URL
BASE_RPC_URL = "https://mainnet.base.org"

# Dashboard port
DASHBOARD_PORT = 8080

# Current block number
current_block = 0
last_updated = ""

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Base Block Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            text-align: center;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        .block-number {
            font-size: 48px;
            font-weight: bold;
            margin: 20px 0;
            color: #4CAF50;
        }
        .last-updated {
            font-size: 12px;
            color: #666;
            margin-top: 20px;
        }
        .refresh-btn {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 15px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 20px;
        }
        .refresh-btn:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Current Base Block</h1>
        <div class="block-number" id="blockNumber">{block_number}</div>
        <button class="refresh-btn" onclick="refreshData()">Refresh</button>
        <div class="last-updated">Last updated: <span id="lastUpdated">{last_updated}</span></div>
    </div>

    <script>
        function refreshData() {{
            fetch(window.location.href)
                .then(response => response.text())
                .then(html => {{
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    document.getElementById('blockNumber').textContent = doc.getElementById('blockNumber').textContent;
                    document.getElementById('lastUpdated').textContent = doc.getElementById('lastUpdated').textContent;
                }})
                .catch(error => console.error('Error refreshing data:', error));
        }}

        // Auto-refresh every 10 seconds
        setInterval(refreshData, 10000);
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """Custom request handler for the dashboard."""
    
    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        # Generate HTML with current block number
        html = HTML_TEMPLATE.format(
            block_number=current_block,
            last_updated=last_updated
        )
        
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info("%s - %s", self.address_string(), format % args)

def get_current_block():
    """Get the current block number from Base blockchain."""
    try:
        # Connect to Base using Web3
        w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        
        # Check connection
        if not w3.is_connected():
            logger.error("Failed to connect to Base blockchain")
            return None
        
        # Get current block number
        block_number = w3.eth.block_number
        logger.info(f"Current Base block number: {block_number}")
        
        return block_number
    except Exception as e:
        logger.error(f"Error getting current block: {e}")
        return None

def update_block_number():
    """Update the current block number periodically."""
    global current_block, last_updated
    
    while True:
        try:
            # Get current block
            block_number = get_current_block()
            
            if block_number is not None:
                current_block = block_number
                last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"Updated block number: {current_block}")
            
            # Wait before next update
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error updating block number: {e}")
            time.sleep(10)

def main():
    """Main entry point."""
    try:
        logger.info("Starting Simple Block Dashboard...")
        
        # Initial block number update
        block_number = get_current_block()
        if block_number is not None:
            global current_block, last_updated
            current_block = block_number
            last_updated = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Start block number updater thread
        updater_thread = threading.Thread(target=update_block_number, daemon=True)
        updater_thread.start()
        
        # Start dashboard server
        server_address = ("", DASHBOARD_PORT)
        httpd = socketserver.TCPServer(server_address, DashboardHandler)
        
        logger.info(f"Dashboard server running at http://localhost:{DASHBOARD_PORT}")
        logger.info("Press Ctrl+C to stop")
        
        # Run the server
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("Dashboard stopped by user")
    except Exception as e:
        logger.error(f"Error in dashboard: {e}")

if __name__ == "__main__":
    main()
