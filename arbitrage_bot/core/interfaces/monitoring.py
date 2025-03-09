"""Interfaces for monitoring and analytics components."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable

from ..models.arbitrage import ArbitrageOpportunity, ExecutionResult
from ..models.enums import TransactionStatus

class TransactionMonitor(ABC):
    """Interface for transaction monitoring components."""
    
    @abstractmethod
    async def monitor_transaction(
        self,
        transaction_hash: str,
        **kwargs
    ) -> TransactionStatus:
        """Monitor a transaction's status."""
        pass

class ArbitrageAnalytics(ABC):
    """Interface for analytics components."""
    
    @abstractmethod
    async def record_opportunity(
        self,
        opportunity: ArbitrageOpportunity
    ) -> None:
        """Record an arbitrage opportunity."""
        pass
    
    @abstractmethod
    async def record_execution(
        self,
        execution_result: ExecutionResult
    ) -> None:
        """Record an execution result."""
        pass
    
    @abstractmethod
    async def get_performance_metrics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics."""
        pass
    
    @abstractmethod
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        """Get recent opportunities."""
        pass
    
    @abstractmethod
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List[ExecutionResult]:
        """Get recent executions."""
        pass

class MarketDataProvider(ABC):
    """Interface for market data providers."""
    
    @abstractmethod
    async def get_current_market_condition(
        self
    ) -> Dict[str, Any]:
        """Get the current market condition."""
        pass
    
    @abstractmethod
    async def register_market_update_callback(
        self,
        callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Register a callback for market updates."""
        pass
    
    @abstractmethod
    async def start_monitoring(
        self,
        update_interval_seconds: float = 60.0
    ) -> None:
        """Start monitoring market conditions."""
        pass
    
    @abstractmethod
    async def stop_monitoring(
        self
    ) -> None:
        """Stop monitoring market conditions."""
        pass