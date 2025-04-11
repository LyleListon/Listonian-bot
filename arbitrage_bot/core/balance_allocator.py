"""
Balance Allocator Module

This module dynamically allocates trading amounts based on available wallet balance.
"""

import warnings

# Emit deprecation warning
warnings.warn(
    "This module is deprecated and will be removed in a future release. "
    "Please use arbitrage_bot.core.unified_balance_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import from compatibility module
from .balance_allocator_compat import BalanceAllocator, create_balance_allocator

# For backward compatibility, we re-export all names from the compatibility module
__all__ = ["BalanceAllocator", "create_balance_allocator"]
