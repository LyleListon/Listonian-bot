"""
Analytics Manager Implementation

This module provides the implementation of the ArbitrageAnalytics protocol.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from decimal import Decimal

from .interfaces import ArbitrageAnalytics
from .models import ArbitrageOpportunity, ExecutionResult

logger = logging.getLogger(__name__)

class AnalyticsManager(ArbitrageAnalytics):
    """
    Implementation of the ArbitrageAnalytics protocol.
    
    This class is responsible for tracking and analyzing arbitrage performance.
    """
    
    def __init__(self):
        """Initialize the analytics manager."""
        self._opportunities = []  # List of opportunities
        self._executions = []  # List of execution results
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Performance tracking
        self._total_profit_wei = 0
        self._total_gas_wei = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._opportunity_count = 0
        
        # Cache for quick lookups
        self._opportunity_cache = {}  # id -> opportunity
        self._execution_cache = {}  # id -> execution
    
    async def initialize(self) -> None:
        """Initialize the analytics manager."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing analytics manager")
            self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            # Save final metrics if needed
            self._initialized = False
            self._opportunities.clear()
            self._executions.clear()
            self._opportunity_cache.clear()
            self._execution_cache.clear()
    
    async def record_opportunity(
        self,
        opportunity: ArbitrageOpportunity
    ) -> None:
        """
        Record an arbitrage opportunity.
        
        Args:
            opportunity: The opportunity to record
        """
        async with self._lock:
            # Add to history
            self._opportunities.append(opportunity)
            self._opportunity_cache[opportunity.id] = opportunity
            
            # Update metrics
            self._opportunity_count += 1
            
            logger.debug(
                f"Recorded opportunity {opportunity.id} with "
                f"expected profit {opportunity.expected_profit_wei / 10**18:.6f} ETH"
            )
    
    async def record_execution(
        self,
        execution_result: ExecutionResult
    ) -> None:
        """
        Record an execution result.
        
        Args:
            execution_result: The execution result to record
        """
        async with self._lock:
            # Add to history
            self._executions.append(execution_result)
            self._execution_cache[execution_result.id] = execution_result
            
            # Update metrics
            if execution_result.is_successful:
                self._successful_executions += 1
                self._total_profit_wei += execution_result.actual_profit_wei
                self._total_gas_wei += execution_result.gas_cost_wei
            else:
                self._failed_executions += 1
            
            logger.debug(
                f"Recorded execution {execution_result.id} with "
                f"profit {execution_result.actual_profit_wei / 10**18:.6f} ETH"
            )
    
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
        async with self._lock:
            # Calculate time window
            end_time = datetime.now()
            start_time = end_time - timedelta(days=time_period_days)
            
            # Filter opportunities and executions in time window
            opportunities = [
                opp for opp in self._opportunities
                if start_time <= opp.timestamp <= end_time
            ]
            
            executions = [
                exec for exec in self._executions
                if start_time <= exec.timestamp <= end_time
            ]
            
            # Calculate metrics
            total_opportunities = len(opportunities)
            total_executions = len(executions)
            successful_executions = sum(1 for e in executions if e.is_successful)
            failed_executions = total_executions - successful_executions
            
            total_profit_wei = sum(
                e.actual_profit_wei for e in executions if e.is_successful
            )
            total_gas_wei = sum(
                e.gas_cost_wei for e in executions if e.is_successful
            )
            
            # Calculate averages
            avg_profit_per_trade = (
                total_profit_wei / successful_executions
                if successful_executions > 0 else 0
            )
            
            avg_gas_per_trade = (
                total_gas_wei / successful_executions
                if successful_executions > 0 else 0
            )
            
            # Calculate success rate
            success_rate = (
                successful_executions / total_executions * 100
                if total_executions > 0 else 0
            )
            
            return {
                "time_period_days": time_period_days,
                "total_opportunities": total_opportunities,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": success_rate,
                "total_profit_wei": str(total_profit_wei),
                "total_profit_eth": total_profit_wei / 10**18,
                "total_gas_wei": str(total_gas_wei),
                "total_gas_eth": total_gas_wei / 10**18,
                "avg_profit_per_trade_wei": str(avg_profit_per_trade),
                "avg_profit_per_trade_eth": avg_profit_per_trade / 10**18,
                "avg_gas_per_trade_wei": str(avg_gas_per_trade),
                "avg_gas_per_trade_eth": avg_gas_per_trade / 10**18,
                "net_profit_wei": str(total_profit_wei - total_gas_wei),
                "net_profit_eth": (total_profit_wei - total_gas_wei) / 10**18
            }
    
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        """
        Get recent arbitrage opportunities.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH
            
        Returns:
            List of recent opportunities
        """
        async with self._lock:
            # Convert ETH to wei
            min_profit_wei = int(min_profit_eth * 10**18)
            
            # Filter and sort opportunities
            filtered_opportunities = [
                opp for opp in self._opportunities
                if opp.expected_profit_wei >= min_profit_wei
            ]
            
            filtered_opportunities.sort(
                key=lambda x: x.timestamp,
                reverse=True
            )
            
            return filtered_opportunities[:max_results]
    
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List[ExecutionResult]:
        """
        Get recent execution results.
        
        Args:
            max_results: Maximum number of executions to return
            
        Returns:
            List of recent executions
        """
        async with self._lock:
            # Sort executions by timestamp
            sorted_executions = sorted(
                self._executions,
                key=lambda x: x.timestamp,
                reverse=True
            )
            
            return sorted_executions[:max_results]