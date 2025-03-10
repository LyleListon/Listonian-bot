"""
Core Package

This package provides core functionality for:
- Web3 interactions
- DEX integrations
- Flash loan management
- MEV protection
"""

from .web3.web3_manager import create_web3_manager
from .web3.interfaces import Transaction, TransactionReceipt, Web3Client
from .web3.flashbots.flashbots_provider import create_flashbots_provider
from .web3.balance_validator import create_balance_validator
from .dex.dex_manager import DexManager, DexInfo
from .dex.path_finder import create_path_finder, PathFinder
from .unified_flash_loan_manager import create_unified_flash_loan_manager

__all__ = [
    'create_web3_manager',
    'Transaction',
    'TransactionReceipt',
    'Web3Client',
    'create_flashbots_provider',
    'create_balance_validator',
    'DexManager',
    'DexInfo',
    'create_path_finder',
    'PathFinder',
    'create_unified_flash_loan_manager'
]
