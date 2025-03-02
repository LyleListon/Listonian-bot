"""
DEPRECATED: This module has been moved to arbitrage_bot.core.flash_loan_manager.
"""
import warnings

from ...core.unified_flash_loan_manager import UnifiedFlashLoanManager, create_flash_loan_manager_sync
from ...core.flash_loan_manager import FlashLoanManager

warnings.warn(
    "arbitrage_bot.core.execution.flash_loan_manager is deprecated. "
    "Use arbitrage_bot.core.unified_flash_loan_manager instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ['FlashLoanManager', 'UnifiedFlashLoanManager']