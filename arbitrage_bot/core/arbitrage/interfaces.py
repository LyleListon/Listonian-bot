"""
Arbitrage System Interfaces

This module defines the interfaces and protocols that different components
of the arbitrage system must implement. These interfaces ensure clean separation
of concerns and enable easy testing and mocking.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class OpportunityDetector(Protocol):
    """
    Protocol for detecting arbitrage opportunities.
    Implementations are responsible for finding potential profit opportunities.
    """
    
    async def detect_opportunities(
        self, 
        market_condition: Dict[str, Any], 
        **kwargs
    ) -> List['ArbitrageOpportunity']:
        """
        Detect arbitrage opportunities based on current market conditions.
        
        Args:
            market_condition: Current market state and prices
            **kwargs: Additional parameters
            
        Returns:
            List of detected opportunities
        """
        ...


@runtime_checkable
class OpportunityValidator(Protocol):
    """
    Protocol for validating arbitrage opportunities.
    Implementations are responsible for validating opportunities before execution.
    """
    
    async def validate_opportunity(
        self, 
        opportunity: 'ArbitrageOpportunity', 
        market_condition: Dict[str, Any], 
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Validate an arbitrage opportunity.
        
        Args:
            opportunity: The opportunity to validate
            market_condition: Current market state and prices
            **kwargs: Additional parameters
            
        Returns:
            Tuple of (is_valid, error_message, confidence_score)
            is_valid: Whether the opportunity is valid
            error_message: Error message if not valid, None otherwise
            confidence_score: Confidence score (0-1) if valid, None otherwise
        """
        ...


@runtime_checkable
class OpportunityDiscoveryManager(Protocol):
    """
    Protocol for managing opportunity discovery.
    Implementations are responsible for coordinating detectors and validators.
    """
    
    async def register_detector(
        self, 
        detector: OpportunityDetector, 
        detector_id: str
    ) -> None:
        """
        Register an opportunity detector.
        
        Args:
            detector: The detector to register
            detector_id: Unique identifier for the detector
        """
        ...
    
    async def register_validator(
        self, 
        validator: OpportunityValidator, 
        validator_id: str
    ) -> None:
        """
        Register an opportunity validator.
        
        Args:
            validator: The validator to register
            validator_id: Unique identifier for the validator
        """
        ...
    
    async def discover_opportunities(
        self, 
        max_results: int = 10, 
        min_profit_wei: int = 0, 
        **kwargs
    ) -> List['ArbitrageOpportunity']:
        """
        Discover arbitrage opportunities.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_wei: Minimum profit threshold in wei
            **kwargs: Additional parameters
            
        Returns:
            List of discovered opportunities
        """
        ...


@runtime_checkable
class ExecutionStrategy(Protocol):
    """
    Protocol for executing arbitrage opportunities.
    Implementations are responsible for different execution strategies.
    """
    
    async def execute_opportunity(
        self, 
        opportunity: 'ArbitrageOpportunity', 
        **kwargs
    ) -> 'ExecutionResult':
        """
        Execute an arbitrage opportunity.
        
        Args:
            opportunity: The opportunity to execute
            **kwargs: Additional parameters
            
        Returns:
            Result of the execution
        """
        ...


@runtime_checkable
class TransactionMonitor(Protocol):
    """
    Protocol for monitoring blockchain transactions.
    Implementations are responsible for tracking transaction status.
    """
    
    async def monitor_transaction(
        self, 
        transaction_hash: str, 
        **kwargs
    ) -> 'TransactionStatus':
        """
        Monitor a blockchain transaction.
        
        Args:
            transaction_hash: Hash of the transaction to monitor
            **kwargs: Additional parameters
            
        Returns:
            Current status of the transaction
        """
        ...


@runtime_checkable
class ExecutionManager(Protocol):
    """
    Protocol for managing opportunity execution.
    Implementations are responsible for coordinating execution strategies.
    """
    
    async def register_strategy(
        self, 
        strategy: ExecutionStrategy, 
        strategy_id: str
    ) -> None:
        """
        Register an execution strategy.
        
        Args:
            strategy: The strategy to register
            strategy_id: Unique identifier for the strategy
        """
        ...
    
    async def register_monitor(
        self, 
        monitor: TransactionMonitor, 
        monitor_id: str
    ) -> None:
        """
        Register a transaction monitor.
        
        Args:
            monitor: The monitor to register
            monitor_id: Unique identifier for the monitor
        """
        ...
    
    async def execute_opportunity(
        self, 
        opportunity: 'ArbitrageOpportunity',
        strategy_id: str = "default", 
        **kwargs
    ) -> 'ExecutionResult':
        """
        Execute an arbitrage opportunity.
        
        Args:
            opportunity: The opportunity to execute
            strategy_id: ID of the strategy to use
            **kwargs: Additional parameters
            
        Returns:
            Result of the execution
        """
        ...
    
    async def get_execution_status(
        self, 
        execution_id: str
    ) -> 'ExecutionStatus':
        """
        Get the status of an execution.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Current status of the execution
        """
        ...


