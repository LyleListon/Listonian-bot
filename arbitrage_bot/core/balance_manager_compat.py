"""
Backward compatibility wrapper for BalanceManager.

This module provides a compatibility layer that maintains the original BalanceManager
interface while using the new UnifiedBalanceManager implementation internally.
"""

import logging
import asyncio
import warnings
from typing import Dict, Any, Optional
from decimal import Decimal

from .unified_balance_manager import UnifiedBalanceManager

logger = logging.getLogger(__name__)


class BalanceManager:
    """
    Compatibility wrapper for the original BalanceManager.

    This class maintains the original BalanceManager interface but delegates all
    functionality to the new UnifiedBalanceManager implementation.
    """

    _instance = None

    def __init__(self, web3_manager, dex_manager, config: Dict[str, Any]):
        """Initialize balance manager compatibility wrapper."""
        warnings.warn(
            "BalanceManager is deprecated and will be removed in a future release. "
            "Please use UnifiedBalanceManager instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Store parameters for later initialization of the unified manager
        self.web3_manager = web3_manager
        self.dex_manager = dex_manager
        self.config = config

        # Initialize the unified manager when first needed
        self._unified_manager = None

        # For compatibility with the old interface
        self.balances = {}
        self.running = False
        self._tasks = set()
        self._shutdown_event = asyncio.Event()

        logger.info("Creating BalanceManager compatibility wrapper")

    async def _ensure_unified_manager(self):
        """Ensure the unified manager is initialized."""
        if self._unified_manager is None:
            from .unified_balance_manager import create_unified_balance_manager

            self._unified_manager = await create_unified_balance_manager(
                self.web3_manager, self.dex_manager, self.config
            )

    @classmethod
    async def get_instance(
        cls,
        web3_manager: Optional = None,
        dex_manager: Optional = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> "BalanceManager":
        """Get or create singleton instance."""
        if not cls._instance:
            if not all([web3_manager, dex_manager, config]):
                raise ValueError("Required parameters missing for initialization")
            cls._instance = cls(web3_manager, dex_manager, config)
            logger.info("BalanceManager compatibility wrapper created successfully")
            # Start balance updates in a task to avoid blocking
            asyncio.create_task(cls._instance.start())
        return cls._instance

    async def start(self):
        """Start balance updates."""
        await self._ensure_unified_manager()
        await self._unified_manager.start()
        self.running = True
        logger.info("Balance manager started via compatibility wrapper")

    async def stop(self):
        """Stop balance updates."""
        if self._unified_manager:
            await self._unified_manager.stop()
        self.running = False
        logger.info("Balance manager stopped via compatibility wrapper")

    async def get_balance(self, token_symbol: str) -> Optional[int]:
        """Get balance for a token."""
        await self._ensure_unified_manager()
        balance = await self._unified_manager.get_balance(token_symbol)
        # Update local balances for compatibility
        if balance is not None:
            self.balances[token_symbol] = balance
        return balance

    def get_all_balances(self) -> Dict[str, int]:
        """Get all token balances."""
        if self._unified_manager:
            self.balances = self._unified_manager.get_all_balances_sync()
        return self.balances.copy()

    async def check_balance(self, token_symbol: str, amount: int) -> bool:
        """Check if balance is sufficient for amount."""
        await self._ensure_unified_manager()
        return await self._unified_manager.check_balance(token_symbol, amount)

    async def get_formatted_balance(self, token_symbol: str) -> Optional[Decimal]:
        """Get formatted balance with decimals."""
        await self._ensure_unified_manager()
        return await self._unified_manager.get_formatted_balance(token_symbol)


async def create_balance_manager(
    web3_manager, dex_manager, config: Dict[str, Any]
) -> BalanceManager:
    """Create and initialize a balance manager instance."""
    warnings.warn(
        "create_balance_manager is deprecated and will be removed in a future release. "
        "Please use create_unified_balance_manager instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return await BalanceManager.get_instance(web3_manager, dex_manager, config)


# For backward compatibility, we keep the original module structure
# but redirect to the new implementation
__all__ = ["BalanceManager", "create_balance_manager"]
