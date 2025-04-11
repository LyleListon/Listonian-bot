"""
Flash Loan Integration Package

This package contains components for integrating with various flash loan providers
to enable capital-efficient arbitrage execution.
"""

from .interfaces import (
    FlashLoanProvider,
    FlashLoanCallback,
    FlashLoanResult,
    FlashLoanParams,
)
from .factory import create_flash_loan_provider

__all__ = [
    "FlashLoanProvider",
    "FlashLoanCallback",
    "FlashLoanResult",
    "FlashLoanParams",
    "create_flash_loan_provider",
]
