"""Blockchain interaction layer for the arbitrage bot."""

from .web3_manager import Web3Manager
from .providers.base import BaseProvider
from .providers.http import HttpProvider

__all__ = [
    'Web3Manager',
    'BaseProvider',
    'HttpProvider',
]

# Version of the blockchain package
__version__ = '1.0.0'

# Default retry count for blockchain operations
DEFAULT_RETRY_COUNT = 3

# Default timeout for transaction confirmation (seconds)
DEFAULT_TX_TIMEOUT = 120

# Default gas price buffer (multiply estimated gas by this factor)
GAS_BUFFER = 1.1