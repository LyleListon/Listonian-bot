"""
Brave Search API Client

This module provides an async client for interacting with the Brave Search API.
It follows the project's standards for async implementation, thread safety,
error handling, and resource management.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import ClientSession, ClientError, ClientResponseError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("brave_search_client")

class BraveSearchClient:
    """
    Async client for Brave Search API with thread safety and proper resource management.
    """
    
    # Brave Search API base URL
    BASE_URL = "https://api.search.brave.com/res/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Brave Search client.
        
        Args:
            api_key: The Brave Search API key. If not provided, it will be read from the
                     BRAVE_API_KEY environment variable.
        """
        self._api_key = api_key or os.environ.get("BRAVE_API_KEY")
        if not self._api_key:
            raise ValueError("Brave API key is required. Set it via constructor or BRAVE_API_KEY environment variable.")
        
        self._lock = asyncio.Lock()
        self._session: Optional[ClientSession] = None
        logger.info("Brave Search client initialized")
    
    async def _get_session(self) -> ClientSession:
        """
        Get or create an aiohttp session with proper resource management.
        
        Returns:
            An aiohttp ClientSession instance.
        """
        async with self._lock:
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession(
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": self._api_key
                    }
                )
            return self._session
    
    async def close(self) -> None:
        """
        Close the aiohttp session and clean up resources.
        """
        async with self._lock:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
                logger.info("Brave Search client session closed")
    
    async def web_search(self, 
                         query: str, 
                         count: int = 10, 
                         offset: int = 0) -> Dict[str, Any]:
        """
        Perform a web search using the Brave Search API.
        
        Args:
            query: The search query string.
            count: Number of results to return (1-20, default 10).
            offset: Pagination offset (max 9, default 0).
            
        Returns:
            Dictionary containing search results.
            
        Raises:
            ValueError: If parameters are invalid.
            ClientError: If there's an issue with the HTTP request.
            Exception: For other unexpected errors.
        """
        if not query:
            raise ValueError("Search query cannot be empty")
        
        if not (1 <= count <= 20):
            raise ValueError("Count must be between 1 and 20")
        
        if not (0 <= offset <= 9):
            raise ValueError("Offset must be between 0 and 9")
        
        params = {
            "q": query,
            "count": str(count),
            "offset": str(offset)
        }
        
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/web/search"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Web search successful for query: {query}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"Web search failed with status {response.status}: {error_text}")
                    response.raise_for_status()
                    
        except ClientResponseError as e:
            logger.error(f"HTTP error during web search: {str(e)}")
            raise
        except ClientError as e:
            logger.error(f"Client error during web search: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during web search: {str(e)}")
            raise
    
    async def __aenter__(self):
        """Support for async context manager."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ensure resources are cleaned up when used as context manager."""
        await self.close()