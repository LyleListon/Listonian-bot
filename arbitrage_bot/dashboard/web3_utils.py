"""Web3 utility functions for dashboard"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, Union
from web3 import Web3
from web3.contract import Contract
from pathlib import Path

from ..web3.connection import create_web3_manager, Web3Manager

# Configure logging
logger = logging.getLogger(__name__)

class DashboardWeb3Utils:
    """Web3 utilities for dashboard"""

    _instance = None
    _lock = asyncio.Lock()
    _contract_lock = asyncio.Lock()
    _initialized = False

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super(DashboardWeb3Utils, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize Web3 utilities"""
        if self._initialized:
            return
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Web3 utilities asynchronously."""
        if self._initialized:
            return True

        async with self._lock:
            if self._initialized:  # Double-check under lock
                return True

            try:
                self.web3_manager = await create_web3_manager()
                self.w3 = self.web3_manager.w3
                self.wallet_address = self.web3_manager.wallet_address
                self._initialized = True
                logger.debug("Web3 utilities initialized successfully")
                return True
            except Exception as e:
                logger.error("Failed to initialize Web3 utilities: %s", str(e))
                return False

    async def get_contract(self, address: str, abi: list) -> Contract:
        """Get contract instance"""
        if not self._initialized and not await self.initialize():
            raise RuntimeError("Web3 utilities not initialized")

        try:
            async with self._contract_lock:
                contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(address), abi=abi
                )
                logger.debug("Contract loaded successfully: %s", address)
                return contract

        except Exception as e:
            logger.error("Error loading contract: %s", str(e))
            raise

    async def eth_call(self, transaction: Dict[str, Any]) -> bytes:
        """Make eth_call"""
        if not self._initialized and not await self.initialize():
            raise RuntimeError("Web3 utilities not initialized")

        try:
            return await self.w3.eth.call(transaction)
        except Exception as e:
            logger.error("Error in eth_call: %s", str(e))
            raise

    async def get_balance(self) -> float:
        """Get ETH balance for wallet address"""
        if not self._initialized and not await self.initialize():
            raise RuntimeError("Web3 utilities not initialized")

        try:
            if not self.wallet_address:
                raise ValueError("Wallet address not initialized")
            balance_wei = await self.w3.eth.get_balance(self.wallet_address)
            # Convert Wei to ETH
            balance_eth = self.w3.from_wei(balance_wei, "ether")
            return float(balance_eth)
        except Exception as e:
            logger.error("Error getting ETH balance: %s", str(e))
            return 0.0

    async def get_token_balance(
        self, token_address: str, token_decimals: int = 18
    ) -> float:
        """Get token balance for wallet address"""
        if not self._initialized and not await self.initialize():
            raise RuntimeError("Web3 utilities not initialized")

        try:
            if not self.wallet_address:
                raise ValueError("Wallet address not initialized")

            # Load ERC20 ABI
            abi_path = Path("abi/ERC20.json")
            async with asyncio.Lock():
                with open(abi_path) as f:
                    erc20_abi = json.load(f)

            # Get token contract
            token_contract = await self.get_contract(token_address, erc20_abi)

            # Get balance
            balance = await token_contract.functions.balanceOf(self.wallet_address).call()

            # Convert to float with proper decimals
            return balance / (10**token_decimals)

        except Exception as e:
            logger.error("Error getting token balance: %s", str(e))
            return 0.0

    async def get_transaction_count(self, address: str) -> int:
        """Get transaction count (nonce) for address"""
        if not self._initialized and not await self.initialize():
            raise RuntimeError("Web3 utilities not initialized")

        try:
            return await self.w3.eth.get_transaction_count(address)
        except Exception as e:
            logger.error("Error getting transaction count: %s", str(e))
            raise

    async def wait_for_transaction_receipt(self, tx_hash: bytes, timeout: int = 300) -> Dict[str, Any]:
        """Wait for transaction receipt with timeout"""
        if not self._initialized and not await self.initialize():
            raise RuntimeError("Web3 utilities not initialized")

        try:
            return await asyncio.wait_for(
                self.w3.eth.wait_for_transaction_receipt(tx_hash),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for transaction receipt")
            raise
        except Exception as e:
            logger.error("Error waiting for transaction receipt: %s", str(e))
            raise

async def create_web3_utils() -> DashboardWeb3Utils:
    """Create and initialize a new DashboardWeb3Utils instance"""
    logger.info("Creating new DashboardWeb3Utils instance")
    utils = DashboardWeb3Utils()
    if not await utils.initialize():
        raise RuntimeError("Failed to initialize Web3 utilities")
    return utils

# Singleton instance
_web3_utils = None
_utils_lock = asyncio.Lock()

async def get_web3_utils() -> DashboardWeb3Utils:
    """Get Web3 utils singleton instance"""
    global _web3_utils
    if _web3_utils is None:
        async with _utils_lock:
            if _web3_utils is None:  # Double-check under lock
                logger.info("Initializing DashboardWeb3Utils singleton")
                _web3_utils = await create_web3_utils()
    return _web3_utils
