"""Base implementation of arbitrage system."""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional

from ..interfaces.arbitrage import (
    ArbitrageSystem, OpportunityDiscoveryManager, ExecutionManager
)
from ..interfaces.monitoring import (
    ArbitrageAnalytics, MarketDataProvider
)
from ..models.arbitrage import ArbitrageOpportunity, ExecutionResult
from ..models.types import ArbitrageSettings

logger = logging.getLogger(__name__)

class BaseArbitrageSystem(ArbitrageSystem):
    """Base implementation of arbitrage system."""
    
    def __init__(
        self,
        discovery_manager: OpportunityDiscoveryManager,
        execution_manager: ExecutionManager,
        analytics_manager: ArbitrageAnalytics,
        market_data_provider: MarketDataProvider,
        config: Dict[str, Any]
    ):
        """Initialize the arbitrage system."""
        self.discovery_manager = discovery_manager
        self.execution_manager = execution_manager
        self.analytics_manager = analytics_manager
        self.market_data_provider = market_data_provider
        
        # Parse config
        arbitrage_config = config.get('arbitrage', {})
        self.settings = ArbitrageSettings(**arbitrage_config)
        
        # Initialize state
        self._running = False
        self._start_time = 0.0
        self._lock = asyncio.Lock()
        self._market_condition = None
        
        logger.info("Arbitrage system initialized with settings: %s", self.settings)
    
    @property
    def is_running(self) -> bool:
        """Whether the system is currently running."""
        return self._running
    
    @property
    def uptime_seconds(self) -> float:
        """Number of seconds the system has been running."""
        if not self._running:
            return 0.0
        return time.time() - self._start_time
    
    async def start(self) -> None:
        """Start the arbitrage system."""
        async with self._lock:
            if self._running:
                logger.warning("Arbitrage system already running")
                return
            
            try:
                # Start market data provider
                await self.market_data_provider.start_monitoring(
                    update_interval_seconds=self.settings.discovery_interval_seconds
                )
                
                # Register market update callback
                await self.market_data_provider.register_market_update_callback(
                    self._handle_market_update
                )
                
                self._running = True
                self._start_time = time.time()
                logger.info("Arbitrage system started")
                
            except Exception as e:
                logger.error("Failed to start arbitrage system: %s", str(e))
                await self.stop()
                raise
    
    async def stop(self) -> None:
        """Stop the arbitrage system."""
        async with self._lock:
            if not self._running:
                logger.warning("Arbitrage system not running")
                return
            
            try:
                # Stop market data provider
                await self.market_data_provider.stop_monitoring()
                
                self._running = False
                logger.info("Arbitrage system stopped")
                
            except Exception as e:
                logger.error("Error stopping arbitrage system: %s", str(e))
                raise
    
    async def discover_opportunities(
        self,
        max_results: int = 10,
        min_profit_eth: float = 0.0,
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """Discover arbitrage opportunities."""
        if not self._running:
            raise RuntimeError("Arbitrage system not running")
        
        try:
            # Convert ETH to Wei
            min_profit_wei = int(min_profit_eth * 10**18)
            
            # Get opportunities
            opportunities = await self.discovery_manager.discover_opportunities(
                max_results=max_results,
                min_profit_wei=min_profit_wei,
                **kwargs
            )
            
            # Record opportunities
            for opp in opportunities:
                await self.analytics_manager.record_opportunity(opp)
            
            return opportunities
            
        except Exception as e:
            logger.error("Error discovering opportunities: %s", str(e))
            return []
    
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        strategy_id: str = "default",
        **kwargs
    ) -> ExecutionResult:
        """Execute an arbitrage opportunity."""
        if not self._running:
            raise RuntimeError("Arbitrage system not running")
        
        try:
            # Execute opportunity
            result = await self.execution_manager.execute_opportunity(
                opportunity=opportunity,
                strategy_id=strategy_id,
                **kwargs
            )
            
            # Record execution
            await self.analytics_manager.record_execution(result)
            
            return result
            
        except Exception as e:
            logger.error("Error executing opportunity: %s", str(e))
            raise
    
    async def get_performance_metrics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Get system performance metrics."""
        return await self.analytics_manager.get_performance_metrics(
            time_period_days=time_period_days
        )
    
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        """Get recent opportunities."""
        return await self.analytics_manager.get_recent_opportunities(
            max_results=max_results,
            min_profit_eth=min_profit_eth
        )
    
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List[ExecutionResult]:
        """Get recent executions."""
        return await self.analytics_manager.get_recent_executions(
            max_results=max_results
        )
    
    async def _handle_market_update(
        self,
        market_condition: Dict[str, Any]
    ) -> None:
        """Handle market condition updates."""
        self._market_condition = market_condition
        
        if self.settings.auto_execute:
            try:
                # Discover opportunities
                opportunities = await self.discover_opportunities(
                    max_results=self.settings.max_opportunities_per_cycle,
                    min_profit_eth=self.settings.min_profit_threshold_eth
                )
                
                # Execute valid opportunities
                for opp in opportunities:
                    if opp.confidence_score >= self.settings.min_confidence_threshold:
                        await self.execute_opportunity(opp)
                    
            except Exception as e:
                logger.error("Error in market update handler: %s", str(e))