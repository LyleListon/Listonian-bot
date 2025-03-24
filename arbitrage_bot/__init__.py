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
    EnhancedExecutionManager,
    AnalyticsManager,
    MarketDataProvider
,
    BaseArbitrageSystem
)

from .core.ml import MLSystem
from .core.web3 import Web3Manager
from .core.flashbots import FlashbotsProvider
from .core.market import EnhancedMarketDataProvider
from .core.memory import MemoryManager
from .utils.async_manager import (
    async_init,
    manager as async_manager,
    run_with_async_context
)

__version__ = '0.1.0'
__all__ = [
    # Core arbitrage components
    'BaseArbitrageSystem',
    'DiscoveryManager',
    'EnhancedExecutionManager',
    'AnalyticsManager',
    'EnhancedMarketDataProvider',
    
    # Core systems
    'MLSystem',
    'Web3Manager',
    'FlashbotsProvider',
    'MemoryManager',
    
    # Async utilities
    'async_init',
    'async_manager',
    'run_with_async_context',
    
    # Version
    '__version__'
]
