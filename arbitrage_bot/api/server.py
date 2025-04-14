"""API server for the arbitrage bot."""

import json
import logging
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from arbitrage_bot.api.middleware.cors_middleware import CORSMiddleware
from arbitrage_bot.api.middleware.auth_middleware import AuthMiddleware
from arbitrage_bot.api.endpoints.base_handler import BaseHandler
from arbitrage_bot.api.endpoints.status_handler import StatusHandler
from arbitrage_bot.api.endpoints.opportunities_handler import OpportunitiesHandler
from arbitrage_bot.api.endpoints.trades_handler import TradesHandler
from arbitrage_bot.api.endpoints.config_handler import ConfigHandler
from arbitrage_bot.api.models.request import OpportunitiesRequest, TradesRequest, ExecuteTradeRequest
from arbitrage_bot.api.models.response import APIResponse

logger = logging.getLogger(__name__)


class APIServer:
    """API server for the arbitrage bot."""
    
    def __init__(self, bot, config: Dict[str, Any]):
        """Initialize the API server.
        
        Args:
            bot: The arbitrage bot instance.
            config: Configuration dictionary.
        """
        self.bot = bot
        self.config = config
        
        # Get API configuration
        api_config = config.get("api", {})
        self.host = api_config.get("host", "127.0.0.1")
        self.port = api_config.get("port", 8000)
        self.api_keys = api_config.get("api_keys", {})
        
        # Create middleware
        self.middleware = [
            CORSMiddleware(
                allow_origins=api_config.get("cors_origins", ["*"]),
                allow_methods=api_config.get("cors_methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
                allow_headers=api_config.get("cors_headers", ["Content-Type", "Authorization"]),
                allow_credentials=api_config.get("cors_credentials", False),
            ),
            AuthMiddleware(
                api_keys=self.api_keys,
                public_paths=api_config.get("public_paths", ["/api/v1/status"]),
            ),
        ]
        
        # Create endpoint handlers
        self.handlers = {
            "status": StatusHandler(bot),
            "opportunities": OpportunitiesHandler(bot),
            "trades": TradesHandler(bot),
            "config": ConfigHandler(bot),
        }
        
        # Create HTTP server
        self.server = None
        self.server_thread = None
        self.running = False
    
    def start(self) -> None:
        """Start the API server."""
        if self.running:
            logger.warning("API server already running")
            return
        
        # Create request handler
        api_server = self
        
        class APIRequestHandler(BaseHTTPRequestHandler):
            def do_OPTIONS(self):
                """Handle OPTIONS requests."""
                self.send_response(200)
                
                # Process middleware
                for middleware in api_server.middleware:
                    middleware.process_response(self, self)
                
                self.end_headers()
            
            def do_GET(self):
                """Handle GET requests."""
                self._handle_request("GET")
            
            def do_POST(self):
                """Handle POST requests."""
                self._handle_request("POST")
            
            def do_PUT(self):
                """Handle PUT requests."""
                self._handle_request("PUT")
            
            def do_DELETE(self):
                """Handle DELETE requests."""
                self._handle_request("DELETE")
            
            def _handle_request(self, method: str):
                """Handle a request.
                
                Args:
                    method: HTTP method.
                """
                # Parse URL
                url = urlparse(self.path)
                path = url.path
                query = parse_qs(url.query)
                
                # Process middleware for request
                for middleware in api_server.middleware:
                    error = middleware.process_request(self)
                    if error:
                        self._send_json_response(401, error)
                        return
                
                # Get request body for POST and PUT requests
                request_body = None
                if method in ["POST", "PUT"]:
                    content_length = int(self.headers.get("Content-Length", 0))
                    request_body = self.rfile.read(content_length) if content_length > 0 else None
                
                # Route request to appropriate handler
                try:
                    response = api_server._route_request(path, method, query, request_body)
                    self._send_json_response(200, response.to_dict())
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
                    error_response = APIResponse(success=False, error=str(e))
                    self._send_json_response(500, error_response.to_dict())
            
            def _send_json_response(self, status_code: int, data: Dict[str, Any]):
                """Send a JSON response.
                
                Args:
                    status_code: HTTP status code.
                    data: Response data.
                """
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json")
                
                # Process middleware for response
                for middleware in api_server.middleware:
                    middleware.process_response(self, self)
                
                self.end_headers()
                
                response_data = json.dumps(data).encode("utf-8")
                self.wfile.write(response_data)
            
            def log_message(self, format, *args):
                """Override log_message to use our logger."""
                logger.info(f"{self.address_string()} - {format % args}")
        
        # Create and start HTTP server
        self.server = HTTPServer((self.host, self.port), APIRequestHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        self.running = True
        logger.info(f"API server started on http://{self.host}:{self.port}")
    
    def stop(self) -> None:
        """Stop the API server."""
        if not self.running:
            logger.warning("API server not running")
            return
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        
        if self.server_thread:
            self.server_thread.join(timeout=5.0)
            self.server_thread = None
        
        self.running = False
        logger.info("API server stopped")
    
    def _route_request(
        self, path: str, method: str, query: Dict[str, List[str]], request_body: Optional[bytes]
    ) -> APIResponse:
        """Route a request to the appropriate handler.
        
        Args:
            path: Request path.
            method: HTTP method.
            query: Query parameters.
            request_body: Request body.
            
        Returns:
            API response.
        """
        # Parse path
        path_parts = path.strip("/").split("/")
        
        # Check API version
        if len(path_parts) < 2 or path_parts[0] != "api":
            return APIResponse(success=False, error="Invalid API path")
        
        api_version = path_parts[1]
        if api_version != "v1":
            return APIResponse(success=False, error=f"Unsupported API version: {api_version}")
        
        # Get endpoint
        if len(path_parts) < 3:
            return APIResponse(success=False, error="Missing endpoint")
        
        endpoint = path_parts[2]
        
        # Get handler
        handler = self.handlers.get(endpoint)
        if not handler:
            return APIResponse(success=False, error=f"Unknown endpoint: {endpoint}")
        
        # Parse request data
        request_data = handler.parse_request_data(request_body)
        
        # Add query parameters to request data
        for key, values in query.items():
            if len(values) == 1:
                request_data[key] = values[0]
            else:
                request_data[key] = values
        
        # Handle specific endpoints
        if endpoint == "status":
            return handler.handle_request(request_data, handler_func=handler.get_status)
        
        elif endpoint == "opportunities":
            # Check for specific opportunity ID
            if len(path_parts) > 3:
                opportunity_id = path_parts[3]
                return handler.handle_request(
                    request_data, handler_func=lambda: handler.get_opportunity(opportunity_id)
                )
            
            # List opportunities
            return handler.handle_request(
                request_data, OpportunitiesRequest, handler.get_opportunities
            )
        
        elif endpoint == "trades":
            # Check for specific trade ID
            if len(path_parts) > 3:
                trade_id = path_parts[3]
                
                # Check for execute action
                if len(path_parts) > 4 and path_parts[4] == "execute" and method == "POST":
                    return handler.handle_request(
                        request_data, ExecuteTradeRequest, handler.execute_trade
                    )
                
                # Get trade details
                return handler.handle_request(
                    request_data, handler_func=lambda: handler.get_trade(trade_id)
                )
            
            # List trades
            return handler.handle_request(
                request_data, TradesRequest, handler.get_trades
            )
        
        elif endpoint == "config":
            return handler.handle_request(request_data, handler_func=handler.get_config)
        
        # Unknown endpoint
        return APIResponse(success=False, error=f"Unknown endpoint: {endpoint}")
