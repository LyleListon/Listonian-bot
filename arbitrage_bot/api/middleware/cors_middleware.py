"""CORS middleware for API server."""

import logging
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)


class CORSMiddleware:
    """Middleware for handling CORS."""
    
    def __init__(
        self,
        allow_origins: List[str] = None,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        allow_credentials: bool = False,
        max_age: int = 600,
    ):
        """Initialize CORS middleware.
        
        Args:
            allow_origins: List of allowed origins.
            allow_methods: List of allowed methods.
            allow_headers: List of allowed headers.
            allow_credentials: Whether to allow credentials.
            max_age: Max age for preflight requests.
        """
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["Content-Type", "Authorization"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    def process_request(self, request: Any) -> None:
        """Process a request.
        
        Args:
            request: The request object.
        """
        # Nothing to do for requests
        pass
    
    def process_response(self, request: Any, response: Any) -> None:
        """Process a response.
        
        Args:
            request: The request object.
            response: The response object.
        """
        # Add CORS headers
        origin = request.headers.get("Origin")
        
        # Check if origin is allowed
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = self.allow_origins[0]
        
        # Add other CORS headers
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
