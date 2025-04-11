"""
Web3 interaction layer.

This module provides:
1. Contract interaction
2. Transaction management
3. Gas price estimation
4. Network monitoring
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from web3 import Web3, AsyncWeb3
from web3.contract import Contract
from web3.exceptions import ContractLogicError, TransactionNotFound

# Configure logging
logger = logging.getLogger(__name__)


class Web3Error(Exception):
    """Base exception for Web3 related errors."""

    pass


class Web3Manager:
    """Manages Web3 interactions and contract operations."""

    def __init__(self):
        """Initialize the Web3 manager."""
        self._lock = asyncio.Lock()
        self._contract_cache: Dict[str, Contract] = {}
        self._provider = None
        self._web3 = None
        self._chain_id = None
        self._last_block = 0
        self._blocks_per_minute = 0
        self._last_block_time = 0
        self._min_gas_price = float("inf")
        self._max_gas_price = 0

        # Load configuration
        self._rpc_url = os.getenv("RPC_URL", "https://mainnet.base.org")
        self._chain_id = int(os.getenv("CHAIN_ID", "8453"))  # Base network

        # Load backup RPC URLs
        backup_urls_str = os.getenv("BACKUP_RPC_URLS", "[]")
        try:
            import json

            self._backup_urls = json.loads(backup_urls_str)
        except Exception as e:
            logger.warning(f"Failed to parse BACKUP_RPC_URLS: {backup_urls_str}")
            self._backup_urls = []

        logger.info(f"Initializing Web3Manager with RPC URL: {self._rpc_url}")

    async def initialize(self) -> None:
        """Initialize Web3 connection."""
        try:
            self._web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self._rpc_url))

            # Test connection
            chain_id = await self._web3.eth.chain_id
            if chain_id != self._chain_id:
                raise Web3Error(
                    f"Chain ID mismatch: expected {self._chain_id}, got {chain_id}"
                )

            logger.info("Web3 connection initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Web3: {e}")
            raise Web3Error(f"Web3 initialization failed: {e}")

    @property
    def chain_id(self) -> int:
        """Get the current chain ID."""
        return self._chain_id

    async def get_block_number(self) -> int:
        """Get the current block number."""
        try:
            block = await self._web3.eth.block_number

            # Calculate blocks per minute
            now = (await self._web3.eth.get_block("latest")).timestamp
            if self._last_block > 0 and self._last_block_time > 0:
                time_diff = now - self._last_block_time
                if time_diff > 0:
                    block_diff = block - self._last_block
                    self._blocks_per_minute = (block_diff / time_diff) * 60

            self._last_block = block
            self._last_block_time = now

            return block
        except Exception as e:
            logger.error(f"Failed to get block number: {e}")
            raise Web3Error(f"Failed to get block number: {e}")

    async def get_gas_price(self) -> int:
        """Get current gas price in wei."""
        try:
            gas_price = await self._web3.eth.gas_price

            # Update min/max tracking
            self._min_gas_price = min(self._min_gas_price, gas_price)
            self._max_gas_price = max(self._max_gas_price, gas_price)

            return gas_price
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            raise Web3Error(f"Failed to get gas price: {e}")

    async def get_balance(self, address: str) -> int:
        """Get balance of address in wei."""
        try:
            if not Web3.is_address(address):
                raise ValueError("Invalid address format")
            address = Web3.to_checksum_address(address)
            return await self._web3.eth.get_balance(address)
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise Web3Error(f"Failed to get balance: {e}")

    async def get_transaction_count(self, address: str) -> int:
        """Get transaction count (nonce) for address."""
        try:
            if not Web3.is_address(address):
                raise ValueError("Invalid address format")
            address = Web3.to_checksum_address(address)
            return await self._web3.eth.get_transaction_count(address)
        except Exception as e:
            logger.error(f"Failed to get transaction count for {address}: {e}")
            raise Web3Error(f"Failed to get transaction count: {e}")

    async def get_contract(self, address: str, abi_name: str) -> Contract:
        """Get contract instance with caching."""
        cache_key = f"{address}:{abi_name}"

        async with self._lock:
            if cache_key in self._contract_cache:
                return self._contract_cache[cache_key]

            try:
                # Validate address
                if not Web3.is_address(address):
                    raise ValueError("Invalid address format")
                address = Web3.to_checksum_address(address)

                # Load ABI
                import json

                abi_path = f"abi/{abi_name}.json"
                with open(abi_path) as f:
                    abi = json.load(f)

                # Create contract
                contract = self._web3.eth.contract(address=address, abi=abi)

                # Cache contract
                self._contract_cache[cache_key] = contract
                return contract

            except Exception as e:
                logger.error(f"Failed to load contract {address}: {e}")
                raise Web3Error(f"Contract loading failed: {e}")

    async def estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """Estimate gas for transaction."""
        try:
            return await self._web3.eth.estimate_gas(transaction)
        except Exception as e:
            logger.error(f"Failed to estimate gas: {e}")
            raise Web3Error(f"Gas estimation failed: {e}")

    async def get_block(self, block_identifier: str = "latest") -> Dict[str, Any]:
        """Get block data."""
        try:
            return await self._web3.eth.get_block(block_identifier)
        except Exception as e:
            logger.error(f"Failed to get block {block_identifier}: {e}")
            raise Web3Error(f"Failed to get block: {e}")

    async def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction data."""
        try:
            return await self._web3.eth.get_transaction(tx_hash)
        except TransactionNotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to get transaction {tx_hash}: {e}")
            raise Web3Error(f"Failed to get transaction: {e}")

    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt."""
        try:
            return await self._web3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to get transaction receipt {tx_hash}: {e}")
            raise Web3Error(f"Failed to get transaction receipt: {e}")

    @property
    def blocks_per_minute(self) -> float:
        """Get blocks per minute rate."""
        return self._blocks_per_minute

    @property
    def min_gas_price(self) -> int:
        """Get minimum observed gas price."""
        return self._min_gas_price

    @property
    def max_gas_price(self) -> int:
        """Get maximum observed gas price."""
        return self._max_gas_price

    async def __aenter__(self) -> "Web3Manager":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # Cleanup if needed
        pass


# Singleton instance
_web3_manager: Optional[Web3Manager] = None


def get_web3_manager() -> Web3Manager:
    """Get the Web3 manager instance."""
    global _web3_manager
    if _web3_manager is None:
        _web3_manager = Web3Manager()
    return _web3_manager
