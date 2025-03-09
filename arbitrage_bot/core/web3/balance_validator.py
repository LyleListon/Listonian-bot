"""
Balance Validator Module

This module provides functionality for:
- Validating token balances
- Checking liquidity requirements
- Verifying transaction feasibility
"""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional
from eth_typing import ChecksumAddress

from .web3_manager import Web3Manager
from ...utils.async_manager import with_retry

logger = logging.getLogger(__name__)

class BalanceValidator:
    """Validates token balances and liquidity requirements."""

    def __init__(
        self,
        web3_manager: Web3Manager,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize balance validator.

        Args:
            web3_manager: Web3Manager instance
            config: Optional configuration dictionary
        """
        self.web3_manager = web3_manager
        self.config = config or {}

        # Load security config
        security = self.config.get("security", {})
        self.min_liquidity = Decimal(str(security.get("min_liquidity", "10000")))

        logger.info(
            f"Balance validator initialized with "
            f"min liquidity: {self.min_liquidity}"
        )

    @with_retry(retries=3, delay=1.0)
    async def validate_eth_balance(
        self,
        required_amount: int,
        address: Optional[ChecksumAddress] = None
    ) -> bool:
        """
        Validate ETH balance meets required amount.

        Args:
            required_amount: Required amount in wei
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            True if balance is sufficient

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        balance = await self.web3_manager.get_balance(address)

        if balance < required_amount:
            logger.warning(
                f"Insufficient ETH balance. "
                f"Required: {required_amount} wei, "
                f"Available: {balance} wei"
            )
            return False

        return True

    @with_retry(retries=3, delay=1.0)
    async def validate_token_balance(
        self,
        token_address: ChecksumAddress,
        required_amount: int,
        address: Optional[ChecksumAddress] = None
    ) -> bool:
        """
        Validate token balance meets required amount.

        Args:
            token_address: Token contract address
            required_amount: Required token amount
            address: Optional address to check. Uses wallet address if not provided.

        Returns:
            True if balance is sufficient

        Raises:
            ValueError: If no address provided and no wallet configured
        """
        balance = await self.web3_manager.get_token_balance(
            token_address=token_address,
            address=address
        )

        if balance < required_amount:
            logger.warning(
                f"Insufficient token balance for {token_address}. "
                f"Required: {required_amount}, "
                f"Available: {balance}"
            )
            return False

        return True

    @with_retry(retries=3, delay=1.0)
    async def validate_pool_liquidity(
        self,
        pool_address: ChecksumAddress,
        token_address: ChecksumAddress
    ) -> bool:
        """
        Validate pool has sufficient liquidity.

        Args:
            pool_address: Pool contract address
            token_address: Token to check liquidity for

        Returns:
            True if liquidity is sufficient
        """
        balance = await self.web3_manager.get_token_balance(
            token_address=token_address,
            address=pool_address
        )

        min_liquidity_wei = self.web3_manager.w3.to_wei(
            self.min_liquidity,
            "ether"
        )

        if balance < min_liquidity_wei:
            logger.warning(
                f"Insufficient pool liquidity for {token_address} "
                f"in pool {pool_address}. "
                f"Required: {min_liquidity_wei} wei, "
                f"Available: {balance} wei"
            )
            return False

        return True

    async def close(self):
        """Clean up resources."""
        pass

async def create_balance_validator(
    web3_manager: Web3Manager,
    config: Optional[Dict[str, Any]] = None
) -> BalanceValidator:
    """
    Create a new balance validator.

    Args:
        web3_manager: Web3Manager instance
        config: Optional configuration dictionary

    Returns:
        BalanceValidator instance
    """
    return BalanceValidator(
        web3_manager=web3_manager,
        config=config
    )
