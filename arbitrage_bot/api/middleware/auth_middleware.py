"""Authentication middleware for API server."""

import logging
import time
import hashlib
import hmac
import base64
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware for handling authentication."""
    
    def __init__(
        self,
        api_keys: Dict[str, str] = None,
        public_paths: List[str] = None,
        header_name: str = "Authorization",
        token_prefix: str = "Bearer",
    ):
        """Initialize authentication middleware.
        
        Args:
            api_keys: Dictionary mapping API keys to user IDs.
            public_paths: List of paths that don't require authentication.
            header_name: Name of the header containing the token.
            token_prefix: Prefix for the token in the header.
        """
        self.api_keys = api_keys or {}
        self.public_paths = public_paths or ["/api/v1/status"]
        self.header_name = header_name
        self.token_prefix = token_prefix
    
    def process_request(self, request: Any) -> Optional[Dict[str, Any]]:
        """Process a request.
        
        Args:
            request: The request object.
            
        Returns:
            Error response if authentication fails, None otherwise.
        """
        # Check if authentication is enabled
        if not self.api_keys:
            # Authentication is disabled
            logger.debug("Authentication is disabled, skipping auth check")
            return None
            
        # Check if path is public
        if request.path in self.public_paths:
            return None
        
        # Get authorization header
        auth_header = request.headers.get(self.header_name)
        
        if not auth_header:
            logger.warning(f"Missing {self.header_name} header")
            return {
                "success": False,
                "error": "Authentication required",
                "timestamp": int(time.time()),
            }
        
        # Check token format
        if not auth_header.startswith(f"{self.token_prefix} "):
            logger.warning(f"Invalid {self.header_name} header format")
            return {
                "success": False,
                "error": "Invalid authentication format",
                "timestamp": int(time.time()),
            }
        
        # Extract token
        token = auth_header[len(f"{self.token_prefix} "):]
        
        # Validate token
        if token not in self.api_keys:
            logger.warning(f"Invalid API key: {token}")
            return {
                "success": False,
                "error": "Invalid API key",
                "timestamp": int(time.time()),
            }
        
        # Set user ID in request
        request.user_id = self.api_keys[token]
        
        return None
    
    def process_response(self, request: Any, response: Any) -> None:
        """Process a response.
        
        Args:
            request: The request object.
            response: The response object.
        """
        # Nothing to do for responses
        pass
