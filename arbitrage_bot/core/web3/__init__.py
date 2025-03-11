"""
Web3 Integration Package

This package provides functionality for:
- Web3 client management
- Provider failover
- Contract interactions
- Transaction management
- Flashbots integration
"""

from .web3_manager import Web3Manager, create_web3_manager
from .web3_client_wrapper import Web3ClientWrapper
from .errors import Web3Error
from .interfaces import (
    Web3Client,
    Contract,
    ContractFunction,
    Transaction,
    TransactionReceipt,
    AccessList
)

__all__ = [
    'Web3Manager',
    'Web3Error',
    'create_web3_manager',
    'Web3ClientWrapper',
    'Web3Client',
    'Contract',
    'ContractFunction',
    'Transaction',
    'TransactionReceipt',
    'AccessList'
]
