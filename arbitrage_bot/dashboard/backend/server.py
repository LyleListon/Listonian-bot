"""Dashboard backend server."""

import json
import logging
import os
import threading
import time
import requests
from typing import Dict, List, Any, Optional
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class DashboardServer:
    """Server for the dashboard frontend."""

    def __init__(self, bot, config: Dict[str, Any]):
        """Initialize the dashboard server.

        Args:
            bot: The arbitrage bot instance.
            config: Configuration dictionary.
        """
        self.bot = bot
        self.config = config

        # Get dashboard configuration
        dashboard_config = config.get("dashboard", {})
        self.host = dashboard_config.get("host", "127.0.0.1")
        self.port = dashboard_config.get("port", 8080)
        self.static_dir = dashboard_config.get("static_dir", "arbitrage_bot/dashboard/frontend/static")

        # Create HTTP server
        self.server = None
        self.server_thread = None
        self.running = False

    def start(self) -> None:
        """Start the dashboard server."""
        if self.running:
            logger.warning("Dashboard server already running")
            return

        # Create request handler
        dashboard_server = self
        static_dir = os.path.abspath(self.static_dir)

        # Log static directory information
        logger.info(f"Static directory: {static_dir}")
        logger.info(f"Static directory exists: {os.path.exists(static_dir)}")
        if os.path.exists(static_dir):
            logger.info(f"Static directory contents: {os.listdir(static_dir)}")

        # Change to the static directory
        os.chdir(static_dir)
        logger.info(f"Changed working directory to: {os.getcwd()}")

        class DashboardRequestHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                # Set directory to static files
                self.directory = static_dir
                super().__init__(*args, **kwargs)

            def do_GET(self):
                """Handle GET requests."""
                # Parse URL
                url = urlparse(self.path)
                path = url.path

                # Handle API requests
                if path.startswith("/api/"):
                    # Check if path contains v1 version prefix and remove it
                    if '/v1/' in path:
                        path = path.replace('/v1/', '/')
                        logger.info(f"Removed v1 prefix from path: {path}")
                    
                    # Forward to API server
                    try:
                        # Use localhost instead of 0.0.0.0 for connection
                        api_host = dashboard_server.config.get('api', {}).get('host', '127.0.0.1')
                        if api_host == '0.0.0.0':
                            api_host = 'localhost'
                            
                        api_url = f"http://{api_host}:{dashboard_server.config.get('api', {}).get('port', 8001)}{path}"
                        logger.info(f"Forwarding request to API: {api_url}")
                        response = requests.get(api_url, timeout=5)

                        # Return API response
                        self.send_response(response.status_code)
                        for header, value in response.headers.items():
                            if header.lower() not in ['content-length', 'transfer-encoding']:
                                self.send_header(header, value)
                        self.end_headers()
                        self.wfile.write(response.content)
                    except Exception as e:
                        logger.error(f"Error forwarding to API: {e}")
                        logger.info(f"Falling back to direct handling for path: {path}")
                        self._handle_api_request(path)
                    return

                # Serve static files
                if path == "/":
                    # Serve index.html for root path
                    self.path = "/index.html"
                    logger.info(f"Serving index.html for root path")

                # Log request information
                logger.info(f"Requested path: {self.path}")
                file_path = os.path.join(static_dir, self.path.lstrip('/'))
                logger.info(f"File path: {file_path}")
                logger.info(f"File exists: {os.path.exists(file_path)}")

                try:
                    super().do_GET()
                except Exception as e:
                    logger.error(f"Error serving static file: {e}")
                    self.send_error(404, "File not found")

            def _handle_api_request(self, path: str):
                """Handle API requests.

                Args:
                    path: Request path.
                """
                # Parse path
                path_parts = path.strip("/").split("/")

                if len(path_parts) < 2:
                    self.send_error(400, "Invalid API path")
                    return

                endpoint = path_parts[1]

                try:
                    # Handle specific endpoints
                    if endpoint == "status":
                        self._send_json_response(dashboard_server._get_status())
                    elif endpoint == "metrics":
                        self._send_json_response(dashboard_server._get_metrics())
                    elif endpoint == "opportunities":
                        self._send_json_response(dashboard_server._get_opportunities())
                    elif endpoint == "trades":
                        self._send_json_response(dashboard_server._get_trades())
                    elif endpoint == "config":
                        self._send_json_response(dashboard_server._get_config())
                    else:
                        self.send_error(404, f"Unknown endpoint: {endpoint}")
                except Exception as e:
                    logger.error(f"Error handling API request: {e}")
                    self.send_error(500, str(e))

            def _send_json_response(self, data: Dict[str, Any]):
                """Send a JSON response.

                Args:
                    data: Response data.
                """
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                response_data = json.dumps(data).encode("utf-8")
                self.wfile.write(response_data)

            def log_message(self, format, *args):
                """Override log_message to use our logger."""
                logger.info(f"{self.address_string()} - {format % args}")

        # Create and start HTTP server
        self.server = HTTPServer((self.host, self.port), DashboardRequestHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        self.running = True
        logger.info(f"Dashboard server started on http://{self.host}:{self.port}")

    def stop(self) -> None:
        """Stop the dashboard server."""
        if not self.running:
            logger.warning("Dashboard server not running")
            return

        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

        if self.server_thread:
            self.server_thread.join(timeout=5.0)
            self.server_thread = None

        self.running = False
        logger.info("Dashboard server stopped")

    def _get_status(self) -> Dict[str, Any]:
        """Get system status.

        Returns:
            Status information.
        """
        # Get bot metrics
        metrics = self.bot.get_metrics()

        # Get component statuses
        components = {
            "market_monitor": "running" if self.bot.running else "stopped",
            "arbitrage_engine": "running" if self.bot.running else "stopped",
            "transaction_manager": "running" if self.bot.running else "stopped",
        }

        # Add blockchain connector statuses
        for name, connector in self.bot.blockchain_connectors.items():
            components[f"blockchain_{name}"] = "connected" if connector.is_connected() else "disconnected"

        return {
            "success": True,
            "data": {
                "status": metrics.get("status", "unknown"),
                "version": "0.1.0",  # TODO: Get from version file
                "uptime": metrics.get("uptime", 0),
                "components": components,
            },
            "timestamp": int(time.time()),
        }

    def _get_metrics(self) -> Dict[str, Any]:
        """Get system metrics.

        Returns:
            Metrics information.
        """
        # Get bot metrics
        metrics = self.bot.get_metrics()

        return {
            "success": True,
            "data": metrics,
            "timestamp": int(time.time()),
        }

    def _get_opportunities(self) -> Dict[str, Any]:
        """Get arbitrage opportunities.

        Returns:
            Opportunities information.
        """
        # Get current opportunities from arbitrage engine
        opportunities = self.bot.arbitrage_engine.current_opportunities

        return {
            "success": True,
            "data": {
                "opportunities": opportunities,
                "total_count": len(opportunities),
                "timestamp": int(time.time()),
            },
            "timestamp": int(time.time()),
        }

    def _get_trades(self) -> Dict[str, Any]:
        """Get recent trades.

        Returns:
            Trades information.
        """
        # Get recent trades from transaction manager
        trades = self.bot.transaction_manager.get_recent_trades(limit=100)

        return {
            "success": True,
            "data": {
                "trades": trades,
                "total_count": len(trades),
                "timestamp": int(time.time()),
            },
            "timestamp": int(time.time()),
        }

    def _get_config(self) -> Dict[str, Any]:
        """Get system configuration.

        Returns:
            Configuration information.
        """
        # Get configuration
        config = self.bot.config

        # Create a sanitized copy of the configuration
        # Remove sensitive information like private keys
        sanitized_config = {
            "trading": config.get("trading", {}),
            "dexes": [
                {
                    "name": dex.get("name"),
                    "network": dex.get("network"),
                    "enabled": dex.get("enabled", True),
                }
                for dex in config.get("dexes", [])
            ],
            "networks": [
                {
                    "name": network.get("name"),
                    "enabled": network.get("enabled", True),
                }
                for network in config.get("blockchain", {}).get("networks", [])
            ],
            "mev_protection": {
                "enabled": config.get("mev_protection", {}).get("enabled", True),
                "provider": config.get("mev_protection", {}).get("provider", "flashbots"),
            },
            "flash_loans": {
                "enabled": config.get("flash_loans", {}).get("enabled", True),
                "provider": config.get("flash_loans", {}).get("default_provider", "aave"),
            },
        }

        return {
            "success": True,
            "data": sanitized_config,
            "timestamp": int(time.time()),
        }
