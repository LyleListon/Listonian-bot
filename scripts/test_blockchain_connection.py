#!/usr/bin/env python3
"""
Blockchain Connection Test Script

This script tests the connection to the Base blockchain using the configured RPC endpoints.
It verifies that the RPC endpoints and API keys are working correctly.
"""

import os
import sys
import logging
import json
import time
from pathlib import Path
from web3 import Web3
from eth_account.messages import encode_defunct

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

def test_primary_rpc_connection():
    """Test the connection to the primary RPC endpoint."""
    try:
        # Get the RPC URL from environment
        rpc_url = os.environ.get("BASE_RPC_URL", "")
        
        if not rpc_url:
            logger.error("BASE_RPC_URL not set")
            return False
        
        logger.info(f"Testing connection to primary RPC endpoint: {rpc_url}")
        
        # Connect to the RPC endpoint
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Check if connected
        if web3.is_connected():
            # Get the latest block number
            block_number = web3.eth.block_number
            
            # Get the latest block
            block = web3.eth.get_block(block_number)
            
            # Get chain ID
            chain_id = web3.eth.chain_id
            
            logger.info(f"Successfully connected to Base blockchain")
            logger.info(f"Chain ID: {chain_id}")
            logger.info(f"Latest block number: {block_number}")
            logger.info(f"Latest block timestamp: {block['timestamp']} ({time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(block['timestamp']))})")
            logger.info(f"Latest block hash: {block['hash'].hex()}")
            logger.info(f"Latest block gas used: {block['gasUsed']}")
            
            return True
        else:
            logger.error(f"Failed to connect to primary RPC endpoint")
            return False
    
    except Exception as e:
        logger.exception(f"Error testing primary RPC connection: {str(e)}")
        return False

def test_fallback_rpc_connection():
    """Test the connection to the fallback RPC endpoint."""
    try:
        # Get the fallback RPC URL from environment
        fallback_rpc_url = os.environ.get("INFURA_BASE_RPC_URL", "")
        
        if not fallback_rpc_url:
            logger.warning("INFURA_BASE_RPC_URL not set, skipping fallback RPC test")
            return True
        
        logger.info(f"Testing connection to fallback RPC endpoint: {fallback_rpc_url}")
        
        # Connect to the RPC endpoint
        web3 = Web3(Web3.HTTPProvider(fallback_rpc_url))
        
        # Check if connected
        if web3.is_connected():
            # Get the latest block number
            block_number = web3.eth.block_number
            
            logger.info(f"Successfully connected to fallback RPC endpoint")
            logger.info(f"Latest block number: {block_number}")
            
            return True
        else:
            logger.error(f"Failed to connect to fallback RPC endpoint")
            return False
    
    except Exception as e:
        logger.exception(f"Error testing fallback RPC connection: {str(e)}")
        return False

def test_wallet_connection():
    """Test the connection to the wallet."""
    try:
        # Get the wallet address and private key from environment
        wallet_address = os.environ.get("WALLET_ADDRESS", "")
        private_key = os.environ.get("PRIVATE_KEY", "")
        
        if not wallet_address or not private_key:
            logger.warning("WALLET_ADDRESS or PRIVATE_KEY not set, skipping wallet test")
            return True
        
        # Get the RPC URL from environment
        rpc_url = os.environ.get("BASE_RPC_URL", "")
        
        if not rpc_url:
            logger.error("BASE_RPC_URL not set")
            return False
        
        logger.info(f"Testing wallet connection for address: {wallet_address}")
        
        # Connect to the RPC endpoint
        web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Check if connected
        if not web3.is_connected():
            logger.error(f"Failed to connect to RPC endpoint")
            return False
        
        # Check if the wallet address is valid
        if not web3.is_address(wallet_address):
            logger.error(f"Invalid wallet address: {wallet_address}")
            return False
        
        # Convert the address to checksum format
        checksum_address = web3.to_checksum_address(wallet_address)
        
        # Get the wallet balance
        balance_wei = web3.eth.get_balance(checksum_address)
        balance_eth = web3.from_wei(balance_wei, "ether")
        
        logger.info(f"Wallet address: {checksum_address}")
        logger.info(f"Wallet balance: {balance_eth} ETH")
        
        # Try to sign a message with the private key
        try:
            # Create an account from the private key
            account = web3.eth.account.from_key(private_key)
            
            # Check if the account address matches the wallet address
            if account.address.lower() != wallet_address.lower():
                logger.error(f"Private key does not match wallet address")
                logger.error(f"Private key address: {account.address}")
                logger.error(f"Wallet address: {wallet_address}")
                return False
            
            # Sign a message
            message = "Test message for Listonian Arbitrage Bot"
            message_hash = encode_defunct(text=message)
            signed_message = web3.eth.account.sign_message(
                message_hash,
                private_key=private_key
            )
            
            logger.info(f"Successfully signed message with private key")
            logger.info(f"Message: {message}")
            logger.info(f"Signature: {signed_message.signature.hex()[:20]}...")
            
            return True
        
        except Exception as e:
            logger.exception(f"Error signing message with private key: {str(e)}")
            return False
    
    except Exception as e:
        logger.exception(f"Error testing wallet connection: {str(e)}")
        return False

def test_basescan_api():
    """Test the connection to the Basescan API."""
    try:
        # Get the Basescan API key from environment
        api_key = os.environ.get("BASESCAN_API_KEY", "")
        
        if not api_key:
            logger.warning("BASESCAN_API_KEY not set, skipping Basescan API test")
            return True
        
        import requests
        
        logger.info(f"Testing connection to Basescan API")
        
        # Build the API URL
        api_url = f"https://api.basescan.org/api?module=stats&action=ethsupply&apikey={api_key}"
        
        # Make a request to the API
        response = requests.get(api_url, timeout=10)
        
        # Check if the response is successful
        if response.status_code == 200:
            # Parse the response
            data = response.json()
            
            # Check if the response is valid
            if data.get("status") == "1":
                logger.info(f"Successfully connected to Basescan API")
                logger.info(f"Response: {data}")
                
                return True
            else:
                logger.error(f"Invalid response from Basescan API: {data}")
                return False
        else:
            logger.error(f"Failed to connect to Basescan API: {response.status_code} - {response.text}")
            return False
    
    except Exception as e:
        logger.exception(f"Error testing Basescan API connection: {str(e)}")
        return False

def main():
    """Main entry point for the script."""
    try:
        logger.info("Starting blockchain connection test")
        
        # Load environment variables
        if not load_env(".env.production"):
            logger.error("Failed to load environment variables")
            return 1
        
        # Test primary RPC connection
        if not test_primary_rpc_connection():
            logger.error("Primary RPC connection test failed")
            return 1
        
        logger.info("Primary RPC connection test passed")
        
        # Test fallback RPC connection
        if not test_fallback_rpc_connection():
            logger.warning("Fallback RPC connection test failed")
            # Don't return error for fallback failure
        else:
            logger.info("Fallback RPC connection test passed")
        
        # Test wallet connection
        if not test_wallet_connection():
            logger.error("Wallet connection test failed")
            return 1
        
        logger.info("Wallet connection test passed")
        
        # Test Basescan API
        if not test_basescan_api():
            logger.warning("Basescan API test failed")
            # Don't return error for Basescan API failure
        else:
            logger.info("Basescan API test passed")
        
        logger.info("All blockchain connection tests passed!")
        return 0
    
    except Exception as e:
        logger.exception(f"Error in blockchain connection test: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())