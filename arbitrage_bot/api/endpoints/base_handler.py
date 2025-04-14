"""Base handler for API endpoints."""

import json
import logging
import traceback
from typing import Dict, List, Any, Optional, Type, Callable, Union

from arbitrage_bot.api.models.base_model import BaseModel
from arbitrage_bot.api.models.response import APIResponse

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base class for API endpoint handlers."""
    
    def __init__(self, bot):
        """Initialize the handler.
        
        Args:
            bot: The arbitrage bot instance.
        """
        self.bot = bot
    
    def handle_request(
        self,
        request_data: Dict[str, Any],
        request_model: Optional[Type[BaseModel]] = None,
        handler_func: Optional[Callable] = None,
    ) -> APIResponse:
        """Handle an API request.
        
        Args:
            request_data: The request data.
            request_model: The request model class.
            handler_func: The handler function.
            
        Returns:
            API response.
        """
        try:
            # Parse request data
            request = None
            if request_model and request_data:
                request = request_model.from_dict(request_data)
            
            # Call handler function
            if handler_func:
                if request:
                    result = handler_func(request)
                else:
                    result = handler_func()
                
                return APIResponse(success=True, data=result)
            
            # No handler function
            return APIResponse(
                success=False, error="No handler function provided"
            )
        
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            logger.debug(traceback.format_exc())
            
            return APIResponse(
                success=False, error=f"Error: {str(e)}"
            )
    
    def parse_request_data(
        self, request_body: Union[str, bytes, None]
    ) -> Dict[str, Any]:
        """Parse request body.
        
        Args:
            request_body: The request body.
            
        Returns:
            Parsed request data.
        """
        if not request_body:
            return {}
        
        try:
            if isinstance(request_body, bytes):
                request_body = request_body.decode("utf-8")
            
            return json.loads(request_body)
        except Exception as e:
            logger.error(f"Error parsing request body: {e}")
            return {}
