"""
DEPRECATED: This module has been moved to arbitrage_bot.core.flash_loan_manager.
"""

import warnings
from ..flash_loan_manager import FlashLoanManager

warnings.warn(
    "arbitrage_bot.core.execution.flash_loan_manager is deprecated. "
    "Use arbitrage_bot.core.flash_loan_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['FlashLoanManager']