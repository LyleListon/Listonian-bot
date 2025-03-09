"""
Analytics Manager

This module contains the implementation of the AnalyticsManager,
which tracks and analyzes arbitrage operations.
"""

import asyncio
import logging
import time
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple, DefaultDict
from collections import defaultdict

from .interfaces import (
    AnalyticsManager,
    ArbitrageAnalytics
)
from .models import (
    ArbitrageOpportunity,
    ExecutionResult,
    ExecutionStatus,
    OpportunityStatus
)

logger = logging.getLogger(__name__)


class BaseAnalyticsManager(AnalyticsManager):
    """
    Base implementation of the AnalyticsManager.
    
    This class manages the recording and analysis of arbitrage operations,
    including opportunities, executions, and performance metrics.
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the analytics manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Registered analytics components
        self._analytics_components: Dict[str, ArbitrageAnalytics] = {}
        
        # Configuration
        self.data_dir = self.config.get("analytics_data_dir", "data/analytics")
        self.auto_persist = self.config.get("auto_persist", True)
        self.persist_interval = self.config.get("persist_interval_seconds", 300)  # 5 minutes
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # In-memory metrics
        self._opportunity_count = 0
        self._execution_count = 0
        self._success_count = 0
        self._total_profit = 0
        self._total_gas_cost = 0
        self._execution_times: List[float] = []
        
        # Time-series data
        self._hourly_metrics: DefaultDict[str, Dict[str, Any]] = defaultdict(lambda: {
            "opportunities": 0,
            "executions": 0,
            "successful_executions": 0,
            "profit": 0,
            "gas_cost": 0
        })
        
        # Token-specific metrics
        self._token_metrics: DefaultDict[str, Dict[str, Any]] = defaultdict(lambda: {
            "opportunities": 0,
            "executions": 0,
            "successful_executions": 0,
            "profit": 0,
            "gas_cost": 0
        })
        
        # Recent opportunities and executions
        self._recent_opportunities: Dict[str, ArbitrageOpportunity] = {}
        self._recent_executions: Dict[str, ExecutionResult] = {}
        
        # Maximum number of recent items to keep
        self.max_recent_items = self.config.get("max_recent_items", 100)
        
        # Background tasks
        self._persist_task = None
        self._shutdown_event = asyncio.Event()
        
        # Locks
        self._analytics_lock = asyncio.Lock()
        
        logger.info("BaseAnalyticsManager initialized")
        
        # Start auto-persist task if enabled
        if self.auto_persist:
            self._persist_task = asyncio.create_task(self._auto_persist_loop())
    
    async def register_analytics(
        self,
        analytics: ArbitrageAnalytics,
        analytics_id: str
    ) -> None:
        """
        Register an analytics component.
        
        Args:
            analytics: Analytics component to register
            analytics_id: Unique identifier for this component
        """
        if analytics_id in self._analytics_components:
            logger.warning(f"Analytics component {analytics_id} already registered, replacing")
        
        self._analytics_components[analytics_id] = analytics
        logger.info(f"Registered analytics component: {analytics_id}")
    
    async def record_opportunity(
        self,
        opportunity: ArbitrageOpportunity
    ) -> None:
        """
        Record an arbitrage opportunity.
        
        Args:
            opportunity: Opportunity to record
        """
        async with self._analytics_lock:
            logger.debug(f"Recording opportunity {opportunity.id}")
            
            # Update metrics
            self._opportunity_count += 1
            
            # Update time-series data
            hour_key = self._get_hour_key(opportunity.timestamp)
            self._hourly_metrics[hour_key]["opportunities"] += 1
            
            # Update token metrics
            if opportunity.input_token_address:
                token_key = opportunity.input_token_address.lower()
                self._token_metrics[token_key]["opportunities"] += 1
            
            # Store in recent opportunities
            self._recent_opportunities[opportunity.id] = opportunity
            
            # Trim recent opportunities if needed
            if len(self._recent_opportunities) > self.max_recent_items:
                # Remove oldest opportunities
                sorted_ops = sorted(
                    self._recent_opportunities.items(),
                    key=lambda x: x[1].timestamp
                )
                for i in range(len(sorted_ops) - self.max_recent_items):
                    del self._recent_opportunities[sorted_ops[i][0]]
            
            # Forward to registered analytics components
            for analytics_id, analytics in self._analytics_components.items():
                try:
                    await analytics.record_opportunity(opportunity)
                except Exception as e:
                    logger.error(f"Error recording opportunity in {analytics_id}: {e}")
    
    async def record_execution(
        self,
        execution_result: ExecutionResult
    ) -> None:
        """
        Record an execution result.
        
        Args:
            execution_result: Execution result to record
        """
        async with self._analytics_lock:
            logger.debug(f"Recording execution for opportunity {execution_result.opportunity_id}")
            
            # Update metrics
            self._execution_count += 1
            
            if execution_result.success:
                self._success_count += 1
                if execution_result.actual_profit is not None:
                    self._total_profit += execution_result.actual_profit
                if execution_result.gas_used is not None:
                    self._total_gas_cost += execution_result.gas_used
            
            # Track execution time if we have the opportunity
            opportunity = self._recent_opportunities.get(execution_result.opportunity_id)
            if opportunity and opportunity.execution_timestamp and opportunity.timestamp:
                execution_time = opportunity.execution_timestamp - opportunity.timestamp
                self._execution_times.append(execution_time)
            
            # Update time-series data
            hour_key = self._get_hour_key(execution_result.timestamp)
            self._hourly_metrics[hour_key]["executions"] += 1
            if execution_result.success:
                self._hourly_metrics[hour_key]["successful_executions"] += 1
                if execution_result.actual_profit is not None:
                    self._hourly_metrics[hour_key]["profit"] += execution_result.actual_profit
                if execution_result.gas_used is not None:
                    self._hourly_metrics[hour_key]["gas_cost"] += execution_result.gas_used
            
            # Update token metrics if we have the opportunity
            if opportunity and opportunity.input_token_address:
                token_key = opportunity.input_token_address.lower()
                self._token_metrics[token_key]["executions"] += 1
                if execution_result.success:
                    self._token_metrics[token_key]["successful_executions"] += 1
                    if execution_result.actual_profit is not None:
                        self._token_metrics[token_key]["profit"] += execution_result.actual_profit
                    if execution_result.gas_used is not None:
                        self._token_metrics[token_key]["gas_cost"] += execution_result.gas_used
            
            # Store in recent executions
            self._recent_executions[execution_result.opportunity_id] = execution_result
            
            # Trim recent executions if needed
            if len(self._recent_executions) > self.max_recent_items:
                # Remove oldest executions
                sorted_execs = sorted(
                    self._recent_executions.items(),
                    key=lambda x: x[1].timestamp
                )
                for i in range(len(sorted_execs) - self.max_recent_items):
                    del self._recent_executions[sorted_execs[i][0]]
            
            # Forward to registered analytics components
            for analytics_id, analytics in self._analytics_components.items():
                try:
                    await analytics.record_execution(execution_result)
                except Exception as e:
                    logger.error(f"Error recording execution in {analytics_id}: {e}")
    
    async def get_performance_metrics(
        self,
        time_range_seconds: Optional[int] = None,
        analytics_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for arbitrage operations.
        
        Args:
            time_range_seconds: How far back to analyze, or None for all time
            analytics_id: Specific analytics to use, or None for aggregated
            
        Returns:
            Dictionary of performance metrics
        """
        async with self._analytics_lock:
            # If specific analytics component requested
            if analytics_id and analytics_id in self._analytics_components:
                try:
                    return await self._analytics_components[analytics_id].get_performance_metrics(
                        time_range_seconds=time_range_seconds
                    )
                except Exception as e:
                    logger.error(f"Error getting metrics from {analytics_id}: {e}")
                    return {}
            
            # Calculate time-filtered metrics
            filtered_opportunities = self._recent_opportunities.values()
            filtered_executions = self._recent_executions.values()
            
            if time_range_seconds:
                cutoff_time = time.time() - time_range_seconds
                filtered_opportunities = [
                    opp for opp in filtered_opportunities 
                    if opp.timestamp >= cutoff_time
                ]
                filtered_executions = [
                    exec_result for exec_result in filtered_executions 
                    if exec_result.timestamp >= cutoff_time
                ]
            
            # Calculate metrics
            opportunity_count = len(filtered_opportunities)
            execution_count = len(filtered_executions)
            success_count = sum(1 for r in filtered_executions if r.success)
            success_rate = success_count / execution_count if execution_count > 0 else 0
            
            total_profit = sum(r.actual_profit or 0 for r in filtered_executions if r.success)
            total_gas_cost = sum(r.gas_used or 0 for r in filtered_executions if r.success)
            
            avg_execution_time = 0
            if filtered_opportunities and filtered_executions:
                execution_times = []
                for opp in filtered_opportunities:
                    if opp.execution_timestamp and opp.timestamp:
                        execution_times.append(opp.execution_timestamp - opp.timestamp)
                if execution_times:
                    avg_execution_time = sum(execution_times) / len(execution_times)
            
            # Return metrics
            return {
                "opportunity_count": opportunity_count,
                "execution_count": execution_count,
                "success_count": success_count,
                "success_rate": success_rate,
                "total_profit": total_profit,
                "total_gas_cost": total_gas_cost,
                "avg_execution_time": avg_execution_time,
                "profit_per_execution": total_profit / success_count if success_count > 0 else 0,
                "net_profit": total_profit - total_gas_cost,
                "recent_opportunity_ids": list(self._recent_opportunities.keys())[-10:],
                "recent_execution_ids": list(self._recent_executions.keys())[-10:],
                "hourly_metrics": dict(self._hourly_metrics),
                "top_tokens": self._get_top_tokens(5)
            }
    
    async def persist_data(self) -> None:
        """Persist analytics data to disk."""
        async with self._analytics_lock:
            try:
                logger.info("Persisting analytics data")
                
                # Create timestamp for filename
                timestamp = int(time.time())
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
                
                # Ensure date directory exists
                date_dir = os.path.join(self.data_dir, date_str)
                os.makedirs(date_dir, exist_ok=True)
                
                # Save opportunities
                opportunities_path = os.path.join(date_dir, f"opportunities_{timestamp}.json")
                with open(opportunities_path, 'w') as f:
                    json.dump(
                        {
                            "timestamp": timestamp,
                            "opportunities": [opp.to_dict() for opp in self._recent_opportunities.values()]
                        },
                        f,
                        indent=2
                    )
                
                # Save executions
                executions_path = os.path.join(date_dir, f"executions_{timestamp}.json")
                with open(executions_path, 'w') as f:
                    json.dump(
                        {
                            "timestamp": timestamp,
                            "executions": [exec_result.to_dict() for exec_result in self._recent_executions.values()]
                        },
                        f,
                        indent=2
                    )
                
                # Save metrics
                metrics_path = os.path.join(date_dir, f"metrics_{timestamp}.json")
                with open(metrics_path, 'w') as f:
                    json.dump(
                        {
                            "timestamp": timestamp,
                            "opportunity_count": self._opportunity_count,
                            "execution_count": self._execution_count,
                            "success_count": self._success_count,
                            "total_profit": self._total_profit,
                            "total_gas_cost": self._total_gas_cost,
                            "hourly_metrics": dict(self._hourly_metrics),
                            "token_metrics": dict(self._token_metrics)
                        },
                        f,
                        indent=2
                    )
                
                logger.info(f"Analytics data persisted to {date_dir}")
                
                # Clean up old files
                self._clean_old_data()
                
            except Exception as e:
                logger.error(f"Error persisting analytics data: {e}")
    
    async def _auto_persist_loop(self) -> None:
        """Background task for automatic data persistence."""
        try:
            logger.info("Starting auto-persist loop")
            while not self._shutdown_event.is_set():
                try:
                    # Wait for interval or shutdown
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.persist_interval
                        )
                    except asyncio.TimeoutError:
                        # Normal timeout, persist data
                        pass
                    
                    # Exit if shutdown
                    if self._shutdown_event.is_set():
                        break
                    
                    # Persist data
                    await self.persist_data()
                    
                except Exception as e:
                    logger.error(f"Error in persist loop: {e}")
                    await asyncio.sleep(60)  # Wait a minute on error
            
        except asyncio.CancelledError:
            logger.info("Auto-persist loop cancelled")
            raise
        
        logger.info("Auto-persist loop stopped")
    
    def _get_hour_key(self, timestamp: float) -> str:
        """Get hour key for time-series data."""
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d_%H")
    
    def _get_top_tokens(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get top tokens by profit."""
        # Sort token metrics by profit
        sorted_tokens = sorted(
            self._token_metrics.items(),
            key=lambda x: x[1]["profit"],
            reverse=True
        )
        
        # Return top N
        return [
            {"token": token, **metrics}
            for token, metrics in sorted_tokens[:count]
        ]
    
    def _clean_old_data(self) -> None:
        """Clean up old analytics data files."""
        try:
            # Keep data for the last 30 days
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # Iterate through date directories
            for date_dir in os.listdir(self.data_dir):
                try:
                    dir_date = datetime.strptime(date_dir, "%Y-%m-%d")
                    if dir_date < cutoff_date:
                        # Remove old directory
                        dir_path = os.path.join(self.data_dir, date_dir)
                        for file in os.listdir(dir_path):
                            os.remove(os.path.join(dir_path, file))
                        os.rmdir(dir_path)
                        logger.info(f"Removed old analytics data: {date_dir}")
                except ValueError:
                    # Not a date directory
                    continue
        
        except Exception as e:
            logger.error(f"Error cleaning old data: {e}")
    
    async def stop(self) -> None:
        """Stop the analytics manager and clean up resources."""
        self._shutdown_event.set()
        
        if self._persist_task:
            try:
                # Wait for persist task to complete
                await asyncio.wait_for(self._persist_task, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for persist task")
                self._persist_task.cancel()
            
            self._persist_task = None
        
        # Final persist
        await self.persist_data()
        
        logger.info("Analytics manager stopped")


async def create_analytics_manager(
    config: Dict[str, Any] = None
) -> BaseAnalyticsManager:
    """
    Create and initialize an analytics manager.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized analytics manager
    """
    manager = BaseAnalyticsManager(config=config)
    return manager