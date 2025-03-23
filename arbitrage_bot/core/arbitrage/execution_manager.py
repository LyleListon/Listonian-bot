"""
Execution Manager Implementation

This module provides the implementation of the ExecutionManager protocol.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

from .interfaces import ExecutionStrategy, TransactionMonitor, ExecutionManager
from .models import ArbitrageOpportunity, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)

class EnhancedExecutionManager(ExecutionManager):
    """
    Implementation of the ExecutionManager protocol.
    
    This class coordinates execution strategies and transaction monitors to
    execute arbitrage opportunities.
    """
    
    def __init__(self):
        """Initialize the execution manager."""
        self._strategies = {}  # strategy_id -> strategy
        self._monitors = {}  # monitor_id -> monitor
        self._active_executions = {}  # execution_id -> execution_info
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the execution manager."""
        async with self._lock:
            if self._initialized:
                return
            
            logger.info("Initializing execution manager")
            self._initialized = True
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        async with self._lock:
            # Cancel any active executions
            for execution_id, execution_info in self._active_executions.items():
                try:
                    await self._cancel_execution(execution_id)
                except Exception as e:
                    logger.error(
                        f"Error cancelling execution {execution_id}: {e}",
                        exc_info=True
                    )
            
            self._initialized = False
            self._strategies.clear()
            self._monitors.clear()
            self._active_executions.clear()
    
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
        async with self._lock:
            if strategy_id in self._strategies:
                raise ValueError(f"Strategy {strategy_id} already registered")
            
            self._strategies[strategy_id] = strategy
            logger.info(f"Registered strategy {strategy_id}")
    
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
        async with self._lock:
            if monitor_id in self._monitors:
                raise ValueError(f"Monitor {monitor_id} already registered")
            
            self._monitors[monitor_id] = monitor
            logger.info(f"Registered monitor {monitor_id}")
    
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
        if not self._initialized:
            raise RuntimeError("Execution manager not initialized")
        
        # Get the strategy
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        # Execute the opportunity
        try:
            # Create execution result
            execution_id = f"exec_{opportunity.id}_{strategy_id}"
            result = ExecutionResult(
                id=execution_id,
                opportunity=opportunity,
                status=ExecutionStatus.PENDING,
                strategy_id=strategy_id
            )
            
            # Add to active executions
            self._active_executions[execution_id] = {
                "result": result,
                "strategy": strategy,
                "monitors": []
            }
            
            # Execute using strategy
            result = await strategy.execute_opportunity(
                opportunity=opportunity,
                **kwargs
            )
            
            # Monitor transaction if available
            if result.transaction_hash:
                monitor_tasks = []
                for monitor in self._monitors.values():
                    task = asyncio.create_task(
                        self._monitor_transaction(
                            monitor=monitor,
                            execution_id=execution_id,
                            transaction_hash=result.transaction_hash
                        )
                    )
                    monitor_tasks.append(task)
                    self._active_executions[execution_id]["monitors"].append(task)
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error executing opportunity {opportunity.id}: {e}",
                exc_info=True
            )
            result = ExecutionResult(
                id=execution_id,
                opportunity=opportunity,
                status=ExecutionStatus.FAILED,
                strategy_id=strategy_id,
                error=str(e)
            )
            return result
    
    async def get_execution_status(
        self,
        execution_id: str
    ) -> ExecutionStatus:
        """
        Get the status of an execution.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Current status of the execution
        """
        execution_info = self._active_executions.get(execution_id)
        if not execution_info:
            return ExecutionStatus.NOT_FOUND
        
        return execution_info["result"].status
    
    async def _monitor_transaction(
        self,
        monitor: TransactionMonitor,
        execution_id: str,
        transaction_hash: str
    ) -> None:
        """Monitor a transaction and update execution status."""
        try:
            status = await monitor.monitor_transaction(
                transaction_hash=transaction_hash
            )
            
            # Update execution status
            execution_info = self._active_executions.get(execution_id)
            if execution_info:
                execution_info["result"].status = status
                
                # Remove from active executions if final
                if status.is_final:
                    await self._cleanup_execution(execution_id)
                    
        except Exception as e:
            logger.error(
                f"Error monitoring transaction {transaction_hash}: {e}",
                exc_info=True
            )
    
    async def _cancel_execution(
        self,
        execution_id: str
    ) -> None:
        """Cancel an active execution."""
        execution_info = self._active_executions.get(execution_id)
        if not execution_info:
            return
        
        # Cancel monitor tasks
        for task in execution_info["monitors"]:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Update status
        execution_info["result"].status = ExecutionStatus.CANCELLED
        
        # Remove from active executions
        await self._cleanup_execution(execution_id)
    
    async def _cleanup_execution(
        self,
        execution_id: str
    ) -> None:
        """Clean up an execution."""
        async with self._lock:
            if execution_id in self._active_executions:
                del self._active_executions[execution_id]