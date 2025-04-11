"""
Arbitrage Core Module

This module provides core arbitrage functionality including discovery,
execution, analytics, and market data management.
"""

from .base_system import BaseArbitrageSystem
from .discovery_manager import DiscoveryManager
from .execution_manager import EnhancedExecutionManager
from .analytics_manager import AnalyticsManager
from .interfaces import ExecutionManager # Removed MarketDataProvider
from .market_data_provider import MarketDataProvider
from .discovery.integration import integrate_dex_discovery, setup_dex_discovery
from .discovery import (
    DEXDiscoveryManager,
    create_dex_discovery_manager,
    DEXInfo,
    DEXProtocolType,
)

__all__ = [
    "BaseArbitrageSystem",
    "DiscoveryManager",
    "ExecutionManager",
    "EnhancedExecutionManager",
    "AnalyticsManager",
    "MarketDataProvider",
    "integrate_dex_discovery",
    "setup_dex_discovery",
    "DEXDiscoveryManager",
    "create_dex_discovery_manager",
    "DEXInfo",
    "DEXProtocolType",
]
