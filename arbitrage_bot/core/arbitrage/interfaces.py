"""
Arbitrage System Interfaces

This module defines the interfaces (abstract base classes) that specify
the contracts between different components of the arbitrage system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from .models import ArbitrageOpportunity, ExecutionResult, TransactionStatus


class OpportunityDetector(ABC):
    """Interface for components that detect arbitrage opportunities."""

    @abstractmethod
    async def detect_opportunities(
        self, market_condition: Dict[str, Any], **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Detect arbitrage opportunities.

        Args:
            market_condition: Current market state and prices
            **kwargs: Additional parameters

        Returns:
            List of detected opportunities
        """
        pass


class OpportunityValidator(ABC):
    """Interface for components that validate arbitrage opportunities."""

    @abstractmethod
    async def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: Dict[str, Any],
        **kwargs
    ) -> tuple[bool, Optional[str], Optional[float]]:
        """
        Validate an arbitrage opportunity.

        Args:
            opportunity: Opportunity to validate
            market_condition: Current market state
            **kwargs: Additional parameters

        Returns:
            Tuple of (is_valid, error_message, confidence_score)
        """
        pass


class OpportunityDiscoveryManager(ABC):
    """Interface for managing opportunity discovery."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the discovery manager."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    async def register_detector(
        self, detector: OpportunityDetector, detector_id: str
    ) -> None:
        """
        Register an opportunity detector.

        Args:
            detector: The detector to register
            detector_id: Unique identifier for the detector
        """
        pass

    @abstractmethod
    async def register_validator(
        self, validator: OpportunityValidator, validator_id: str
    ) -> None:
        """
        Register an opportunity validator.

        Args:
            validator: The validator to register
            validator_id: Unique identifier for the validator
        """
        pass

    @abstractmethod
    async def discover_opportunities(
        self,
        max_results: int = 10,
        min_profit_wei: int = 0,
        market_condition: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Discover arbitrage opportunities.

        Args:
            max_results: Maximum number of opportunities to return
            min_profit_wei: Minimum profit threshold in wei
            market_condition: Current market state
            **kwargs: Additional parameters

        Returns:
            List of discovered opportunities
        """
        pass


class ExecutionStrategy(ABC):
    """Interface for components that execute arbitrage opportunities."""

    @abstractmethod
    async def execute_opportunity(
        self, opportunity: ArbitrageOpportunity, **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.

        Args:
            opportunity: The opportunity to execute
            **kwargs: Additional parameters

        Returns:
            Result of the execution
        """
        pass


class TransactionMonitor(ABC):
    """Interface for components that monitor transaction status."""

    @abstractmethod
    async def monitor_transaction(self, transaction_hash: str) -> TransactionStatus:
        """
        Monitor a transaction's status.

        Args:
            transaction_hash: Hash of transaction to monitor

        Returns:
            Current status of the transaction
        """
        pass


class ExecutionManager(ABC):
    """Interface for managing arbitrage execution."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the execution manager."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    async def register_strategy(
        self, strategy: ExecutionStrategy, strategy_id: str
    ) -> None:
        """
        Register an execution strategy.

        Args:
            strategy: The strategy to register
            strategy_id: Unique identifier for the strategy
        """
        pass

    @abstractmethod
    async def register_monitor(
        self, monitor: TransactionMonitor, monitor_id: str
    ) -> None:
        """
        Register a transaction monitor.

        Args:
            monitor: The monitor to register
            monitor_id: Unique identifier for the monitor
        """
        pass

    @abstractmethod
    async def execute_opportunity(
        self, opportunity: ArbitrageOpportunity, strategy_id: str = "default", **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.

        Args:
            opportunity: The opportunity to execute
            strategy_id: ID of the strategy to use
            **kwargs: Additional parameters

        Returns:
            Result of the execution
        """
        pass


class ArbitrageAnalytics(ABC):
    """Interface for tracking arbitrage analytics."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the analytics manager."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    async def record_opportunity(self, opportunity: ArbitrageOpportunity) -> None:
        """
        Record an arbitrage opportunity.

        Args:
            opportunity: The opportunity to record
        """
        pass

    @abstractmethod
    async def record_execution(self, execution_result: ExecutionResult) -> None:
        """
        Record an execution result.

        Args:
            execution_result: The execution result to record
        """
        pass

    @abstractmethod
    async def get_performance_metrics(
        self, time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance metrics.

        Args:
            time_period_days: Time period to calculate metrics for

        Returns:
            Dictionary of performance metrics
        """
        pass

    @abstractmethod
    async def get_recent_opportunities(
        self, max_results: int = 100, min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        """
        Get recent arbitrage opportunities.

        Args:
            max_results: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH

        Returns:
            List of recent opportunities
        """
        pass

    @abstractmethod
    async def get_recent_executions(
        self, max_results: int = 100
    ) -> List[ExecutionResult]:
        """
        Get recent execution results.

        Args:
            max_results: Maximum number of executions to return

        Returns:
            List of recent executions
        """
        pass


class MarketDataProvider(ABC):
    """Interface for providing market data."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the market data provider."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    async def start_monitoring(self, update_interval_seconds: float = 60.0) -> None:
        """
        Start monitoring market conditions.

        Args:
            update_interval_seconds: Time between updates in seconds
        """
        pass

    @abstractmethod
    async def stop_monitoring(self) -> None:
        """Stop monitoring market conditions."""
        pass

    @abstractmethod
    async def get_current_market_condition(self) -> Dict[str, Any]:
        """
        Get the current market condition.

        Returns:
            Current market state and prices
        """
        pass

    @abstractmethod
    async def register_market_update_callback(self, callback: callable) -> None:
        """
        Register a callback for market updates.

        Args:
            callback: Function to call when market updates occur
        """
        pass


class ArbitrageSystem(ABC):
    """Interface for the main arbitrage system."""

    @abstractmethod
    async def start(self) -> None:
        """Start the arbitrage system."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the arbitrage system."""
        pass

    @abstractmethod
    async def discover_opportunities(
        self, max_results: int = 10, min_profit_eth: float = 0.0, **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Discover arbitrage opportunities.

        Args:
            max_results: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH
            **kwargs: Additional parameters

        Returns:
            List of discovered opportunities
        """
        pass

    @abstractmethod
    async def execute_opportunity(
        self, opportunity: ArbitrageOpportunity, strategy_id: str = "default", **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.

        Args:
            opportunity: The opportunity to execute
            strategy_id: ID of the strategy to use
            **kwargs: Additional parameters

        Returns:
            Result of the execution
        """
        pass

    @abstractmethod
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics.

        Returns:
            Dictionary of performance metrics
        """
        pass
