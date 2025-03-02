"""
Default Execution Manager

This module contains the implementation of the DefaultExecutionManager,
which is responsible for executing arbitrage opportunities using appropriate strategies.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Set, Tuple, cast

from ...dex.interfaces import DEX
from ...web3.interfaces import Web3Client, Transaction, TransactionReceipt
from ..interfaces import (
    ExecutionManager,
    ExecutionStrategy,
    TransactionMonitor,
    BalanceManager
)
from ..models import (
    ArbitrageOpportunity,
    ArbitrageRoute,
    ExecutionResult,
    ExecutionStatus,
    OpportunityStatus,
    TransactionInfo,
    MarketCondition
)

logger = logging.getLogger(__name__)


class DefaultExecutionManager(ExecutionManager):
    """
    Default implementation of the ExecutionManager interface.
    
    This manager is responsible for executing arbitrage opportunities,
    selecting appropriate strategies, and monitoring transaction status.
    """
    
    def __init__(
        self,
        web3_client: Web3Client,
        dexes: Dict[str, DEX],
        strategies: Dict[str, ExecutionStrategy],
        transaction_monitor: Optional[TransactionMonitor] = None,
        balance_manager: Optional[BalanceManager] = None,
        config: Dict[str, Any] = None
    ):
        """
        Initialize the execution manager.
        
        Args:
            web3_client: Web3 client for blockchain interactions
            dexes: Dictionary mapping DEX IDs to DEX instances
            strategies: Dictionary mapping strategy names to strategy instances
            transaction_monitor: Optional transaction monitor
            balance_manager: Optional balance manager
            config: Configuration dictionary
        """
        self.web3_client = web3_client
        self.dexes = dexes
        self.strategies = strategies
        self.transaction_monitor = transaction_monitor
        self.balance_manager = balance_manager
        self.config = config or {}
        
        # Configuration
        self.max_concurrent_executions = int(self.config.get("max_concurrent_executions", 1))
        self.default_strategy = self.config.get("default_strategy", "standard")
        self.execution_timeout = int(self.config.get("execution_timeout", 300))  # 5 minutes
        self.enable_flashbots = bool(self.config.get("enable_flashbots", False))
        self.min_confidence_score = Decimal(self.config.get("min_confidence_score", "0.7"))  # 70% confidence
        
        # Execution state
        self._active_executions: Dict[str, asyncio.Task] = {}
        self._execution_lock = asyncio.Lock()
        self._last_execution_time = 0
        
        logger.info("DefaultExecutionManager initialized")
    
    async def execute_opportunity(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: MarketCondition,
        **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.
        
        Args:
            opportunity: Arbitrage opportunity to execute
            market_condition: Current market condition
            **kwargs: Additional execution parameters
            
        Returns:
            Execution result
        """
        logger.info(f"Executing arbitrage opportunity: {opportunity.id}")
        
        # Verify opportunity status
        if opportunity.status != OpportunityStatus.VALIDATED:
            logger.warning(f"Opportunity {opportunity.id} is not validated, skipping execution")
            return ExecutionResult(
                opportunity_id=opportunity.id,
                status=ExecutionStatus.SKIPPED,
                timestamp=int(time.time()),
                message="Opportunity is not validated",
                transaction_info=None,
                profit=None,
                gas_used=None,
                total_cost=None
            )
        
        # Check confidence score
        if opportunity.confidence_score < self.min_confidence_score:
            logger.warning(
                f"Opportunity {opportunity.id} confidence score {opportunity.confidence_score} "
                f"is below threshold {self.min_confidence_score}, skipping execution"
            )
            return ExecutionResult(
                opportunity_id=opportunity.id,
                status=ExecutionStatus.SKIPPED,
                timestamp=int(time.time()),
                message=f"Confidence score {opportunity.confidence_score} below threshold",
                transaction_info=None,
                profit=None,
                gas_used=None,
                total_cost=None
            )
        
        # Limit concurrent executions
        async with self._execution_lock:
            # Check if maximum concurrent executions is reached
            if len(self._active_executions) >= self.max_concurrent_executions:
                logger.warning(
                    f"Maximum concurrent executions ({self.max_concurrent_executions}) reached, "
                    f"skipping opportunity {opportunity.id}"
                )
                return ExecutionResult(
                    opportunity_id=opportunity.id,
                    status=ExecutionStatus.SKIPPED,
                    timestamp=int(time.time()),
                    message="Maximum concurrent executions reached",
                    transaction_info=None,
                    profit=None,
                    gas_used=None,
                    total_cost=None
                )
            
            # Check if enough time has passed since last execution
            min_time_between_executions = int(self.config.get("min_time_between_executions", 0))
            current_time = time.time()
            if current_time - self._last_execution_time < min_time_between_executions:
                logger.warning(
                    f"Not enough time passed since last execution, "
                    f"skipping opportunity {opportunity.id}"
                )
                return ExecutionResult(
                    opportunity_id=opportunity.id,
                    status=ExecutionStatus.SKIPPED,
                    timestamp=int(time.time()),
                    message="Not enough time passed since last execution",
                    transaction_info=None,
                    profit=None,
                    gas_used=None,
                    total_cost=None
                )
            
            # Update last execution time
            self._last_execution_time = current_time
            
            # Create execution task
            execution_task = asyncio.create_task(
                self._execute_opportunity_internal(opportunity, market_condition, **kwargs)
            )
            
            # Store the task
            self._active_executions[opportunity.id] = execution_task
        
        try:
            # Wait for execution to complete with timeout
            execution_result = await asyncio.wait_for(
                execution_task,
                timeout=self.execution_timeout
            )
            
            return execution_result
            
        except asyncio.TimeoutError:
            logger.error(f"Execution of opportunity {opportunity.id} timed out")
            return ExecutionResult(
                opportunity_id=opportunity.id,
                status=ExecutionStatus.FAILED,
                timestamp=int(time.time()),
                message="Execution timed out",
                transaction_info=None,
                profit=None,
                gas_used=None,
                total_cost=None
            )
            
        finally:
            # Clean up the task
            async with self._execution_lock:
                if opportunity.id in self._active_executions:
                    del self._active_executions[opportunity.id]
    
    async def _execute_opportunity_internal(
        self,
        opportunity: ArbitrageOpportunity,
        market_condition: MarketCondition,
        **kwargs
    ) -> ExecutionResult:
        """
        Internal method to execute an arbitrage opportunity.
        
        Args:
            opportunity: Arbitrage opportunity to execute
            market_condition: Current market condition
            **kwargs: Additional execution parameters
            
        Returns:
            Execution result
        """
        # Determine which strategy to use
        strategy_name = kwargs.get("strategy", self.default_strategy)
        
        # Select strategy
        if strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
        else:
            logger.warning(f"Strategy {strategy_name} not found, using default strategy")
            strategy = self.strategies[self.default_strategy]
        
        # Check if balance manager exists and verify sufficient balance
        if self.balance_manager:
            has_sufficient_balance = await self.balance_manager.verify_balance(
                opportunity.route.input_token.address,
                opportunity.route.input_token.amount
            )
            
            if not has_sufficient_balance:
                logger.warning(
                    f"Insufficient balance for opportunity {opportunity.id}, "
                    f"token: {opportunity.route.input_token.address}, "
                    f"amount: {opportunity.route.input_token.amount}"
                )
                return ExecutionResult(
                    opportunity_id=opportunity.id,
                    status=ExecutionStatus.FAILED,
                    timestamp=int(time.time()),
                    message="Insufficient balance",
                    transaction_info=None,
                    profit=None,
                    gas_used=None,
                    total_cost=None
                )
        
        try:
            # Prepare execution parameters - incorporate MEV protection if enabled
            execution_params = {**kwargs}
            
            # Add Flashbots parameters if enabled
            if self.enable_flashbots:
                execution_params["use_flashbots"] = True
                
                # Add priority fee if provided in market condition
                if market_condition.priority_fee:
                    execution_params["priority_fee"] = market_condition.priority_fee
            
            # Execute the opportunity using the selected strategy
            logger.info(f"Executing opportunity {opportunity.id} with strategy {strategy_name}")
            execution_result = await strategy.execute(
                opportunity=opportunity,
                web3_client=self.web3_client,
                dexes=self.dexes,
                **execution_params
            )
            
            # Monitor transaction if transaction monitor exists and execution succeeded
            if (
                self.transaction_monitor and 
                execution_result.status == ExecutionStatus.SUBMITTED and
                execution_result.transaction_info is not None
            ):
                transaction_hash = execution_result.transaction_info.transaction_hash
                
                # Monitor transaction
                logger.info(f"Monitoring transaction {transaction_hash} for opportunity {opportunity.id}")
                updated_transaction_info = await self.transaction_monitor.monitor_transaction(
                    transaction_hash=transaction_hash,
                    opportunity=opportunity,
                    **kwargs
                )
                
                # Update execution result based on transaction status
                if updated_transaction_info:
                    if updated_transaction_info.status:
                        execution_result.status = ExecutionStatus.SUCCEEDED
                        execution_result.message = "Transaction succeeded"
                    else:
                        execution_result.status = ExecutionStatus.FAILED
                        execution_result.message = f"Transaction failed: {updated_transaction_info.error_message}"
                    
                    execution_result.transaction_info = updated_transaction_info
                    execution_result.gas_used = updated_transaction_info.gas_used
                    execution_result.total_cost = (
                        updated_transaction_info.gas_used * 
                        (updated_transaction_info.gas_price + updated_transaction_info.priority_fee)
                    )
            
            # Log execution result
            if execution_result.status == ExecutionStatus.SUCCEEDED:
                logger.info(
                    f"Execution of opportunity {opportunity.id} succeeded, "
                    f"profit: {execution_result.profit}, "
                    f"gas used: {execution_result.gas_used}, "
                    f"total cost: {execution_result.total_cost}"
                )
            else:
                logger.warning(
                    f"Execution of opportunity {opportunity.id} {execution_result.status.name}, "
                    f"message: {execution_result.message}"
                )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error executing opportunity {opportunity.id}: {e}")
            return ExecutionResult(
                opportunity_id=opportunity.id,
                status=ExecutionStatus.FAILED,
                timestamp=int(time.time()),
                message=f"Execution error: {e}",
                transaction_info=None,
                profit=None,
                gas_used=None,
                total_cost=None
            )
    
    async def cancel_execution(
        self,
        opportunity_id: str
    ) -> bool:
        """
        Cancel the execution of an arbitrage opportunity.
        
        Args:
            opportunity_id: ID of the opportunity to cancel
            
        Returns:
            True if the execution was cancelled, False otherwise
        """
        logger.info(f"Cancelling execution of opportunity: {opportunity_id}")
        
        async with self._execution_lock:
            if opportunity_id in self._active_executions:
                # Get the execution task
                execution_task = self._active_executions[opportunity_id]
                
                # Cancel the task
                execution_task.cancel()
                
                # Remove from active executions
                del self._active_executions[opportunity_id]
                
                logger.info(f"Execution of opportunity {opportunity_id} cancelled")
                return True
            else:
                logger.warning(f"Opportunity {opportunity_id} not found in active executions")
                return False
    
    async def get_execution_status(
        self,
        opportunity_id: str
    ) -> Optional[ExecutionStatus]:
        """
        Get the status of an arbitrage opportunity execution.
        
        Args:
            opportunity_id: ID of the opportunity
            
        Returns:
            Execution status if the opportunity is being executed, None otherwise
        """
        async with self._execution_lock:
            if opportunity_id in self._active_executions:
                execution_task = self._active_executions[opportunity_id]
                
                if execution_task.done():
                    if execution_task.exception():
                        return ExecutionStatus.FAILED
                    else:
                        try:
                            execution_result = execution_task.result()
                            return execution_result.status
                        except Exception:
                            return ExecutionStatus.FAILED
                else:
                    return ExecutionStatus.PENDING
            else:
                return None
    
    async def get_active_executions(self) -> List[str]:
        """
        Get the list of active executions.
        
        Returns:
            List of opportunity IDs being executed
        """
        async with self._execution_lock:
            return list(self._active_executions.keys())
    
    async def close(self):
        """Close the execution manager and release resources."""
        logger.info("Closing DefaultExecutionManager")
        
        # Cancel all active executions
        async with self._execution_lock:
            for opportunity_id, execution_task in self._active_executions.items():
                logger.info(f"Cancelling execution of opportunity {opportunity_id}")
                execution_task.cancel()
            
            self._active_executions.clear()
        
        # Close the transaction monitor if it exists
        if self.transaction_monitor:
            await self.transaction_monitor.close()


async def create_default_execution_manager(
    web3_client: Web3Client,
    dexes: Dict[str, DEX],
    strategies: Dict[str, ExecutionStrategy],
    transaction_monitor: Optional[TransactionMonitor] = None,
    balance_manager: Optional[BalanceManager] = None,
    config: Dict[str, Any] = None
) -> DefaultExecutionManager:
    """
    Factory function to create a default execution manager.
    
    Args:
        web3_client: Web3 client for blockchain interactions
        dexes: Dictionary mapping DEX IDs to DEX instances
        strategies: Dictionary mapping strategy names to strategy instances
        transaction_monitor: Optional transaction monitor
        balance_manager: Optional balance manager
        config: Configuration dictionary
        
    Returns:
        Initialized default execution manager
    """
    return DefaultExecutionManager(
        web3_client=web3_client,
        dexes=dexes,
        strategies=strategies,
        transaction_monitor=transaction_monitor,
        balance_manager=balance_manager,
        config=config
    )