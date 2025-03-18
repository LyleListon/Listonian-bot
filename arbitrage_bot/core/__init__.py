"""
Core functionality for the arbitrage bot.

This package provides:
1. Web3 interaction layer
 (contract interactions, transactions, gas estimation)
2. Storage management
3. Cache management
4. System monitoring
5. Resource management
"""

from typing import Dict, Any
from .storage import get_db_pool
from .cache import get_cache

from .dex import (
    get_token_symbol,
    generate_pool_key,
    get_pool_data,
    calculate_price,
    validate_liquidity,
    BaseDEX,
    SwapBasedV3
)

from .web3 import (
    Web3Manager,
    load_contract,
    build_transaction,
    estimate_gas,
    setup_event_filter,
    batch_call,
    handle_web3_error,
    validate_address,
    get_web3_manager
)

__all__ = ['get_db_pool', 'get_cache', 'get_token_symbol', 'generate_pool_key', 'get_pool_data', 'calculate_price', 'validate_liquidity', 'BaseDEX', 'SwapBasedV3', 'Web3Manager', 'load_contract', 'build_transaction', 'estimate_gas', 'setup_event_filter', 'batch_call', 'handle_web3_error', 'validate_address', 'get_web3_manager']
