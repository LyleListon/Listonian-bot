#!/usr/bin/env python3
"""
Brave Search MCP Server Wrapper

This script is a wrapper to run the Brave Search MCP server without import issues.
It directly imports the necessary modules and runs the server.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
import traceback
import aiohttp
from aiohttp import ClientSession, ClientError, ClientResponseError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("brave_search_mcp")

# Brave Search API base URL
BASE_URL = "https://api.search.brave.com/res/v1"

# Global variables
client = None
lock = asyncio.Lock()

# MCP protocol constants
REQUEST_TYPE = "request"
RESPONSE_TYPE = "response"
ERROR_TYPE = "error"
TOOL_CALL_TYPE = "tool_call"
RESOURCE_REQUEST_TYPE = "resource_request"

class BraveSearchClient:
    """
    Async client for Brave Search API with thread safety and proper resource management.
    """
    
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
        self._session = None
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
            url = f"{BASE_URL}/web/search"
            
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

async def initialize_client() -> None:
    """
    Initialize the Brave Search client with proper resource management.
    """
    global client
    
    async with lock:
        if client is None:
            api_key = os.environ.get("BRAVE_API_KEY")
            if not api_key:
                logger.error("BRAVE_API_KEY environment variable is not set")
                raise ValueError("BRAVE_API_KEY environment variable is required")
            
            client = BraveSearchClient(api_key)
            logger.info("Brave Search client initialized")

async def cleanup() -> None:
    """
    Clean up resources before shutting down.
    """
    global client
    
    async with lock:
        if client:
            await client.close()
            client = None
            logger.info("Brave Search client closed")

async def brave_web_search(query: str, count: int = 10, offset: int = 0) -> Dict[str, Any]:
    """
    Perform a web search using the Brave Search API.
    
    Args:
        query: Search query (max 400 chars, 50 words)
        count: Number of results (1-20, default 10)
        offset: Pagination offset (max 9, default 0)
        
    Returns:
        Dictionary containing search results.
    """
    global client
    
    if not client:
        await initialize_client()
    
    try:
        result = await client.web_search(query, count, offset)
        return result
    except Exception as e:
        logger.error(f"Error in brave_web_search: {str(e)}")
        raise

def get_tool_schemas() -> Dict[str, Any]:
    """
    Define the schemas for the tools provided by this MCP server.
    
    Returns:
        Dictionary containing tool schemas.
    """
    return {
        "brave_web_search": {
            "description": "Performs a web search using the Brave Search API, ideal for general queries, news, articles, and online content. Use this for broad information gathering, recent events, or when you need diverse web sources. Supports pagination, content filtering, and freshness controls. Maximum 20 results per request, with offset for pagination.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (max 400 chars, 50 words)"
                    },
                    "count": {
                        "type": "number",
                        "description": "Number of results (1-20, default 10)",
                        "default": 10
                    },
                    "offset": {
                        "type": "number",
                        "description": "Pagination offset (max 9, default 0)",
                        "default": 0
                    }
                },
                "required": ["query"]
            }
        }
    }

async def handle_tool_call(request_id: str, tool_name: str, arguments: Dict[str, Any]) -> None:
    """
    Handle a tool call request from the MCP protocol.
    
    Args:
        request_id: The ID of the request.
        tool_name: The name of the tool to call.
        arguments: The arguments to pass to the tool.
    """
    try:
        if tool_name == "brave_web_search":
            query = arguments.get("query")
            count = arguments.get("count", 10)
            offset = arguments.get("offset", 0)
            
            if not query:
                raise ValueError("Query parameter is required")
            
            result = await brave_web_search(query, count, offset)
            
            # Send the response
            response = {
                "type": RESPONSE_TYPE,
                "request_id": request_id,
                "content": result
            }
            print(json.dumps(response), flush=True)
            logger.info(f"Sent response for request {request_id}")
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    except Exception as e:
        # Send error response
        error_response = {
            "type": ERROR_TYPE,
            "request_id": request_id,
            "error": {
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        }
        print(json.dumps(error_response), flush=True)
        logger.error(f"Error handling tool call {tool_name}: {str(e)}")

async def handle_resource_request(request_id: str, uri: str) -> None:
    """
    Handle a resource request from the MCP protocol.
    
    Args:
        request_id: The ID of the request.
        uri: The URI of the resource to access.
    """
    # This MCP server doesn't provide any resources yet
    error_response = {
        "type": ERROR_TYPE,
        "request_id": request_id,
        "error": {
            "message": f"Resource not found: {uri}",
            "type": "ResourceNotFoundError"
        }
    }
    print(json.dumps(error_response), flush=True)
    logger.error(f"Resource not found: {uri}")

async def process_input() -> None:
    """
    Process input from stdin according to the MCP protocol.
    """
    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
                
            try:
                message = json.loads(line)
                message_type = message.get("type")
                request_id = message.get("request_id")
                
                if message_type == REQUEST_TYPE:
                    # Handle server info request
                    if message.get("command") == "server_info":
                        response = {
                            "type": RESPONSE_TYPE,
                            "request_id": request_id,
                            "content": {
                                "name": "brave-search",
                                "display_name": "Brave Search",
                                "description": "Provides access to the Brave Search API for web searches",
                                "version": "1.0.0",
                                "tools": get_tool_schemas()
                            }
                        }
                        print(json.dumps(response), flush=True)
                        logger.info("Sent server info response")
                
                elif message_type == TOOL_CALL_TYPE:
                    # Handle tool call
                    tool_name = message.get("tool_name")
                    arguments = message.get("arguments", {})
                    await handle_tool_call(request_id, tool_name, arguments)
                
                elif message_type == RESOURCE_REQUEST_TYPE:
                    # Handle resource request
                    uri = message.get("uri")
                    await handle_resource_request(request_id, uri)
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {line}")
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error reading from stdin: {str(e)}")
            break

async def main() -> None:
    """
    Main entry point for the MCP server.
    """
    try:
        # Initialize the client
        await initialize_client()
        
        # Process input
        await process_input()
    finally:
        # Clean up resources
        await cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)