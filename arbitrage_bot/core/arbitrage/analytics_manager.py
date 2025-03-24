"""
Analytics Manager Implementation

This module provides the implementation of the ArbitrageAnalytics protocol.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from decimal import Decimal
from pathlib import Path

from .interfaces import ArbitrageAnalytics
from .models import ArbitrageOpportunity, ExecutionResult
from ..memory.memory_bank import MemoryBank

logger = logging.getLogger(__name__)

class AnalyticsManager(ArbitrageAnalytics):
    """
    Implementation of the ArbitrageAnalytics protocol.
    
    This class is responsible for tracking and analyzing arbitrage performance.
    """
    
    def __init__(self, storage_dir: Path = Path("memory-bank")):
        """Initialize the analytics manager."""
        self._lock = asyncio.Lock()
        self._initialized = False
        
        # Initialize memory bank
        self._memory_bank = MemoryBank(
            storage_dir=storage_dir
        )
    
    async def initialize(self) -> None:
        """Initialize the analytics manager."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing analytics manager")
            await self._memory_bank.initialize()
            self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            # Cleanup memory bank
            await self._memory_bank.cleanup()
            self._initialized = False
    
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
            # Convert opportunity to dict
            opportunity_data = {
                'id': opportunity.id,
                'timestamp': opportunity.timestamp.isoformat(),
                'token_pair': opportunity.token_pair,
                'expected_profit_wei': str(opportunity.expected_profit_wei),
                'gas_cost_wei': str(opportunity.gas_cost_wei),
                'confidence_score': opportunity.confidence_score,
                'status': 'PENDING'
            }

            # Store in memory bank
            await self._memory_bank.add_trade(opportunity_data)
            
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
            # Convert execution result to dict
            execution_data = {
                'id': execution_result.id,
                'timestamp': execution_result.timestamp.isoformat(),
                'opportunity_id': execution_result.opportunity_id,
                'status': 'SUCCESSFUL' if execution_result.is_successful else 'FAILED',
                'actual_profit_wei': str(execution_result.actual_profit_wei),
                'gas_cost_wei': str(execution_result.gas_cost_wei),
                'tx_hash': execution_result.tx_hash,
                'error': execution_result.error if not execution_result.is_successful else None
            }

            # Store in memory bank
            await self._memory_bank.add_trade(execution_data)
            
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
            # Get daily stats from memory bank
            daily_stats = await self._memory_bank.get_daily_stats(
                days=time_period_days
            )
            return daily_stats[-1] if daily_stats else {}
    
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
            # Get recent trades from memory bank
            trades = await self._memory_bank.get_recent_trades(
                max_results=max_results
            )
            # Filter pending trades
            return [t for t in trades if t['status'] == 'PENDING' and 
                   float(t['expected_profit_wei']) / 10**18 >= min_profit_eth]
    
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
            # Get recent trades from memory bank
            trades = await self._memory_bank.get_recent_trades(
                max_results=max_results)
            return [t for t in trades if t['status'] in ('SUCCESSFUL', 'FAILED')]