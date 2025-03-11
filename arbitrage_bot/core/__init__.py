"""
Core Package

This package provides core functionality for:
- Web3 integration
- Flash loan management
- Contract interactions
- Transaction management
"""

from .web3 import Web3Manager, Web3Error, create_web3_manager

__all__ = [
    'Web3Manager',
    'Web3Error',
    'create_web3_manager'
]
