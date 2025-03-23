"""Listonian Arbitrage Bot.

A sophisticated cryptocurrency arbitrage system designed to identify and execute
profitable trading opportunities across decentralized exchanges (DEXs).
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from .core.arbitrage import (
    DiscoveryManager,
    ExecutionManager,
    AnalyticsManager,
    MarketDataProvider
)

from .utils.memory_bank import (
    initialize_memory_bank,
    MemoryBankMonitor,
    SchemaValidator
)

__version__ = '0.1.0'
__all__ = [
    'DiscoveryManager',
    'ExecutionManager',
    'AnalyticsManager',
    'MarketDataProvider',
    'initialize_memory_bank',
    'MemoryBankMonitor',
    'SchemaValidator'
]
