"""
Backward compatibility wrapper for BalanceAllocator.

This module provides a compatibility layer that maintains the original BalanceAllocator
interface while using the new UnifiedBalanceManager implementation internally.
"""

import logging
import asyncio
import warnings
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal

from .unified_balance_manager import UnifiedBalanceManager

logger = logging.getLogger(__name__)

class BalanceAllocator:
    """
    Compatibility wrapper for the original BalanceAllocator.
    
    This class maintains the original BalanceAllocator interface but delegates all
    functionality to the new UnifiedBalanceManager implementation.
    """
    
    def __init__(self, web3_manager, config: Dict[str, Any]):
        """
        Initialize the BalanceAllocator compatibility wrapper.
        
        Args:
            web3_manager: Web3Manager instance for checking balances
            config: Configuration dictionary
        """
        warnings.warn(
            "BalanceAllocator is deprecated and will be removed in a future release. "
            "Please use UnifiedBalanceManager instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Store parameters for later initialization of the unified manager
        self.web3_manager = web3_manager
        self.config = config
        
        # Initialize the unified manager when first needed
        self._unified_manager = None
        
        # For compatibility with the old interface
        allocation_config = config.get('dynamic_allocation', {})
        self.enabled = allocation_config.get('enabled', True)
        self.min_percentage = allocation_config.get('min_percentage', 5)
        self.max_percentage = allocation_config.get('max_percentage', 50)
        self.absolute_min_eth = allocation_config.get('absolute_min_eth', 0.05)
        self.absolute_max_eth = allocation_config.get('absolute_max_eth', 10.0)
        self.concurrent_trades = allocation_config.get('concurrent_trades', 2)
        self.reserve_percentage = allocation_config.get('reserve_percentage', 10)
        
        logger.info("BalanceAllocator compatibility wrapper initialized")
        logger.info("Dynamic allocation enabled: %s", self.enabled)
    
    async def _ensure_unified_manager(self):
        """Ensure the unified manager is initialized."""
        if self._unified_manager is None:
            from .unified_balance_manager import create_unified_balance_manager
            self._unified_manager = await create_unified_balance_manager(
                self.web3_manager,
                None,  # No dex_manager for BalanceAllocator
                self.config
            )
    
    async def get_allocation_range(self, token_address: str) -> Tuple[int, int]:
        """
        Get the minimum and maximum allocation amounts for a token based on current balance.
        
        Args:
            token_address: Address of the token to allocate
            
        Returns:
            Tuple of (min_amount, max_amount) in wei
        """
        await self._ensure_unified_manager()
        return await self._unified_manager.get_allocation_range(token_address)
    
    async def adjust_amount_to_limits(self, token_address: str, amount: int) -> int:
        """
        Adjust an amount to be within the current allocation limits.
        
        Args:
            token_address: Address of the token
            amount: Proposed amount in wei
            
        Returns:
            Adjusted amount in wei within allocation limits
        """
        await self._ensure_unified_manager()
        return await self._unified_manager.adjust_amount_to_limits(token_address, amount)


async def create_balance_allocator(web3_manager, config: Dict[str, Any]) -> BalanceAllocator:
    """
    Create and initialize a BalanceAllocator instance.
    
    Args:
        web3_manager: Web3Manager instance
        config: Configuration dictionary
        
    Returns:
        Initialized BalanceAllocator instance
    """
    warnings.warn(
        "create_balance_allocator is deprecated and will be removed in a future release. "
        "Please use create_unified_balance_manager instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Create BalanceAllocator compatibility wrapper
    allocator = BalanceAllocator(web3_manager, config)
    
    return allocator


# For backward compatibility, we keep the original module structure
# but redirect to the new implementation
__all__ = ['BalanceAllocator', 'create_balance_allocator']