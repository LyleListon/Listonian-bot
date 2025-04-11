"""
Distribution Manager Module

Manages profit distribution and balance management.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from decimal import Decimal

from ..web3.web3_manager import Web3Manager

logger = logging.getLogger(__name__)


class DistributionManager:
    """Manages profit distribution and balance tracking."""

    def __init__(
        self, web3_manager: Web3Manager, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the distribution manager.

        Args:
            web3_manager: Web3 manager instance
            config: Optional configuration
        """
        self.web3_manager = web3_manager
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()
        self._monitor_task = None

        # Distribution settings
        self.profit_recipient = self.config.get("wallet", {}).get("profit_recipient")
        self.min_balance = Decimal(
            str(self.config.get("min_balance", 0.1))
        )  # Minimum 0.1 ETH
        self.gas_buffer = Decimal(
            str(self.config.get("gas_buffer", 0.05))
        )  # 0.05 ETH buffer for gas

        # Balance tracking
        self._last_balance = Decimal("0")
        self._last_balance_check = 0
        self._balance_check_interval = 60  # Check balance every minute

    async def initialize(self) -> bool:
        """
        Initialize the distribution manager.

        Returns:
            True if initialization successful
        """
        try:
            # Validate web3_manager
            if not self.web3_manager or not hasattr(self.web3_manager, "get_balance"):
                raise ValueError(
                    "web3_manager must be provided and implement get_balance method"
                )

            # Verify profit recipient
            if not self.profit_recipient:
                self.profit_recipient = self.web3_manager.wallet_address
                logger.info(
                    "Using wallet address as profit recipient: %s",
                    self.profit_recipient,
                )

            # Get initial balance
            balance = await self.web3_manager.get_balance()
            self._last_balance = Decimal(str(balance))
            self._last_balance_check = asyncio.get_event_loop().time()

            # Start balance monitoring
            self._monitor_task = asyncio.create_task(self._monitor_balance())

            self.initialized = True
            logger.info("Distribution manager initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize distribution manager: {e}")
            return False

    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None
            self.initialized = False
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def _monitor_balance(self):
        """Monitor wallet balance."""
        while True:
            try:
                await asyncio.sleep(self._balance_check_interval)
                await self._check_balance()
            except asyncio.CancelledError:
                logger.info("Balance monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Error monitoring balance: {e}")
                await asyncio.sleep(60)  # Longer delay on error

    async def _check_balance(self):
        """Check current balance and update tracking."""
        async with self.lock:
            try:
                current_time = asyncio.get_event_loop().time()
                if (
                    current_time - self._last_balance_check
                    < self._balance_check_interval
                ):
                    return

                balance = await self.web3_manager.get_balance()
                self._last_balance = Decimal(str(balance))
                self._last_balance_check = current_time

                # Log if balance is low
                if self._last_balance < self.min_balance:
                    logger.warning(
                        f"Low balance: {self._last_balance} ETH "
                        f"(minimum: {self.min_balance} ETH)"
                    )
            except Exception as e:
                logger.error(f"Failed to check balance: {e}")
                raise  # Re-raise for proper error handling

    async def get_balance(self) -> Decimal:
        """
        Get current balance.

        Returns:
            Current balance in ETH
        """
        if not self.initialized:
            raise RuntimeError("Distribution manager not initialized")

        # Check if we need to update balance
        current_time = asyncio.get_event_loop().time()
        if current_time - self._last_balance_check >= self._balance_check_interval:
            await self._check_balance()

        return self._last_balance

    async def has_sufficient_balance(self, required_amount: Decimal) -> bool:
        """
        Check if we have sufficient balance.

        Args:
            required_amount: Required amount in ETH

        Returns:
            True if balance is sufficient
        """
        if not self.initialized:
            raise RuntimeError("Distribution manager not initialized")

        balance = await self.get_balance()
        return balance >= (required_amount + self.gas_buffer)

    async def distribute_profits(self, amount: Decimal) -> bool:
        """
        Distribute profits to recipient.

        Args:
            amount: Amount to distribute in ETH

        Returns:
            True if distribution successful
        """
        if not self.initialized:
            raise RuntimeError("Distribution manager not initialized")

        try:
            # Check if we have enough balance
            if not await self.has_sufficient_balance(amount):
                logger.warning(
                    f"Insufficient balance for distribution: {amount} ETH "
                    f"(current: {self._last_balance} ETH)"
                )
                return False

            # Create transaction
            tx = {
                "to": self.profit_recipient,
                "value": self.web3_manager.w3.to_wei(amount, "ether"),
                "from": self.web3_manager.wallet_address,
            }

            # Send transaction
            tx_hash = await self.web3_manager.send_transaction(tx)
            logger.info(
                f"Distributed {amount} ETH to {self.profit_recipient} "
                f"(tx: {tx_hash})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to distribute profits: {e}")
            return False


async def create_distribution_manager(
    web3_manager: Web3Manager, config: Optional[Dict[str, Any]] = None
) -> DistributionManager:
    """
    Create and initialize a distribution manager.

    Args:
        web3_manager: Web3 manager instance
        config: Optional configuration

    Returns:
        Initialized DistributionManager instance
    """
    if not web3_manager:
        raise ValueError("web3_manager is required")

    if not hasattr(web3_manager, "get_balance"):
        raise ValueError("web3_manager must implement get_balance method")

    manager = DistributionManager(web3_manager, config)
    success = await manager.initialize()
    if not success:
        await manager.cleanup()  # Ensure proper cleanup on failure
        raise RuntimeError("Failed to initialize distribution manager")
    return manager
