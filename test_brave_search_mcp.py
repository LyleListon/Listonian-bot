#!/usr/bin/env python3
"""
Test script for Brave Search MCP Server

This script tests the Brave Search MCP server by sending a request to it
and displaying the response. It's useful for verifying that the server
is working correctly before using it with Cline.
"""

import os
import sys
import json
import asyncio
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_brave_search_mcp")

# Load environment variables from .env file
load_dotenv()

# MCP protocol constants
REQUEST_TYPE = "request"
RESPONSE_TYPE = "response"
ERROR_TYPE = "error"
TOOL_CALL_TYPE = "tool_call"
RESOURCE_REQUEST_TYPE = "resource_request"

async def send_server_info_request(writer):
    """
    Send a server_info request to the MCP server.
    
    Args:
        writer: The StreamWriter to write to.
    """
    request = {
        "type": REQUEST_TYPE,
        "request_id": "test-1",
        "command": "server_info"
    }
    writer.write(json.dumps(request).encode() + b'\n')
    await writer.drain()
    logger.info("Sent server_info request")

async def send_tool_call_request(writer, query="latest cryptocurrency prices", count=5, offset=0):
    """
    Send a tool_call request to the MCP server.
    
    Args:
        writer: The StreamWriter to write to.
        query: The search query.
        count: Number of results to return.
        offset: Pagination offset.
    """
    request = {
        "type": TOOL_CALL_TYPE,
        "request_id": "test-2",
        "tool_name": "brave_web_search",
        "arguments": {
            "query": query,
            "count": count,
            "offset": offset
        }
    }
    writer.write(json.dumps(request).encode() + b'\n')
    await writer.drain()
    logger.info(f"Sent tool_call request with query: {query}")

async def process_response(reader):
    """
    Process a response from the MCP server.
    
    Args:
        reader: The StreamReader to read from.
    """
    try:
        line = await reader.readline()
        if not line:
            logger.error("No response received")
            return
            
        response = json.loads(line.decode())
        response_type = response.get("type")
        request_id = response.get("request_id")
        
        if response_type == RESPONSE_TYPE:
            content = response.get("content")
            logger.info(f"Received response for request {request_id}")
            
            if isinstance(content, dict) and "tools" in content:
                # This is a server_info response
                logger.info(f"Server name: {content.get('name')}")
                logger.info(f"Server description: {content.get('description')}")
                logger.info(f"Available tools: {list(content.get('tools', {}).keys())}")
            else:
                # This is a tool_call response
                if isinstance(content, dict) and "web" in content:
                    # Print search results
                    results = content.get("web", {}).get("results", [])
                    logger.info(f"Found {len(results)} search results")
                    
                    for i, result in enumerate(results, 1):
                        print(f"\nResult {i}:")
                        print(f"Title: {result.get('title')}")
                        print(f"URL: {result.get('url')}")
                        print(f"Description: {result.get('description')}")
                else:
                    # Just print the raw content
                    print(json.dumps(content, indent=2))
        
        elif response_type == ERROR_TYPE:
            error = response.get("error", {})
            logger.error(f"Error for request {request_id}: {error.get('message')}")
            logger.error(f"Error type: {error.get('type')}")
            if "traceback" in error:
                logger.error(f"Traceback: {error.get('traceback')}")
    
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON response: {line.decode()}")
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")

async def run_test():
    """
    Run the test by starting the MCP server and sending requests to it.
    """
    # Start the MCP server as a subprocess
    logger.info("Starting Brave Search MCP server...")
    process = await asyncio.create_subprocess_exec(
        sys.executable, "run_brave_search_mcp_wrapper.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    try:
        # Wait a moment for the server to initialize
        await asyncio.sleep(1)
        
        # Create a reader and writer for the subprocess
        reader = process.stdout
        writer = process.stdin
        
        # Send a server_info request
        await send_server_info_request(writer)
        
        # Process the response
        await process_response(reader)
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Send a tool_call request
        await send_tool_call_request(writer)
        
        # Process the response
        await process_response(reader)
        
        # Wait a moment before closing
        await asyncio.sleep(1)
        
    finally:
        # Terminate the subprocess
        logger.info("Terminating MCP server...")
        process.terminate()
        await process.wait()
        logger.info("Test completed")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        logger.info("Test stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)