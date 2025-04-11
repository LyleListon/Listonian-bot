"""
Web3 Package

This package provides Web3 functionality with:
- Async Web3 initialization
- Connection management
- Transaction handling
- Gas price estimation
"""

from .web3_manager import Web3Manager, create_web3_manager

__all__ = ["Web3Manager", "create_web3_manager"]
