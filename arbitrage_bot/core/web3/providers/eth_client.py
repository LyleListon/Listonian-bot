"""
Ethereum Client Module

This module provides functionality for:
- Ethereum node interactions
- Contract interactions
- Transaction management
"""

import logging
from typing import Any, Dict, Optional
from web3 import Web3
from eth_typing import ChecksumAddress

from ....utils.async_manager import with_retry
from ..interfaces import Web3Client

logger = logging.getLogger(__name__)

class EthClient(Web3Client):
    """Ethereum client implementation."""

    def __init__(
        self,
        w3: Web3,
        wallet_address: Optional[ChecksumAddress] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Ethereum client.

        Args:
            w3: Web3 instance
            wallet_address: Optional wallet address
            config: Optional configuration dictionary
        """
        self.w3 = w3
        self.wallet_address = wallet_address
        self.config = config or {}

        logger.info(
            f"Ethereum client initialized with "
            f"wallet {wallet_address or 'None'}"
        )

    @with_retry(retries=3, delay=1.0)
    async def get_balance(
        self,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get ETH balance for address.

        Args:
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            Balance in wei

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        if not address and not self.wallet_address:
            raise ValueError("No address provided and no wallet configured")

        address = address or self.wallet_address
        return self.w3.eth.get_balance(address)

    @with_retry(retries=3, delay=1.0)
    async def get_token_balance(
        self,
        token_address: ChecksumAddress,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get token balance for address.

        Args:
            token_address: Token contract address
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            Token balance

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        if not address and not self.wallet_address:
            raise ValueError("No address provided and no wallet configured")

        address = address or self.wallet_address

        # ERC20 balanceOf function selector
        selector = self.w3.keccak(text="balanceOf(address)")[:4]

        # Encode address parameter
        params = self.w3.eth.abi.encode_single("address", address)

        # Make call
        result = await self.w3.eth.call({
            "to": token_address,
            "data": selector + params
        })

        # Decode result
        return int.from_bytes(result, byteorder="big")

    @with_retry(retries=3, delay=1.0)
    async def get_nonce(
        self,
        address: Optional[ChecksumAddress] = None
    ) -> int:
        """
        Get next nonce for address.

        Args:
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            Next nonce

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        if not address and not self.wallet_address:
            raise ValueError("No address provided and no wallet configured")

        address = address or self.wallet_address
        return await self.w3.eth.get_transaction_count(address)

    async def close(self):
        """Clean up resources."""
        if hasattr(self.w3.provider, "close"):
            await self.w3.provider.close()
