"""Web3 utility functions for dashboard"""

import os
import json
import logging
from typing import Optional, Dict, Any, Union
from web3 import Web3
from web3.contract import Contract
import eventlet

from ..web3.connection import create_web3_manager, Web3Manager

# Configure logging
logger = logging.getLogger(__name__)


class DashboardWeb3Utils:
    """Web3 utilities for dashboard"""

    def __init__(self):
        """Initialize Web3 utilities"""
        self.web3_manager = create_web3_manager()
        self.w3 = self.web3_manager.web3
        self.wallet_address = self.web3_manager.wallet_address

    def get_contract(self, address: str, abi: list) -> Contract:
        """Get contract instance"""
        try:
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(address), abi=abi
            )
            logger.debug(f"Contract loaded successfully: {address}")
            return contract

        except Exception as e:
            logger.error(f"Error loading contract: {str(e)}")
            raise

    def eth_call(self, transaction: Dict[str, Any]) -> bytes:
        """Make eth_call"""
        try:
            result = self.w3.eth.call(transaction)
            return result

        except Exception as e:
            logger.error(f"Error in eth_call: {str(e)}")
            raise

    def get_balance(self) -> float:
        """Get ETH balance for wallet address"""
        try:
            if not self.wallet_address:
                raise ValueError("Wallet address not initialized")
            balance_wei = self.w3.eth.get_balance(self.wallet_address)
            # Convert Wei to ETH
            balance_eth = self.w3.from_wei(balance_wei, "ether")
            return float(balance_eth)
        except Exception as e:
            logger.error(f"Error getting ETH balance: {str(e)}")
            return 0.0

    def get_token_balance(
        self, token_address: str, token_decimals: int = 18
    ) -> float:
        """Get token balance for wallet address"""
        try:
            if not self.wallet_address:
                raise ValueError("Wallet address not initialized")

            # Load ERC20 ABI
            with open(os.path.join("abi", "ERC20.json")) as f:
                erc20_abi = json.load(f)

            # Get token contract
            token_contract = self.get_contract(token_address, erc20_abi)

            # Get balance
            balance = token_contract.functions.balanceOf(self.wallet_address).call()

            # Convert to float with proper decimals
            return balance / (10**token_decimals)

        except Exception as e:
            logger.error(f"Error getting token balance: {str(e)}")
            return 0.0


def create_web3_utils() -> DashboardWeb3Utils:
    """Create a new DashboardWeb3Utils instance"""
    logger.info("Creating new DashboardWeb3Utils instance")
    return DashboardWeb3Utils()


# Singleton instance
_web3_utils = None


def get_web3_utils() -> DashboardWeb3Utils:
    """Get Web3 utils singleton instance"""
    global _web3_utils
    if _web3_utils is None:
        logger.info("Initializing DashboardWeb3Utils singleton")
        _web3_utils = create_web3_utils()
    return _web3_utils
