"""Core functionality for the arbitrage bot.

This module provides core components including ML capabilities,
market analysis, and arbitrage system implementations.
"""

from .errors import Web3Error

from .ml.model_interface import MLSystem
from .arbitrage import (
    DiscoveryManager,
    ExecutionManager,
    AnalyticsManager,
    MarketDataProvider
)

__all__ = [
    "Web3Error",
    "MLSystem",
    "DiscoveryManager",
    "ExecutionManager",
    "AnalyticsManager",
    "MarketDataProvider"
]
