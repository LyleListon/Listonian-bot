"""
Web3 interaction layer.

This module provides:
1. Provider management with fallback
2. Contract interactions
3. Transaction handling
4. Gas estimation
"""

from .web3 import (
    Web3Manager,
    Web3Error,
    get_web3_manager
)

__all__ = [
    'Web3Manager',
    'Web3Error',
    'get_web3_manager'
]
