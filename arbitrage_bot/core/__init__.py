"""Core functionality for the arbitrage bot.

This module provides core components including market analysis
and arbitrage system implementations.
"""

from .errors import Web3Error
from .arbitrage import (
    DiscoveryManager,
    ExecutionManager,
    AnalyticsManager,
    MarketDataProvider
)

__all__ = [
    "Web3Error",
    "DiscoveryManager",
    "ExecutionManager",
    "AnalyticsManager",
    "MarketDataProvider"
]
