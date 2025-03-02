"""
Arbitrage Bot Core - Arbitrage Module

This module provides components for detecting, validating, and executing
arbitrage opportunities across decentralized exchanges.
"""

__version__ = "0.1.0"

# Export Protocol interfaces for public use
from .interfaces import (
    ArbitrageAnalytics,
    ArbitrageSystem,
    ExecutionManager,
    ExecutionStrategy,
    MarketDataProvider,
    OpportunityDetector,
    OpportunityDiscoveryManager,
    OpportunityValidator,
    TransactionMonitor,
)

# Export data models for public use
from .models import (
    ArbitrageOpportunity,
    ArbitrageRoute,
    DEXInfo,
    ExecutionResult,
    ExecutionStatus,
    PoolInfo,
    StrategyType,
    TokenAmount,
    TradeStep,
    TransactionDetails,
    TransactionStatus,
)

# Module initialization - Will be expanded as we develop additional components
# This is where we would register default implementations and adapters

__all__ = [
    # Interfaces
    "ArbitrageAnalytics",
    "ArbitrageSystem",
    "ExecutionManager",
    "ExecutionStrategy",
    "MarketDataProvider",
    "OpportunityDetector",
    "OpportunityDiscoveryManager",
    "OpportunityValidator",
    "TransactionMonitor",
    
    # Data models
    "ArbitrageOpportunity",
    "ArbitrageRoute",
    "DEXInfo",
    "ExecutionResult",
    "ExecutionStatus",
    "PoolInfo",
    "StrategyType",
    "TokenAmount",
    "TradeStep",
    "TransactionDetails",
    "TransactionStatus",
]

# Future enhancement: Add factory function for creating a complete arbitrage system
# Example:
# async def create_arbitrage_system(config: Dict[str, Any]) -> ArbitrageSystem:
#     """Create and configure an arbitrage system from the provided configuration."""
#     from .factory import create_arbitrage_system as factory_create
#     return await factory_create(config)