"""Balance manager for tracking and updating token balances."""

import warnings

# Emit deprecation warning
warnings.warn(
    "This module is deprecated and will be removed in a future release. "
    "Please use arbitrage_bot.core.unified_balance_manager instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Import from compatibility module
from .balance_manager_compat import BalanceManager, create_balance_manager

# For backward compatibility, we re-export all names from the compatibility module
__all__ = ["BalanceManager", "create_balance_manager"]
