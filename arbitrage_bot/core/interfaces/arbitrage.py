"""Interfaces for arbitrage system components."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

from ..models.arbitrage import ArbitrageOpportunity, ExecutionResult

class OpportunityDetector(ABC):
    """Interface for opportunity detection components."""
    
    @abstractmethod
    async def detect_opportunities(
        self,
        market_condition: Dict[str, Any],
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Detect arbitrage opportunities."""
        pass

class OpportunityValidator(ABC):
    """Interface for opportunity validation components."""
    
    @abstractmethod
    async def validate_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: Dict[str, Any],
        **kwargs
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """Validate an arbitrage opportunity."""
        pass

class OpportunityDiscoveryManager(ABC):
    """Interface for opportunity discovery management."""
    
    @abstractmethod
    async def register_detector(
        self,
        detector: OpportunityDetector,
        detector_id: str
    ) -> None:
        """Register an opportunity detector."""
        pass
    
    @abstractmethod
    async def register_validator(
        self,
        validator: OpportunityValidator,
        validator_id: str
    ) -> None:
        """Register an opportunity validator."""
        pass
    
    @abstractmethod
    async def discover_opportunities(
        self,
        max_results: int = 10,
        min_profit_wei: int = 0,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Discover arbitrage opportunities."""
        pass

class ExecutionStrategy(ABC):
    """Interface for execution strategy components."""
    
    @abstractmethod
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        **kwargs
    ) -> ExecutionResult:
        """Execute an arbitrage opportunity."""
        pass

class ExecutionManager(ABC):
    """Interface for execution management."""
    
    @abstractmethod
    async def register_strategy(
        self,
        strategy: ExecutionStrategy,
        strategy_id: str
    ) -> None:
        """Register an execution strategy."""
        pass
    
    @abstractmethod
    async def register_monitor(
        self,
        monitor: 'TransactionMonitor',
        monitor_id: str
    ) -> None:
        """Register a transaction monitor."""
        pass
    
    @abstractmethod
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        strategy_id: str = "default",
        **kwargs
    ) -> ExecutionResult:
        """Execute an arbitrage opportunity."""
        pass
    
    @abstractmethod
    async def get_execution_status(
        self,
        execution_id: str
    ) -> 'ExecutionStatus':
        """Get the status of an execution."""
        pass

class ArbitrageSystem(ABC):
    """Interface for the complete arbitrage system."""
    
    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Whether the system is currently running."""
        pass
    
    @property
    @abstractmethod
    def uptime_seconds(self) -> float:
        """Number of seconds the system has been running."""
        pass
    
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
        self,
        max_results: int = 10,
        min_profit_eth: float = 0.0,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Discover arbitrage opportunities."""
        pass
    
    @abstractmethod
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        strategy_id: str = "default",
        **kwargs
    ) -> ExecutionResult:
        """Execute an arbitrage opportunity."""
        pass
    
    @abstractmethod
    async def get_performance_metrics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Get system performance metrics."""
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