"""
Execution Manager

This module contains the implementation of the ExecutionManager,
which coordinates the execution of arbitrage opportunities.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, Tuple
import uuid

from .interfaces import (
    ExecutionManager,
    ExecutionStrategy,
    TransactionMonitor
)
from .models import (
    ArbitrageOpportunity,
    ExecutionResult,
    ExecutionStatus
)

logger = logging.getLogger(__name__)


class BaseExecutionManager(ExecutionManager):
    """
    Base implementation of the ExecutionManager.
    
    This class coordinates the execution of arbitrage opportunities
    using registered strategies and monitors.
    """
    
    def __init__(
        self,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the execution manager.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        
        # Registered components
        self._strategies: Dict[str, ExecutionStrategy] = {}
        self._monitors: Dict[str, TransactionMonitor] = {}
        
        # Configuration
        self.default_strategy_id = self.config.get("default_strategy", "standard")
        self.default_monitor_id = self.config.get("default_monitor", "standard")
        self.execution_timeout = self.config.get("execution_timeout_seconds", 120)
        self.transaction_timeout = self.config.get("transaction_timeout_seconds", 180)
        self.max_retries = self.config.get("max_execution_retries", 1)
        
        # Active executions
        self._active_executions: Dict[str, asyncio.Task] = {}
        
        # Locks
        self._execution_lock = asyncio.Lock()
        
        logger.info("BaseExecutionManager initialized")
    
    async def register_strategy(
        self,
        strategy: ExecutionStrategy,
        strategy_id: str
    ) -> None:
        """
        Register an execution strategy.
        
        Args:
            strategy: Strategy to register
            strategy_id: Unique identifier for this strategy
        """
        if strategy_id in self._strategies:
            logger.warning(f"Strategy {strategy_id} already registered, replacing")
        
        self._strategies[strategy_id] = strategy
        logger.info(f"Registered execution strategy: {strategy_id}")
    
    async def register_monitor(
        self,
        monitor: TransactionMonitor,
        monitor_id: str
    ) -> None:
        """
        Register a transaction monitor.
        
        Args:
            monitor: Monitor to register
            monitor_id: Unique identifier for this monitor
        """
        if monitor_id in self._monitors:
            logger.warning(f"Monitor {monitor_id} already registered, replacing")
        
        self._monitors[monitor_id] = monitor
        logger.info(f"Registered transaction monitor: {monitor_id}")
    
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        strategy_id: Optional[str] = None,
        monitor_id: Optional[str] = None,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.
        
        Args:
            opportunity: Opportunity to execute
            strategy_id: Specific strategy to use, or None for default
            monitor_id: Specific monitor to use, or None for default
            **kwargs: Additional execution parameters
            
        Returns:
            Result of the execution
        """
        async with self._execution_lock:
            # Generate execution ID
            execution_id = kwargs.get("execution_id", str(uuid.uuid4()))
            logger.info(f"Starting execution {execution_id} for opportunity {opportunity.id}")
            
            # Select strategy
            strategy_id = strategy_id or self.default_strategy_id
            if strategy_id not in self._strategies:
                logger.error(f"Strategy {strategy_id} not found")
                return ExecutionResult(
                    opportunity_id=opportunity.id,
                    success=False,
                    error_message=f"Strategy {strategy_id} not found"
                )
            
            strategy = self._strategies[strategy_id]
            logger.info(f"Using strategy {strategy_id}")
            
            # Select monitor
            monitor_id = monitor_id or self.default_monitor_id
            if monitor_id not in self._monitors:
                logger.error(f"Monitor {monitor_id} not found")
                return ExecutionResult(
                    opportunity_id=opportunity.id,
                    success=False,
                    error_message=f"Monitor {monitor_id} not found"
                )
            
            monitor = self._monitors[monitor_id]
            logger.info(f"Using monitor {monitor_id}")
            
            # Execute with retries
            result = None
            retry_count = 0
            
            while result is None or (
                not result.success and 
                retry_count < self.max_retries and
                result.status != ExecutionStatus.REJECTED
            ):
                if retry_count > 0:
                    logger.info(f"Retrying execution {execution_id} (attempt {retry_count+1}/{self.max_retries+1})")
                
                try:
                    # Execute the opportunity
                    execution_task = asyncio.create_task(strategy.execute_opportunity(
                        opportunity=opportunity,
                        execution_id=execution_id,
                        **kwargs
                    ))
                    
                    # Store active execution
                    self._active_executions[execution_id] = execution_task
                    
                    # Wait for execution with timeout
                    try:
                        result = await asyncio.wait_for(
                            execution_task,
                            timeout=self.execution_timeout
                        )
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"Execution {execution_id} timed out")
                        result = ExecutionResult(
                            opportunity_id=opportunity.id,
                            success=False,
                            status=ExecutionStatus.TIMEOUT,
                            error_message="Execution timed out"
                        )
                        execution_task.cancel()
                    
                    # Monitor transaction if needed
                    if result.success and result.transaction_hash and monitor:
                        logger.info(f"Monitoring transaction {result.transaction_hash}")
                        try:
                            monitoring_result = await asyncio.wait_for(
                                monitor.monitor_transaction(
                                    transaction_hash=result.transaction_hash,
                                    timeout_seconds=self.transaction_timeout,
                                    opportunity_id=opportunity.id,
                                    execution_id=execution_id
                                ),
                                timeout=self.transaction_timeout + 10  # Add a small buffer
                            )
                            
                            # Update result with monitoring info
                            result.status = monitoring_result.status
                            result.gas_used = monitoring_result.gas_used
                            result.actual_profit = monitoring_result.actual_profit
                            result.block_number = monitoring_result.block_number
                            result.receipt = monitoring_result.receipt
                            
                            # Check if transaction failed
                            if result.status != ExecutionStatus.CONFIRMED:
                                result.success = False
                                logger.warning(f"Transaction failed with status: {result.status}")
                            
                        except asyncio.TimeoutError:
                            logger.warning(f"Transaction monitoring timed out for {result.transaction_hash}")
                            result.status = ExecutionStatus.TIMEOUT
                            result.success = False
                            result.error_message = "Transaction monitoring timed out"
                    
                except Exception as e:
                    logger.error(f"Error executing opportunity: {e}")
                    result = ExecutionResult(
                        opportunity_id=opportunity.id,
                        success=False,
                        error_message=str(e)
                    )
                
                finally:
                    # Clean up active execution
                    if execution_id in self._active_executions:
                        del self._active_executions[execution_id]
                
                # Increment retry counter
                retry_count += 1
            
            # Log final result
            if result.success:
                logger.info(f"Execution {execution_id} successful: TX {result.transaction_hash}")
                if result.actual_profit:
                    logger.info(f"Actual profit: {result.actual_profit} wei")
            else:
                logger.warning(f"Execution {execution_id} failed: {result.error_message}")
            
            return result


async def create_execution_manager(
    config: Dict[str, Any] = None
) -> BaseExecutionManager:
    """
    Create and initialize an execution manager.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized execution manager
    """
    manager = BaseExecutionManager(config=config)
    return manager