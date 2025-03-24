"""
Base Arbitrage System Implementation

This module provides the core implementation of the ArbitrageSystem protocol,
integrating all components of the arbitrage system.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .interfaces import (
    ArbitrageAnalytics,
    ArbitrageSystem,
    ExecutionManager,
    MarketDataProvider,
    OpportunityDiscoveryManager,
)
from .models import (
    ArbitrageOpportunity,
    ExecutionResult,
    ExecutionStatus,
)


logger = logging.getLogger(__name__)


class BaseArbitrageSystem(ArbitrageSystem):
    """
    Base implementation of the ArbitrageSystem protocol.
    
    This class integrates all components of the arbitrage system and provides
    the main API for discovering and executing arbitrage opportunities.
    """
    
    def __init__(
        self,
        discovery_manager: OpportunityDiscoveryManager,
        execution_manager: ExecutionManager,
        analytics_manager: ArbitrageAnalytics,
        market_data_provider: MarketDataProvider,
        config: Dict[str, Any],
    ):
        """
        Initialize the base arbitrage system.
        
        Args:
            discovery_manager: Manager for discovering opportunities
            execution_manager: Manager for executing opportunities
            analytics_manager: Manager for tracking analytics
            market_data_provider: Provider for market data
            config: System configuration
        """
        self._discovery_manager = discovery_manager
        self._execution_manager = execution_manager
        self._analytics_manager = analytics_manager
        self._market_data_provider = market_data_provider
        self._config = config
        
        # System state
        self._running = False
        self._start_time = None
        self._stop_time = None
        self._lock = asyncio.Lock()
        
        # Background tasks
        self._tasks = set()
        
        # Tracking state
        self._opportunity_cache = {}  # Opportunity ID -> Opportunity
        self._execution_cache = {}  # Execution ID -> Execution Result
        
        # Configure system from config
        self._configure()
    
    def _configure(self):
        """Configure the system from the configuration dictionary."""
        # Discovery configuration
        self._discovery_interval = self._config.get("discovery_interval_seconds", 10)
        self._max_opportunities = self._config.get("max_opportunities", 100)
        self._min_profit_wei = self._config.get("min_profit_wei", 0)
        
        # Execution configuration
        self._default_strategy = self._config.get("default_execution_strategy", "standard")
        self._auto_execute = self._config.get("auto_execute", False)
        self._max_concurrent_executions = self._config.get("max_concurrent_executions", 1)
        
        # Market data configuration
        self._market_update_interval = self._config.get("market_update_interval_seconds", 60)
        
        # Analytics configuration
        self._performance_window_days = self._config.get("performance_window_days", 30)
    
    @property
    def is_running(self) -> bool:
        """
        Check if the system is running.
        
        Returns:
            True if the system is running, False otherwise
        """
        return self._running
    
    @property
    def uptime_seconds(self) -> float:
        """
        Get the system uptime in seconds.
        
        Returns:
            System uptime in seconds
        """
        if not self._start_time:
            return 0
        
        end_time = self._stop_time or time.time()
        return end_time - self._start_time
    
    async def start(self) -> None:
        """
        Start the arbitrage system.
        
        This starts all components and begins monitoring for opportunities.
        """
        async with self._lock:
            if self._running:
                logger.warning("Arbitrage system is already running")
                return
            
            logger.info("Starting arbitrage system")
            
            try:
                # Initialize all components first
                await self._discovery_manager.initialize()
                await self._execution_manager.initialize()
                await self._analytics_manager.initialize()
                
                # Start market data provider
                await self._market_data_provider.start_monitoring(
                    update_interval_seconds=self._market_update_interval
                )
                
                # Register market update callback
                await self._market_data_provider.register_market_update_callback(
                    self._on_market_update
                )
                
                # Start discovery loop
                discovery_task = asyncio.create_task(self._discovery_loop())
                self._tasks.add(discovery_task)
                discovery_task.add_done_callback(self._tasks.discard)
                
                # Update state
                self._running = True
                self._start_time = time.time()
                self._stop_time = None
                
                logger.info("Arbitrage system started successfully")
            
            except Exception as e:
                logger.error(f"Failed to start arbitrage system: {e}", exc_info=True)
                await self._cleanup()
                raise
    
    async def stop(self) -> None:
        """
        Stop the arbitrage system.
        
        This stops all components and background tasks.
        """
        async with self._lock:
            if not self._running:
                logger.warning("Arbitrage system is not running")
                return
            
            logger.info("Stopping arbitrage system")
            await self._cleanup()
            
            # Update state
            self._running = False
            self._stop_time = time.time()
            
            logger.info("Arbitrage system stopped successfully")
    
    async def _cleanup(self):
        """Clean up resources when stopping the system."""
        # Cancel and wait for all tasks
        if self._tasks:
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
        
        # Stop components in reverse order
        try:
            await self._market_data_provider.stop_monitoring()
            await self._discovery_manager.cleanup()
            await self._execution_manager.cleanup()
            await self._analytics_manager.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    async def _discovery_loop(self):
        """Background task for discovering opportunities."""
        logger.info("Starting opportunity discovery loop")
        
        while True:
            try:
                # Get current market condition
                market_condition = await self._market_data_provider.get_current_market_condition()
                
                # Discover opportunities
                opportunities = await self._discovery_manager.discover_opportunities(
                    max_results=self._max_opportunities,
                    min_profit_wei=self._min_profit_wei,
                    market_condition=market_condition,
                )
                
                # Process opportunities
                await self._process_opportunities(opportunities)
                
                # Sleep until next discovery interval
                await asyncio.sleep(self._discovery_interval)
            
            except asyncio.CancelledError:
                logger.info("Opportunity discovery loop cancelled")
                break
            except Exception as e:
                logger.error(
                    f"Error in opportunity discovery loop: {e}", exc_info=True
                )
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _process_opportunities(self, opportunities: List[ArbitrageOpportunity]):
        """
        Process discovered opportunities.
        
        Args:
            opportunities: List of discovered opportunities
        """
        if not opportunities:
            return
        
        logger.info(f"Processing {len(opportunities)} discovered opportunities")
        
        # Update opportunity cache
        for opportunity in opportunities:
            self._opportunity_cache[opportunity.id] = opportunity
            
            # Record opportunity in analytics
            await self._analytics_manager.record_opportunity(opportunity)
            
            # Auto-execute if enabled
            if (
                self._auto_execute 
                and opportunity.is_profitable_after_gas
                and opportunity.confidence_score >= 0.8
            ):
                logger.info(
                    f"Auto-executing opportunity {opportunity.id} with "
                    f"expected profit {opportunity.expected_profit_after_gas / 10**18:.6f} ETH"
                )
                try:
                    result = await self.execute_opportunity(
                        opportunity, strategy_id=self._default_strategy
                    )
                    logger.info(f"Auto-execution result: {result}")
                except Exception as e:
                    logger.error(
                        f"Error auto-executing opportunity {opportunity.id}: {e}",
                        exc_info=True,
                    )
    
    async def _on_market_update(self, market_condition: Dict[str, Any]):
        """
        Handle market updates.
        
        Args:
            market_condition: Current market state
        """
        logger.debug("Received market update")
        # Trigger immediate opportunity discovery
        try:
            opportunities = await self._discovery_manager.discover_opportunities(
                max_results=self._max_opportunities,
                min_profit_wei=self._min_profit_wei,
                market_condition=market_condition,
            )
            await self._process_opportunities(opportunities)
        except Exception as e:
            logger.error(f"Error processing market update: {e}", exc_info=True)
    
    async def discover_opportunities(
        self,
        max_results: int = 10,
        min_profit_eth: float = 0.0,
        **kwargs
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
        if not self._running:
            logger.warning("Arbitrage system is not running")
        
        # Convert ETH to wei
        min_profit_wei = int(min_profit_eth * 10**18)
        
        # Get current market condition
        market_condition = await self._market_data_provider.get_current_market_condition()
        
        # Discover opportunities
        opportunities = await self._discovery_manager.discover_opportunities(
            max_results=max_results,
            min_profit_wei=min_profit_wei,
            market_condition=market_condition,
            **kwargs
        )
        
        # Update cache and record opportunities
        for opportunity in opportunities:
            self._opportunity_cache[opportunity.id] = opportunity
            await self._analytics_manager.record_opportunity(opportunity)
        
        return opportunities
    
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        strategy_id: str = "default",
        **kwargs
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
        if not self._running:
            logger.warning("Arbitrage system is not running")
        
        # Execute opportunity
        result = await self._execution_manager.execute_opportunity(
            opportunity=opportunity,
            strategy_id=strategy_id,
            **kwargs
        )
        
        # Update cache and record execution
        self._execution_cache[result.id] = result
        await self._analytics_manager.record_execution(result)
        
        return result
    
    async def get_opportunity_by_id(
        self,
        opportunity_id: str
    ) -> Optional[ArbitrageOpportunity]:
        """
        Get an opportunity by ID.
        
        Args:
            opportunity_id: ID of the opportunity
            
        Returns:
            The opportunity if found, None otherwise
        """
        return self._opportunity_cache.get(opportunity_id)
    
    async def get_execution_by_id(
        self,
        execution_id: str
    ) -> Optional[ExecutionResult]:
        """
        Get an execution result by ID.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            The execution result if found, None otherwise
        """
        return self._execution_cache.get(execution_id)
    
    async def get_recent_opportunities(
        self,
        limit: int = 100,
        min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        """
        Get recent opportunities.
        
        Args:
            limit: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH
            
        Returns:
            List of recent opportunities
        """
        min_profit_wei = int(min_profit_eth * 10**18)
        
        opportunities = sorted(
            [
                opp for opp in self._opportunity_cache.values()
                if opp.expected_profit_after_gas >= min_profit_wei
            ],
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        return opportunities[:limit]
    
    async def get_recent_executions(
        self,
        limit: int = 100
    ) -> List[ExecutionResult]:
        """
        Get recent executions.
        
        Args:
            limit: Maximum number of executions to return
            
        Returns:
            List of recent executions
        """
        executions = sorted(
            self._execution_cache.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        return executions[:limit]
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get system performance metrics.
        
        Returns:
            Dictionary containing performance metrics
        """
        return await self._analytics_manager.get_performance_metrics(
            window_days=self._performance_window_days
        )