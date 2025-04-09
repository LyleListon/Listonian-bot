#!/usr/bin/env python3
"""
Simple script to fetch and display the current block number on Base blockchain.
"""

import json
import time
import logging
import requests
from web3 import Web3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("base_block_checker")

# Base RPC URL
BASE_RPC_URL = "https://mainnet.base.org"

def get_current_block():
    """Get the current block number from Base blockchain."""
    try:
        # Connect to Base using Web3
        w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))
        
        # Check connection
        if not w3.is_connected():
            logger.error("Failed to connect to Base blockchain")
            return None
        
        # Get current block number
        block_number = w3.eth.block_number
        logger.info(f"Current Base block number: {block_number}")
        
        return block_number
    except Exception as e:
        logger.error(f"Error getting current block: {e}")
        return None

def main():
    """Main entry point."""
    try:
        logger.info("Fetching current Base block number...")
        
        # Get current block
        block_number = get_current_block()
        
        if block_number is not None:
            print(f"\n===================================")
            print(f"  CURRENT BASE BLOCK: {block_number}")
            print(f"===================================\n")
        else:
            print("\nFailed to get current Base block number.")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()