@runtime_checkable
class ArbitrageAnalytics(Protocol):
    """
    Protocol for analytics and performance tracking.
    Implementations are responsible for recording and analyzing performance.
    """
    
    async def record_opportunity(
        self, 
        opportunity: 'ArbitrageOpportunity'
    ) -> None:
        """
        Record an arbitrage opportunity.
        
        Args:
            opportunity: The opportunity to record
        """
        ...
    
    async def record_execution(
        self, 
        execution_result: 'ExecutionResult'
    ) -> None:
        """
        Record an execution result.
        
        Args:
            execution_result: The execution result to record
        """
        ...
    
    async def get_performance_metrics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Args:
            time_period_days: Time period in days to calculate metrics for
            
        Returns:
            Dictionary of performance metrics
        """
        ...
    
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List['ArbitrageOpportunity']:
        """
        Get recent arbitrage opportunities.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH
            
        Returns:
            List of recent opportunities
        """
        ...
    
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List['ExecutionResult']:
        """
        Get recent execution results.
        
        Args:
            max_results: Maximum number of executions to return
            
        Returns:
            List of recent executions
        """
        ...


@runtime_checkable
class MarketDataProvider(Protocol):
    """
    Protocol for providing market data.
    Implementations are responsible for fetching and caching market data.
    """
    
    async def get_current_market_condition(
        self
    ) -> Dict[str, Any]:
        """
        Get the current market condition.
        
        Returns:
            Current market state and prices
        """
        ...
    
    async def register_market_update_callback(
        self,
        callback: callable
    ) -> None:
        """
        Register a callback for market updates.
        
        Args:
            callback: Function to call when market updates occur
        """
        ...
    
    async def start_monitoring(
        self,
        update_interval_seconds: float = 60.0
    ) -> None:
        """
        Start monitoring market conditions.
        
        Args:
            update_interval_seconds: Time between updates in seconds
        """
        ...
    
    async def stop_monitoring(
        self
    ) -> None:
        """
        Stop monitoring market conditions.
        """
        ...


@runtime_checkable
class ArbitrageSystem(Protocol):
    """
    Protocol for the main arbitrage system.
    Implementations are responsible for integrating all components.
    """
    
    @property
    def is_running(self) -> bool:
        """
        Check if the system is running.
        
        Returns:
            True if the system is running, False otherwise
        """
        ...
    
    @property
    def uptime_seconds(self) -> float:
        """
        Get the system uptime in seconds.
        
        Returns:
            System uptime in seconds
        """
        ...
    
    async def start(self) -> None:
        """
        Start the arbitrage system.
        """
        ...
    
    async def stop(self) -> None:
        """
        Stop the arbitrage system.
        """
        ...
    
    async def discover_opportunities(
        self,
        max_results: int = 10,
        min_profit_eth: float = 0.0,
        **kwargs
    ) -> List['ArbitrageOpportunity']:
        """
        Discover arbitrage opportunities.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH
            **kwargs: Additional parameters
            
        Returns:
            List of discovered opportunities
        """
        ...
    
    async def execute_opportunity(
        self,
        opportunity: 'ArbitrageOpportunity',
        strategy_id: str = "default",
        **kwargs
    ) -> 'ExecutionResult':
        """
        Execute an arbitrage opportunity.
        
        Args:
            opportunity: The opportunity to execute
            strategy_id: ID of the strategy to use
            **kwargs: Additional parameters
            
        Returns:
            Result of the execution
        """
        ...
    
    async def get_opportunity_by_id(
        self,
        opportunity_id: str
    ) -> Optional['ArbitrageOpportunity']:
        """
        Get an opportunity by ID.
        
        Args:
            opportunity_id: ID of the opportunity
            
        Returns:
            The opportunity if found, None otherwise
        """
        ...
    
    async def get_execution_by_id(
        self,
        execution_id: str
    ) -> Optional['ExecutionResult']:
        """
        Get an execution result by ID.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            The execution result if found, None otherwise
        """
        ...
    
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List['ArbitrageOpportunity']:
        """
        Get recent arbitrage opportunities.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH
            
        Returns:
            List of recent opportunities
        """
        ...
    
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List['ExecutionResult']:
        """
        Get recent execution results.
        
        Args:
            max_results: Maximum number of executions to return
            
        Returns:
            List of recent executions
        """
        ...
    
    async def get_performance_metrics(
        self
    ) -> Dict[str, Any]:
        """
        Get performance metrics for the arbitrage system.
        
        Returns:
            Dictionary of performance metrics
        """
        ...


# Forward references for type hints
from .models import (
    ArbitrageOpportunity,
    ExecutionResult,
    ExecutionStatus,
    TransactionStatus
)