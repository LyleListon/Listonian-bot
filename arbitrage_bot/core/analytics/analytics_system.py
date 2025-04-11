"""
Analytics System Module

Provides analytics and monitoring for the arbitrage system.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
# from decimal import Decimal # Removed unused import
from datetime import datetime, timedelta

# from ...utils.async_manager import manager # Removed unused import
# from ..web3.web3_manager import Web3Manager # Removed unused import
from ..dex.dex_manager import DexManager

logger = logging.getLogger(__name__)


class AnalyticsSystem:
    """Manages analytics and monitoring for the arbitrage system."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the analytics system.

        Args:
            config: Optional configuration
        """
        self.config = config or {}
        self.initialized = False
        self.lock = asyncio.Lock()

        # Components will be set after initialization
        self.web3_manager = None
        self.dex_manager = None
        self.wallet_address = None

        # Analytics storage
        self._trade_history = []
        self._gas_usage = []
        self._profit_metrics = {}
        self._performance_metrics = {}

        # Cache settings
        self.metrics_ttl = int(self.config.get("metrics_ttl", 300))  # 5 minutes
        self._last_metrics_update = 0

    async def initialize(self) -> bool:
        """
        Initialize the analytics system.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize storage
            self._trade_history = []
            self._gas_usage = []
            self._profit_metrics = {}
            self._performance_metrics = {}

            self.initialized = True
            logger.info("Analytics system initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize analytics system: {e}")
            return False

    def set_dex_manager(self, dex_manager: DexManager):
        """Set the DEX manager instance."""
        self.dex_manager = dex_manager

    async def log_trade(self, trade_data: Dict[str, Any]):
        """Log a completed trade."""
        if not self.initialized:
            raise RuntimeError("Analytics system not initialized")

        async with self.lock:
            self._trade_history.append({**trade_data, "timestamp": datetime.utcnow()})
            await self._update_metrics()

    async def log_gas_usage(self, gas_data: Dict[str, Any]):
        """Log gas usage data."""
        if not self.initialized:
            raise RuntimeError("Analytics system not initialized")

        async with self.lock:
            self._gas_usage.append({**gas_data, "timestamp": datetime.utcnow()})
            await self._update_metrics()

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        if not self.initialized:
            raise RuntimeError("Analytics system not initialized")

        async with self.lock:
            current_time = asyncio.get_event_loop().time()
            if current_time - self._last_metrics_update > self.metrics_ttl:
                await self._update_metrics()
            return self._performance_metrics

    async def get_profit_metrics(self) -> Dict[str, Any]:
        """Get current profit metrics."""
        if not self.initialized:
            raise RuntimeError("Analytics system not initialized")

        async with self.lock:
            current_time = asyncio.get_event_loop().time()
            if current_time - self._last_metrics_update > self.metrics_ttl:
                await self._update_metrics()
            return self._profit_metrics

    async def _update_metrics(self):
        """Update all metrics."""
        try:
            # Update timestamp
            self._last_metrics_update = asyncio.get_event_loop().time()

            # Calculate performance metrics
            self._performance_metrics = await self._calculate_performance_metrics()

            # Calculate profit metrics
            self._profit_metrics = await self._calculate_profit_metrics()

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics."""
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)

        # Filter recent trades
        recent_trades = [
            trade for trade in self._trade_history if trade["timestamp"] > day_ago
        ]

        return {
            "trades_24h": len(recent_trades),
            "success_rate": self._calculate_success_rate(recent_trades),
            "avg_execution_time": self._calculate_avg_execution_time(recent_trades),
            "gas_efficiency": await self._calculate_gas_efficiency(),
        }

    async def _calculate_profit_metrics(self) -> Dict[str, Any]:
        """Calculate profit metrics."""
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)

        # Filter recent trades
        recent_trades = [
            trade for trade in self._trade_history if trade["timestamp"] > day_ago
        ]

        return {
            "total_profit_24h": sum(trade["profit"] for trade in recent_trades),
            "avg_profit_per_trade": self._calculate_avg_profit(recent_trades),
            "roi_24h": await self._calculate_roi(recent_trades),
            "profit_after_gas": self._calculate_profit_after_gas(recent_trades),
        }

    def _calculate_success_rate(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate trade success rate."""
        if not trades:
            return 0.0
        successful = sum(1 for trade in trades if trade.get("success", False))
        return successful / len(trades)

    def _calculate_avg_execution_time(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average trade execution time."""
        if not trades:
            return 0.0
        execution_times = [
            trade.get("execution_time", 0)
            for trade in trades
            if trade.get("execution_time") is not None
        ]
        return sum(execution_times) / len(execution_times) if execution_times else 0.0

    async def _calculate_gas_efficiency(self) -> float:
        """Calculate gas efficiency metric."""
        if not self._gas_usage:
            return 0.0

        total_gas = sum(usage["gas_used"] for usage in self._gas_usage)
        total_profit = sum(usage.get("profit", 0) for usage in self._gas_usage)

        return total_profit / total_gas if total_gas > 0 else 0.0

    def _calculate_avg_profit(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate average profit per trade."""
        if not trades:
            return 0.0
        profits = [trade.get("profit", 0) for trade in trades]
        return sum(profits) / len(profits)

    async def _calculate_roi(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate return on investment."""
        if not trades:
            return 0.0

        total_investment = sum(trade.get("amount_in", 0) for trade in trades)
        total_profit = sum(trade.get("profit", 0) for trade in trades)

        return total_profit / total_investment if total_investment > 0 else 0.0

    def _calculate_profit_after_gas(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate profit after gas costs."""
        if not trades:
            return 0.0

        total_profit = sum(trade.get("profit", 0) for trade in trades)
        total_gas_cost = sum(trade.get("gas_cost", 0) for trade in trades)

        return total_profit - total_gas_cost


async def create_analytics_system(
    config: Optional[Dict[str, Any]] = None,
) -> AnalyticsSystem:
    """
    Create and initialize an analytics system.

    Args:
        config: Optional configuration

    Returns:
        Initialized AnalyticsSystem instance
    """
    analytics = AnalyticsSystem(config)
    if not await analytics.initialize():
        raise RuntimeError("Failed to initialize analytics system")
    return analytics
