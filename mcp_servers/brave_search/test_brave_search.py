#!/usr/bin/env python3
"""
Test script for the Brave Search MCP server.

This script demonstrates how to use the BraveSearchClient directly
to perform web searches using the Brave Search API.
"""

import os
import sys
import asyncio
import json
from typing import Dict, Any

# Import the brave_search_client from the same directory
from . import brave_search_client
BraveSearchClient = brave_search_client.BraveSearchClient

async def test_web_search(query: str, count: int = 5) -> None:
    """
    Test the web search functionality.
    
    Args:
        query: The search query.
        count: Number of results to return.
    """
    # Get the API key from environment variable
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        print("Error: BRAVE_API_KEY environment variable is not set")
        print("Please set it in your .env file or export it in your shell")
        sys.exit(1)
    
    print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
    print(f"Searching for: {query}")
    print(f"Result count: {count}")
    print("-" * 50)
    
    try:
        async with BraveSearchClient(api_key) as client:
            results = await client.web_search(query, count=count)
            
            # Print the results in a readable format
            print(f"Total results: {results.get('total', 'unknown')}")
            print("-" * 50)
            
            web_results = results.get("web", {}).get("results", [])
            for i, result in enumerate(web_results, 1):
                print(f"{i}. {result.get('title', 'No title')}")
                print(f"   URL: {result.get('url', 'No URL')}")
                print(f"   Description: {result.get('description', 'No description')[:100]}...")
                print("-" * 50)
                
            print("Search completed successfully!")
            
    except Exception as e:
        print(f"Error during search: {str(e)}")
        raise

async def main() -> None:
    """
    Main entry point for the test script.
    """
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "cryptocurrency arbitrage trading bot"
    
    count = 5
    if len(sys.argv) > 2:
        try:
            count = int(sys.argv[2])
        except ValueError:
            print(f"Invalid count: {sys.argv[2]}. Using default: {count}")
    
    await test_web_search(query, count)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Test stopped by user")
    except Exception as e:
        print(f"Unhandled exception: {str(e)}")
        sys.exit(1)