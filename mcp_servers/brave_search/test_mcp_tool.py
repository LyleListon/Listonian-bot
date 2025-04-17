#!/usr/bin/env python3
"""
Test script for using the Brave Search MCP server through the MCP protocol.

This script demonstrates how to use the MCP tool to perform web searches
using the Brave Search API.
"""

import os
import sys
import json
import asyncio
import subprocess
from typing import Dict, Any, Optional

async def run_mcp_tool(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Run an MCP tool using subprocess.
    
    Args:
        server_name: The name of the MCP server.
        tool_name: The name of the tool to run.
        arguments: The arguments to pass to the tool.
        
    Returns:
        The result of the tool execution, or None if there was an error.
    """
    # Format the MCP tool request
    request = {
        "server_name": server_name,
        "tool_name": tool_name,
        "arguments": arguments
    }
    
    # Convert the request to JSON
    request_json = json.dumps(request)
    
    # Print the request for debugging
    print(f"Sending request to MCP tool:")
    print(f"Server: {server_name}")
    print(f"Tool: {tool_name}")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    print("-" * 50)
    
    try:
        # Run the MCP tool using the Roo CLI
        # Note: This is a simplified example and may need adjustment based on your setup
        cmd = ["roo", "mcp", "tool", request_json]
        
        # Run the command and capture the output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        # Check if there was an error
        if process.returncode != 0:
            print(f"Error running MCP tool: {stderr.decode()}")
            return None
        
        # Parse the result
        result = json.loads(stdout.decode())
        return result
        
    except Exception as e:
        print(f"Error running MCP tool: {str(e)}")
        return None

async def test_brave_search() -> None:
    """
    Test the brave_web_search MCP tool.
    """
    # Define the search query
    query = "cryptocurrency arbitrage trading bot"
    
    # Define the arguments for the brave_web_search tool
    arguments = {
        "query": query,
        "count": 5,
        "offset": 0
    }
    
    # Run the MCP tool
    result = await run_mcp_tool("brave-search", "brave_web_search", arguments)
    
    # Check if the tool execution was successful
    if result is None:
        print("Failed to run the MCP tool")
        return
    
    # Print the results
    print(f"Search results for: {query}")
    print(f"Total results: {result.get('total', 'unknown')}")
    print("-" * 50)
    
    web_results = result.get("web", {}).get("results", [])
    for i, result in enumerate(web_results, 1):
        print(f"{i}. {result.get('title', 'No title')}")
        print(f"   URL: {result.get('url', 'No URL')}")
        print(f"   Description: {result.get('description', 'No description')[:100]}...")
        print("-" * 50)
    
    print("Search completed successfully!")

async def main() -> None:
    """
    Main entry point for the test script.
    """
    await test_brave_search()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Test stopped by user")
    except Exception as e:
        print(f"Unhandled exception: {str(e)}")
        sys.exit(1)