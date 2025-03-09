"""
Arbitrage Bot Package

This package provides functionality for:
- Flash loan arbitrage
- Flashbots integration
- MEV protection
- Multi-path arbitrage optimization
"""

from .core.web3.web3_manager import create_web3_manager
from .core.web3.interfaces import Transaction, TransactionReceipt, Web3Client
from .core.web3.flashbots.flashbots_provider import create_flashbots_provider
from .core.web3.balance_validator import create_balance_validator
from .core.dex.dex_manager import create_dex_manager, DexManager, DexInfo
from .core.dex.path_finder import create_path_finder, PathFinder
from .core.unified_flash_loan_manager import create_unified_flash_loan_manager
from .utils.config_loader import load_config, create_config_loader
from .utils.async_manager import manager, with_lock, with_semaphore, with_retry

__version__ = "0.1.0"

__all__ = [
    'create_web3_manager',
    'Transaction',
    'TransactionReceipt',
    'Web3Client',
    'create_flashbots_provider',
    'create_balance_validator',
    'create_dex_manager',
    'DexManager',
    'DexInfo',
    'create_path_finder',
    'PathFinder',
    'create_unified_flash_loan_manager',
    'load_config',
    'create_config_loader',
    'manager',
    'with_lock',
    'with_semaphore',
    'with_retry'
]
