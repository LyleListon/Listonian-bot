"""
Web3 Client Wrapper

This module provides a wrapper around web3.py's Web3 class to ensure consistent
async/await patterns and proper property access.
"""

import logging
from typing import Any, Dict, Optional
from web3 import Web3
from eth_typing import ChecksumAddress

logger = logging.getLogger(__name__)

class Web3ClientWrapper:
    """
    Wrapper around web3.py's Web3 class to ensure consistent async/await patterns.
    
    This wrapper provides async methods for commonly used Web3 properties and
    ensures consistent error handling and logging.
    """

    def __init__(self, w3: Web3):
        """
        Initialize the wrapper.

        Args:
            w3: Web3 instance to wrap
        """
        self._w3 = w3
        self.eth = EthWrapper(w3.eth)

    @property
    def middleware_onion(self):
        """Access to middleware stack."""
        return self._w3.middleware_onion

    def __getattr__(self, name: str) -> Any:
        """
        Passthrough for any attributes not explicitly wrapped.

        Args:
            name: Attribute name

        Returns:
            The requested attribute from the underlying Web3 instance
        """
        return getattr(self._w3, name)

class EthWrapper:
    """
    Wrapper around web3.py's Eth class to ensure consistent async/await patterns.
    """

    def __init__(self, eth):
        """
        Initialize the wrapper.

        Args:
            eth: Web3.eth instance to wrap
        """
        self._eth = eth

    async def get_gas_price(self) -> int:
        """
        Get current gas price.

        Returns:
            Current gas price in Wei
        """
        try:
            return self._eth.gas_price
        except Exception as e:
            logger.error(f"Failed to get gas price: {e}")
            raise

    async def get_block_number(self) -> int:
        """
        Get current block number.

        Returns:
            Current block number
        """
        try:
            return self._eth.block_number
        except Exception as e:
            logger.error(f"Failed to get block number: {e}")
            raise

    async def get_block(self, block_identifier: Any, full_transactions: bool = False) -> Dict[str, Any]:
        """
        Get block by number or hash.

        Args:
            block_identifier: Block number or hash
            full_transactions: Whether to include full transaction objects

        Returns:
            Block data
        """
        try:
            return self._eth.get_block(block_identifier, full_transactions)
        except Exception as e:
            logger.error(f"Failed to get block {block_identifier}: {e}")
            raise

    async def get_transaction_count(self, address: ChecksumAddress, block_identifier: Optional[Any] = None) -> int:
        """
        Get transaction count (nonce) for address.

        Args:
            address: Account address
            block_identifier: Block number or hash (default: 'latest')

        Returns:
            Transaction count
        """
        try:
            return self._eth.get_transaction_count(address, block_identifier or 'latest')
        except Exception as e:
            logger.error(f"Failed to get transaction count for {address}: {e}")
            raise

    async def get_balance(self, address: ChecksumAddress, block_identifier: Optional[Any] = None) -> int:
        """
        Get ETH balance for address.

        Args:
            address: Account address
            block_identifier: Block number or hash (default: 'latest')

        Returns:
            Balance in Wei
        """
        try:
            return self._eth.get_balance(address, block_identifier or 'latest')
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise

    async def call(self, transaction: Dict[str, Any], block_identifier: Optional[Any] = None) -> bytes:
        """
        Execute a new message call immediately without creating a transaction on the blockchain.

        Args:
            transaction: Transaction parameters
            block_identifier: Block number or hash (default: 'latest')

        Returns:
            The return data of the call
        """
        try:
            return self._eth.call(transaction, block_identifier or 'latest')
        except Exception as e:
            logger.error(f"Failed to execute eth_call: {e}")
            raise

    def __getattr__(self, name: str) -> Any:
        """
        Passthrough for any attributes not explicitly wrapped.

        Args:
            name: Attribute name

        Returns:
            The requested attribute from the underlying Eth instance
        """
        attr = getattr(self._eth, name)
        
        # If the attribute is a method, wrap it to ensure async compatibility
        if callable(attr):
            async def wrapped(*args, **kwargs):
                return attr(*args, **kwargs)
            return wrapped
        return attr