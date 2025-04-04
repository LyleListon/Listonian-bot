#!/usr/bin/env python3
"""
Production Test Script

This script tests the Listonian Arbitrage Bot in production mode.
It connects to the MCP server, calls the scan_dexes tool, and verifies that the response is valid.
"""

import os
import sys
import logging
import json
import time
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the environment loader
from scripts.load_env import load_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

def test_api_connection():
    """Test the connection to the API."""
    try:
        # Get the API endpoint from environment
        host = os.environ.get("MCP_SERVER_HOST", "localhost")
        port = os.environ.get("MCP_SERVER_PORT", "9050")
        api_key = os.environ.get("BASE_DEX_SCANNER_API_KEY", "")
        
        # Build the API URL
        api_url = f"http://{host}:{port}"
        
        logger.info(f"Testing connection to API at {api_url}")
        
        # Make a request to the root endpoint
        response = requests.get(f"{api_url}/", timeout=10)
        
        # Check if the response is successful
        if response.status_code == 200:
            logger.info(f"API connection successful: {response.text}")
            return True
        else:
            logger.error(f"API connection failed: {response.status_code} - {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Error testing API connection: {str(e)}")
        return False

def test_scan_dexes():
    """Test the scan_dexes tool."""
    try:
        # Get the API endpoint from environment
        host = os.environ.get("MCP_SERVER_HOST", "localhost")
        port = os.environ.get("MCP_SERVER_PORT", "9050")
        api_key = os.environ.get("BASE_DEX_SCANNER_API_KEY", "")
        
        # Build the API URL
        api_url = f"http://{host}:{port}/api/v1/scan_dexes"
        
        logger.info(f"Testing scan_dexes at {api_url}")
        
        # Set up headers with API key
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        
        # Make a request to the scan_dexes endpoint
        response = requests.post(api_url, headers=headers, json={}, timeout=30)
        
        # Check if the response is successful
        if response.status_code == 200:
            # Parse the response
            data = response.json()
            
            # Check if the response is valid
            if isinstance(data, list):
                logger.info(f"scan_dexes successful: Found {len(data)} DEXes")
                
                # Print DEX details
                for i, dex in enumerate(data, 1):
                    logger.info(f"DEX {i}:")
                    logger.info(f"  Name: {dex.get('name', 'Unknown')}")
                    logger.info(f"  Factory: {dex.get('factory_address', 'Unknown')}")
                    logger.info(f"  Router: {dex.get('router_address', 'Unknown')}")
                    logger.info(f"  Type: {dex.get('type', 'Unknown')}")
                    logger.info(f"  Version: {dex.get('version', 'Unknown')}")
                
                return True
            else:
                logger.error(f"Invalid response format: {data}")
                return False
        else:
            logger.error(f"scan_dexes failed: {response.status_code} - {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Error testing scan_dexes: {str(e)}")
        return False

def test_get_factory_pools():
    """Test the get_factory_pools tool."""
    try:
        # First, get the DEXes
        host = os.environ.get("MCP_SERVER_HOST", "localhost")
        port = os.environ.get("MCP_SERVER_PORT", "9050")
        api_key = os.environ.get("BASE_DEX_SCANNER_API_KEY", "")
        
        # Build the API URL for scan_dexes
        scan_url = f"http://{host}:{port}/api/v1/scan_dexes"
        
        # Set up headers with API key
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }
        
        # Make a request to the scan_dexes endpoint
        response = requests.post(scan_url, headers=headers, json={}, timeout=30)
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"scan_dexes failed: {response.status_code} - {response.text}")
            return False
        
        # Parse the response
        dexes = response.json()
        
        # Check if we have any DEXes
        if not dexes:
            logger.warning("No DEXes found, skipping get_factory_pools test")
            return True
        
        # Get the first DEX factory address
        factory_address = dexes[0].get("factory_address")
        dex_name = dexes[0].get("name")
        
        if not factory_address:
            logger.warning("No factory address found, skipping get_factory_pools test")
            return True
        
        logger.info(f"Testing get_factory_pools for {dex_name} ({factory_address})")
        
        # Build the API URL for get_factory_pools
        pools_url = f"http://{host}:{port}/api/v1/get_factory_pools"
        
        # Make a request to the get_factory_pools endpoint
        response = requests.post(
            pools_url,
            headers=headers,
            json={"factory_address": factory_address},
            timeout=30
        )
        
        # Check if the response is successful
        if response.status_code == 200:
            # Parse the response
            data = response.json()
            
            # Check if the response is valid
            if isinstance(data, list):
                logger.info(f"get_factory_pools successful: Found {len(data)} pools for {dex_name}")
                
                # Print pool details for the first 5 pools
                for i, pool in enumerate(data[:5], 1):
                    logger.info(f"Pool {i}:")
                    logger.info(f"  Address: {pool.get('address', 'Unknown')}")
                    logger.info(f"  Token0: {pool.get('token0', {}).get('symbol', 'Unknown')}")
                    logger.info(f"  Token1: {pool.get('token1', {}).get('symbol', 'Unknown')}")
                    logger.info(f"  Liquidity: ${pool.get('liquidity_usd', 0):,.2f}")
                
                return True
            else:
                logger.error(f"Invalid response format: {data}")
                return False
        else:
            logger.error(f"get_factory_pools failed: {response.status_code} - {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to API: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Error testing get_factory_pools: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    try:
        logger.info("Starting production test")
        
        # Load environment variables
        if not load_env(".env.production"):
            logger.error("Failed to load environment variables")
            return 1
        
        # Test API connection
        if not test_api_connection():
            logger.error("API connection test failed")
            return 1
        
        logger.info("API connection test passed")
        
        # Test scan_dexes
        if not test_scan_dexes():
            logger.error("scan_dexes test failed")
            return 1
        
        logger.info("scan_dexes test passed")
        
        # Test get_factory_pools
        if not test_get_factory_pools():
            logger.error("get_factory_pools test failed")
            return 1
        
        logger.info("get_factory_pools test passed")
        
        logger.info("All tests passed! The production setup is working correctly.")
        return 0
    
    except Exception as e:
        logger.exception(f"Error in production test: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())