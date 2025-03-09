"""
Web3 Package

This package provides functionality for:
- Web3 interactions
- Contract interactions
- Transaction management
"""

from .web3_manager import create_web3_manager
from .interfaces import Transaction, TransactionReceipt, Web3Client
from .providers import EthClient

__all__ = [
    'create_web3_manager',
    'Transaction',
    'TransactionReceipt',
    'Web3Client',
    'EthClient'
]
