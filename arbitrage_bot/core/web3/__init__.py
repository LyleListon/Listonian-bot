"""
Web3 Integration Package

This package contains classes and utilities for interacting with the Ethereum blockchain,
including providers, clients, and interfaces.
"""

from .interfaces import Web3Client, Transaction

__all__ = [
    'Web3Client',
    'Transaction'
]
