"""
Web3 Manager Module

This module provides functionality for:
- Managing Web3 connections
- Contract interactions
- Transaction management
"""

import logging
from typing import Any, Dict, Optional
from web3 import Web3
from eth_account import Account
from eth_typing import ChecksumAddress

from ...utils.async_manager import with_retry

logger = logging.getLogger(__name__)

class Web3Manager:
    """Manages Web3 connections and interactions."""

    def __init__(
        self,
        provider_url: str,
        private_key: Optional[str] = None,
        chain_id: int = 8453,  # Base mainnet
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Web3 manager.

        Args:
            provider_url: Web3 provider URL
            private_key: Optional private key for transactions
            chain_id: Chain ID
            config: Optional configuration dictionary
        """
        self.provider_url = provider_url
        self.chain_id = chain_id
        self.config = config or {}

        # Initialize Web3
        self.w3 = Web3(Web3.HTTPProvider(provider_url))

        # Configure for PoA chains
        self.w3.eth.default_block = "latest"

        # Set up account if private key provided
        self.private_key = private_key
        self.account = None
        self.wallet_address = None

        if private_key:
            self.account = Account.from_key(private_key)
            self.wallet_address = self.account.address

            # Add middleware for signing transactions
            def sign_transaction(transaction_dict):
                signed = self.account.sign_transaction(transaction_dict)
                return signed.rawTransaction

            self.w3.middleware_onion.add(
                lambda make_request, w3: (
                    lambda method, params: make_request(
                        method,
                        [sign_transaction(params[0])] if method == 'eth_sendRawTransaction'
                        else params
                    )
                )
            )

        # Expose eth module
        self.eth = self.w3.eth

        logger.info(
            f"Web3 manager initialized for chain {chain_id} "
            f"with account {self.wallet_address or 'None'}"
        )

    @property
    def is_connected(self) -> bool:
        """Check if connected to node."""
        return self.w3.is_connected()

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
        return self.eth.get_balance(address)

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
        params = self.eth.abi.encode_single("address", address)

        # Make call
        result = await self.eth.call({
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
        return await self.eth.get_transaction_count(address)

    async def close(self):
        """Clean up resources."""
        if hasattr(self.w3.provider, "close"):
            await self.w3.provider.close()

async def create_web3_manager(
    provider_url: str,
    private_key: Optional[str] = None,
    chain_id: int = 8453,
    config: Optional[Dict[str, Any]] = None
) -> Web3Manager:
    """
    Create a new Web3 manager.

    Args:
        provider_url: Web3 provider URL
        private_key: Optional private key for transactions
        chain_id: Chain ID
        config: Optional configuration dictionary

    Returns:
        Web3Manager instance
    """
    return Web3Manager(
        provider_url=provider_url,
        private_key=private_key,
        chain_id=chain_id,
        config=config
    )
