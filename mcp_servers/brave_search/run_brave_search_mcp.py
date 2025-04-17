#!/usr/bin/env python3
"""
Brave Search MCP Server

This script runs an MCP server that provides access to the Brave Search API.
It follows the project's standards for async implementation, thread safety,
error handling, and resource management.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
import traceback

# Import the brave_search_client from the same directory
import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
import brave_search_client
BraveSearchClient = brave_search_client.BraveSearchClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("brave_search_mcp")

# Global variables
client: Optional[BraveSearchClient] = None
lock = asyncio.Lock()

# MCP protocol constants
REQUEST_TYPE = "request"
RESPONSE_TYPE = "response"
ERROR_TYPE = "error"
TOOL_CALL_TYPE = "tool_call"
RESOURCE_REQUEST_TYPE = "resource_request"

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