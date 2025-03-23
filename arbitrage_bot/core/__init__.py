"""Core functionality for the arbitrage bot.

This module provides core components including ML capabilities,
market analysis, and arbitrage system implementations.
"""

class Web3Error(Exception):
    """Base exception class for Web3-related errors."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

from .ml import MLSystem, PriceValidator
from .arbitrage import (
    DiscoveryManager,
    ExecutionManager,
    AnalyticsManager,
    MarketDataProvider
)

__all__ = [
    "Web3Error",
    "MLSystem",
    "PriceValidator",
    "DiscoveryManager",
    "ExecutionManager",
    "AnalyticsManager",
    "MarketDataProvider"
]
