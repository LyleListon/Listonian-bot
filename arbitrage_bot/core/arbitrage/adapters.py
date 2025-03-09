"""
Arbitrage System Legacy Adapters

This module provides adapter classes that implement the interface protocols
but delegate to existing legacy code. This enables gradual migration from the
old codebase to the new architecture.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .interfaces import (
    OpportunityDiscoveryManager,
    OpportunityDetector,
    OpportunityValidator,
    ExecutionManager,
    ExecutionStrategy,
    TransactionMonitor,
    ArbitrageAnalytics,
    MarketDataProvider
)
from .models import (
    ArbitrageOpportunity,
    ArbitrageRoute,
    RouteStep,
    ExecutionResult,
    StrategyType,
    OpportunityStatus,
    ExecutionStatus,
    TransactionStatus,
    ErrorType,
    ErrorDetails,
    TransactionDetails,
    PerformanceMetrics
)

# Import legacy code
from ..monitor import ArbitrageMonitor  # Legacy monitor
from ..execution import ArbitrageExecutor  # Legacy executor
from ..analytics import OpportunityTracker  # Legacy tracker
from ..data import MarketDataManager  # Legacy data manager

logger = logging.getLogger(__name__)


class LegacyDiscoveryManagerAdapter(OpportunityDiscoveryManager):
    """
    Adapter implementing OpportunityDiscoveryManager interface but delegating to legacy code.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the legacy discovery manager adapter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.arbitrage_monitor = ArbitrageMonitor(config)
        
        # Internal storage for registered detectors and validators
        self.detectors = {}
        self.validators = {}
        
        logger.info("Initialized legacy discovery manager adapter")
    
    async def register_detector(
        self, 
        detector: OpportunityDetector, 
        detector_id: str
    ) -> None:
        """
        Register an opportunity detector (not used in legacy mode).
        
        Args:
            detector: The detector to register
            detector_id: Unique identifier for the detector
        """
        logger.info(f"Registering detector {detector_id} (ignored in legacy mode)")
        self.detectors[detector_id] = detector
    
    async def register_validator(
        self, 
        validator: OpportunityValidator, 
        validator_id: str
    ) -> None:
        """
        Register an opportunity validator (not used in legacy mode).
        
        Args:
            validator: The validator to register
            validator_id: Unique identifier for the validator
        """
        logger.info(f"Registering validator {validator_id} (ignored in legacy mode)")
        self.validators[validator_id] = validator
    
    async def discover_opportunities(
        self, 
        max_results: int = 10, 
        min_profit_wei: int = 0, 
        **kwargs
    ) -> List[ArbitrageOpportunity]:
        """
        Discover arbitrage opportunities using legacy code.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_wei: Minimum profit threshold in wei
            **kwargs: Additional parameters
            
        Returns:
            List of discovered opportunities
        """
        logger.info(f"Discovering opportunities using legacy code (max_results={max_results}, min_profit_wei={min_profit_wei})")
        
        # Convert wei to ETH for legacy code
        min_profit_eth = min_profit_wei / 10**18
        
        # Call legacy method to find opportunities
        legacy_opportunities = await self.arbitrage_monitor.find_opportunities(
            min_profit=min_profit_eth,
            max_results=max_results
        )
        
        # Convert legacy opportunities to new model
        opportunities = []
        for legacy_opp in legacy_opportunities:
            # Create route steps
            steps = []
            for step in legacy_opp.get("steps", []):
                route_step = RouteStep(
                    dex_id=step.get("dex", "unknown"),
                    input_token_address=step.get("input_token", "0x"),
                    output_token_address=step.get("output_token", "0x"),
                    pool_address=step.get("pool_address"),
                    input_amount=step.get("input_amount"),
                    expected_output=step.get("expected_output"),
                    min_output=step.get("min_output"),
                    path_indexes=step.get("path", []),
                    fee_tier=step.get("fee_tier")
                )
                steps.append(route_step)
            
            # Create route
            route = ArbitrageRoute(
                steps=steps,
                input_token_address=legacy_opp.get("input_token", "0x"),
                output_token_address=legacy_opp.get("output_token", "0x"),
                input_amount=legacy_opp.get("input_amount", 0),
                expected_output=legacy_opp.get("expected_output", 0),
                min_output=legacy_opp.get("min_output"),
                expected_profit=legacy_opp.get("expected_profit", 0),
                gas_estimate=legacy_opp.get("gas_estimate")
            )
            
            # Determine strategy type
            strategy_type_str = legacy_opp.get("type", "cross_dex")
            strategy_type = StrategyType.CROSS_DEX
            if strategy_type_str == "triangular":
                strategy_type = StrategyType.TRIANGULAR
            elif strategy_type_str == "flash_loan":
                strategy_type = StrategyType.FLASH_LOAN
            elif strategy_type_str == "multi_path":
                strategy_type = StrategyType.MULTI_PATH
            
            # Create opportunity
            opportunity = ArbitrageOpportunity(
                id=legacy_opp.get("id", str(uuid.uuid4())),
                strategy_type=strategy_type,
                route=route,
                input_amount=legacy_opp.get("input_amount", 0),
                expected_output=legacy_opp.get("expected_output", 0),
                expected_profit=legacy_opp.get("expected_profit", 0),
                confidence_score=legacy_opp.get("confidence", 0.5),
                timestamp=legacy_opp.get("timestamp", time.time()),
                status=OpportunityStatus.VALID if legacy_opp.get("valid", True) else OpportunityStatus.INVALID,
                gas_estimate=legacy_opp.get("gas_estimate"),
                gas_price=legacy_opp.get("gas_price"),
                expiration_time=legacy_opp.get("expiration_time")
            )
            
            opportunities.append(opportunity)
        
        logger.info(f"Converted {len(opportunities)} legacy opportunities to new model")
        return opportunities


class LegacyExecutionManagerAdapter(ExecutionManager):
    """
    Adapter implementing ExecutionManager interface but delegating to legacy code.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the legacy execution manager adapter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.arbitrage_executor = ArbitrageExecutor(config)
        
        # Internal storage for registered strategies and monitors
        self.strategies = {}
        self.monitors = {}
        
        logger.info("Initialized legacy execution manager adapter")
    
    async def register_strategy(
        self, 
        strategy: ExecutionStrategy, 
        strategy_id: str
    ) -> None:
        """
        Register an execution strategy (not used in legacy mode).
        
        Args:
            strategy: The strategy to register
            strategy_id: Unique identifier for the strategy
        """
        logger.info(f"Registering strategy {strategy_id} (ignored in legacy mode)")
        self.strategies[strategy_id] = strategy
    
    async def register_monitor(
        self, 
        monitor: TransactionMonitor, 
        monitor_id: str
    ) -> None:
        """
        Register a transaction monitor (not used in legacy mode).
        
        Args:
            monitor: The monitor to register
            monitor_id: Unique identifier for the monitor
        """
        logger.info(f"Registering monitor {monitor_id} (ignored in legacy mode)")
        self.monitors[monitor_id] = monitor
    
    async def execute_opportunity(
        self, 
        opportunity: ArbitrageOpportunity,
        strategy_id: str = "default", 
        **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity using legacy code.
        
        Args:
            opportunity: The opportunity to execute
            strategy_id: ID of the strategy to use (ignored in legacy mode)
            **kwargs: Additional parameters
            
        Returns:
            Result of the execution
        """
        logger.info(f"Executing opportunity {opportunity.id} using legacy code")
        
        # Convert new model to legacy format
        legacy_opportunity = {
            "id": opportunity.id,
            "type": opportunity.strategy_type.value,
            "input_token": opportunity.route.input_token_address,
            "output_token": opportunity.route.output_token_address,
            "input_amount": opportunity.input_amount,
            "expected_output": opportunity.expected_output,
            "expected_profit": opportunity.expected_profit,
            "gas_estimate": opportunity.gas_estimate,
            "gas_price": opportunity.gas_price,
            "confidence": opportunity.confidence_score,
            "steps": []
        }
        
        # Add steps
        for step in opportunity.route.steps:
            legacy_step = {
                "dex": step.dex_id,
                "input_token": step.input_token_address,
                "output_token": step.output_token_address,
                "pool_address": step.pool_address,
                "input_amount": step.input_amount,
                "expected_output": step.expected_output,
                "min_output": step.min_output,
                "path": step.path_indexes,
                "fee_tier": step.fee_tier
            }
            legacy_opportunity["steps"].append(legacy_step)
        
        # Call legacy method to execute opportunity
        execution_start_time = time.time()
        legacy_result = await self.arbitrage_executor.execute_arbitrage(
            opportunity=legacy_opportunity,
            **kwargs
        )
        execution_duration = time.time() - execution_start_time
        
        # Convert legacy result to new model
        execution_id = legacy_result.get("id", str(uuid.uuid4()))
        
        # Determine execution status
        status_str = legacy_result.get("status", "failed")
        status = ExecutionStatus.FAILED
        if status_str == "success":
            status = ExecutionStatus.SUCCESS
        elif status_str == "pending":
            status = ExecutionStatus.PENDING
        elif status_str == "in_progress":
            status = ExecutionStatus.IN_PROGRESS
        
        # Create transaction details if available
        transaction_details = None
        if "transaction" in legacy_result:
            tx = legacy_result["transaction"]
            
            # Determine transaction status
            tx_status_str = tx.get("status", "unknown")
            tx_status = TransactionStatus.UNKNOWN
            if tx_status_str == "pending":
                tx_status = TransactionStatus.PENDING
            elif tx_status_str == "confirming":
                tx_status = TransactionStatus.CONFIRMING
            elif tx_status_str == "confirmed":
                tx_status = TransactionStatus.CONFIRMED
            elif tx_status_str == "failed":
                tx_status = TransactionStatus.FAILED
            elif tx_status_str == "reverted":
                tx_status = TransactionStatus.REVERTED
            
            transaction_details = TransactionDetails(
                hash=tx.get("hash", "0x"),
                from_address=tx.get("from", "0x"),
                to_address=tx.get("to", "0x"),
                value=tx.get("value", 0),
                gas_limit=tx.get("gas_limit", 0),
                gas_price=tx.get("gas_price", 0),
                nonce=tx.get("nonce", 0),
                data=tx.get("data", "0x"),
                chain_id=tx.get("chain_id", 1),
                status=tx_status,
                block_number=tx.get("block_number"),
                gas_used=tx.get("gas_used"),
                timestamp=tx.get("timestamp", time.time()),
                confirmation_time=tx.get("confirmation_time"),
                error_message=tx.get("error")
            )
        
        # Create error details if available
        error_details = None
        if "error" in legacy_result:
            error = legacy_result["error"]
            
            # Determine error type
            error_type_str = error.get("type", "unknown")
            error_type = ErrorType.UNKNOWN_ERROR
            if error_type_str == "validation":
                error_type = ErrorType.VALIDATION_ERROR
            elif error_type_str == "execution":
                error_type = ErrorType.EXECUTION_ERROR
            elif error_type_str == "transaction":
                error_type = ErrorType.TRANSACTION_ERROR
            elif error_type_str == "slippage":
                error_type = ErrorType.SLIPPAGE_ERROR
            elif error_type_str == "gas":
                error_type = ErrorType.GAS_ERROR
            
            error_details = ErrorDetails(
                type=error_type,
                message=error.get("message", "Unknown error"),
                timestamp=error.get("timestamp", time.time()),
                transaction_hash=error.get("transaction_hash"),
                retry_count=error.get("retry_count", 0),
                is_recoverable=error.get("is_recoverable", False)
            )
        
        # Create execution result
        execution_result = ExecutionResult(
            id=execution_id,
            opportunity_id=opportunity.id,
            status=status,
            timestamp=legacy_result.get("timestamp", time.time()),
            transaction_hash=legacy_result.get("transaction_hash"),
            transaction_details=transaction_details,
            success=legacy_result.get("success", False),
            actual_profit=legacy_result.get("actual_profit"),
            expected_profit=opportunity.expected_profit,
            gas_used=legacy_result.get("gas_used"),
            gas_price=legacy_result.get("gas_price"),
            error=error_details,
            completion_time=legacy_result.get("completion_time"),
            execution_duration=execution_duration,
            strategy_id=strategy_id,
            confirmations=legacy_result.get("confirmations", 0)
        )
        
        logger.info(f"Execution result created: {execution_id} with status {status.value}")
        return execution_result
    
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
        logger.info(f"Getting execution status for {execution_id} using legacy code")
        
        # Call legacy method to get execution status
        legacy_status = await self.arbitrage_executor.get_execution_status(execution_id)
        
        # Convert legacy status to new model
        status_str = legacy_status.get("status", "failed")
        status = ExecutionStatus.FAILED
        if status_str == "success":
            status = ExecutionStatus.SUCCESS
        elif status_str == "pending":
            status = ExecutionStatus.PENDING
        elif status_str == "in_progress":
            status = ExecutionStatus.IN_PROGRESS
        
        logger.info(f"Execution status: {status.value}")
        return status


class LegacyAnalyticsManagerAdapter(ArbitrageAnalytics):
    """
    Adapter implementing ArbitrageAnalytics interface but delegating to legacy code.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the legacy analytics manager adapter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.opportunity_tracker = OpportunityTracker(config)
        
        logger.info("Initialized legacy analytics manager adapter")
    
    async def record_opportunity(
        self, 
        opportunity: ArbitrageOpportunity
    ) -> None:
        """
        Record an arbitrage opportunity using legacy code.
        
        Args:
            opportunity: The opportunity to record
        """
        logger.info(f"Recording opportunity {opportunity.id} using legacy code")
        
        # Convert new model to legacy format
        legacy_opportunity = {
            "id": opportunity.id,
            "type": opportunity.strategy_type.value,
            "input_token": opportunity.route.input_token_address,
            "output_token": opportunity.route.output_token_address,
            "input_amount": opportunity.input_amount,
            "expected_output": opportunity.expected_output,
            "expected_profit": opportunity.expected_profit,
            "gas_estimate": opportunity.gas_estimate,
            "gas_price": opportunity.gas_price,
            "confidence": opportunity.confidence_score,
            "timestamp": opportunity.timestamp,
            "status": opportunity.status.value
        }
        
        # Call legacy method to record opportunity
        await self.opportunity_tracker.record_opportunity(legacy_opportunity)
    
    async def record_execution(
        self, 
        execution_result: ExecutionResult
    ) -> None:
        """
        Record an execution result using legacy code.
        
        Args:
            execution_result: The execution result to record
        """
        logger.info(f"Recording execution {execution_result.id} using legacy code")
        
        # Convert new model to legacy format
        legacy_execution = {
            "id": execution_result.id,
            "opportunity_id": execution_result.opportunity_id,
            "status": execution_result.status.value,
            "timestamp": execution_result.timestamp,
            "transaction_hash": execution_result.transaction_hash,
            "success": execution_result.success,
            "actual_profit": execution_result.actual_profit,
            "expected_profit": execution_result.expected_profit,
            "gas_used": execution_result.gas_used,
            "gas_price": execution_result.gas_price
        }
        
        # Call legacy method to record execution
        await self.opportunity_tracker.record_execution(legacy_execution)
    
    async def get_performance_metrics(
        self,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance metrics using legacy code.
        
        Args:
            time_period_days: Time period in days to calculate metrics for
            
        Returns:
            Dictionary of performance metrics
        """
        logger.info(f"Getting performance metrics using legacy code (time_period_days={time_period_days})")
        
        # Call legacy method to get metrics
        legacy_metrics = await self.opportunity_tracker.get_metrics(time_period_days)
        
        # Convert legacy metrics to new model
        metrics = {
            "opportunities_found": legacy_metrics.get("opportunities_found", 0),
            "opportunities_valid": legacy_metrics.get("opportunities_valid", 0),
            "opportunities_invalid": legacy_metrics.get("opportunities_invalid", 0),
            "executions_attempted": legacy_metrics.get("executions_attempted", 0),
            "executions_successful": legacy_metrics.get("executions_successful", 0),
            "executions_failed": legacy_metrics.get("executions_failed", 0),
            "total_profit": legacy_metrics.get("total_profit_wei", 0),
            "total_profit_eth": legacy_metrics.get("total_profit_eth", 0.0),
            "total_gas_used": legacy_metrics.get("total_gas_used", 0),
            "average_profit_per_execution": legacy_metrics.get("average_profit_eth", 0.0),
            "average_gas_per_execution": legacy_metrics.get("average_gas", 0),
            "success_rate": legacy_metrics.get("success_rate", 0.0),
            "average_execution_time": legacy_metrics.get("average_execution_time", 0.0),
            "timestamp": time.time()
        }
        
        logger.info(f"Performance metrics converted from legacy format")
        return metrics
    
    async def get_recent_opportunities(
        self,
        max_results: int = 100,
        min_profit_eth: float = 0.0
    ) -> List[ArbitrageOpportunity]:
        """
        Get recent arbitrage opportunities using legacy code.
        
        Args:
            max_results: Maximum number of opportunities to return
            min_profit_eth: Minimum profit threshold in ETH
            
        Returns:
            List of recent opportunities
        """
        logger.info(f"Getting recent opportunities using legacy code (max_results={max_results}, min_profit_eth={min_profit_eth})")
        
        # Call legacy method to get recent opportunities
        legacy_opportunities = await self.opportunity_tracker.get_recent_opportunities(
            max_results=max_results,
            min_profit_eth=min_profit_eth
        )
        
        # Convert legacy opportunities to new model
        opportunities = []
        for legacy_opp in legacy_opportunities:
            # Create route with minimal information (just enough for display)
            route = ArbitrageRoute(
                steps=[],
                input_token_address=legacy_opp.get("input_token", "0x"),
                output_token_address=legacy_opp.get("output_token", "0x"),
                input_amount=legacy_opp.get("input_amount", 0),
                expected_output=legacy_opp.get("expected_output", 0),
                expected_profit=legacy_opp.get("expected_profit", 0)
            )
            
            # Determine strategy type
            strategy_type_str = legacy_opp.get("type", "cross_dex")
            strategy_type = StrategyType.CROSS_DEX
            if strategy_type_str == "triangular":
                strategy_type = StrategyType.TRIANGULAR
            elif strategy_type_str == "flash_loan":
                strategy_type = StrategyType.FLASH_LOAN
            elif strategy_type_str == "multi_path":
                strategy_type = StrategyType.MULTI_PATH
            
            # Determine opportunity status
            status_str = legacy_opp.get("status", "pending")
            status = OpportunityStatus.PENDING
            if status_str == "valid":
                status = OpportunityStatus.VALID
            elif status_str == "invalid":
                status = OpportunityStatus.INVALID
            elif status_str == "executing":
                status = OpportunityStatus.EXECUTING
            elif status_str == "executed":
                status = OpportunityStatus.EXECUTED
            elif status_str == "failed":
                status = OpportunityStatus.FAILED
            
            # Create opportunity with minimal information (just enough for display)
            opportunity = ArbitrageOpportunity(
                id=legacy_opp.get("id", str(uuid.uuid4())),
                strategy_type=strategy_type,
                route=route,
                input_amount=legacy_opp.get("input_amount", 0),
                expected_output=legacy_opp.get("expected_output", 0),
                expected_profit=legacy_opp.get("expected_profit", 0),
                confidence_score=legacy_opp.get("confidence", 0.5),
                timestamp=legacy_opp.get("timestamp", time.time()),
                status=status,
                execution_id=legacy_opp.get("execution_id")
            )
            
            opportunities.append(opportunity)
        
        logger.info(f"Converted {len(opportunities)} legacy opportunities to new model")
        return opportunities
    
    async def get_recent_executions(
        self,
        max_results: int = 100
    ) -> List[ExecutionResult]:
        """
        Get recent execution results using legacy code.
        
        Args:
            max_results: Maximum number of executions to return
            
        Returns:
            List of recent executions
        """
        logger.info(f"Getting recent executions using legacy code (max_results={max_results})")
        
        # Call legacy method to get recent executions
        legacy_executions = await self.opportunity_tracker.get_recent_executions(
            max_results=max_results
        )
        
        # Convert legacy executions to new model
        executions = []
        for legacy_exec in legacy_executions:
            # Determine execution status
            status_str = legacy_exec.get("status", "failed")
            status = ExecutionStatus.FAILED
            if status_str == "success":
                status = ExecutionStatus.SUCCESS
            elif status_str == "pending":
                status = ExecutionStatus.PENDING
            elif status_str == "in_progress":
                status = ExecutionStatus.IN_PROGRESS
            
            # Create execution result with minimal information (just enough for display)
            execution_result = ExecutionResult(
                id=legacy_exec.get("id", str(uuid.uuid4())),
                opportunity_id=legacy_exec.get("opportunity_id", ""),
                status=status,
                timestamp=legacy_exec.get("timestamp", time.time()),
                transaction_hash=legacy_exec.get("transaction_hash"),
                success=legacy_exec.get("success", False),
                actual_profit=legacy_exec.get("actual_profit"),
                expected_profit=legacy_exec.get("expected_profit"),
                gas_used=legacy_exec.get("gas_used"),
                gas_price=legacy_exec.get("gas_price"),
                completion_time=legacy_exec.get("completion_time")
            )
            
            executions.append(execution_result)
        
        logger.info(f"Converted {len(executions)} legacy executions to new model")
        return executions


class LegacyMarketDataProviderAdapter(MarketDataProvider):
    """
    Adapter implementing MarketDataProvider interface but delegating to legacy code.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the legacy market data provider adapter.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.market_data_manager = MarketDataManager(config)
        self.callbacks = []
        self._monitoring = False
        self._update_task = None
        
        logger.info("Initialized legacy market data provider adapter")
    
    async def get_current_market_condition(
        self
    ) -> Dict[str, Any]:
        """
        Get the current market condition using legacy code.
        
        Returns:
            Current market state and prices
        """
        logger.info("Getting current market condition using legacy code")
        
        # Call legacy method to get market condition
        legacy_market_condition = await self.market_data_manager.get_current_market_data()
        
        # Convert legacy market condition to new model
        market_condition = {
            "timestamp": time.time(),
            "prices": legacy_market_condition.get("prices", {}),
            "pools": legacy_market_condition.get("pools", {}),
            "gas_price": legacy_market_condition.get("gas_price", 0),
            "block_number": legacy_market_condition.get("block_number", 0)
        }
        
        return market_condition
    
    async def register_market_update_callback(
        self,
        callback: callable
    ) -> None:
        """
        Register a callback for market updates.
        
        Args:
            callback: Function to call when market updates occur
        """
        logger.info("Registering market update callback")
        self.callbacks.append(callback)
    
    async def start_monitoring(
        self,
        update_interval_seconds: float = 60.0
    ) -> None:
        """
        Start monitoring market conditions.
        
        Args:
            update_interval_seconds: Time between updates in seconds
        """
        if self._monitoring:
            logger.warning("Market monitoring already started")
            return
        
        logger.info(f"Starting market monitoring with interval {update_interval_seconds}s")
        self._monitoring = True
        
        # Start update task
        self._update_task = asyncio.create_task(
            self._update_loop(update_interval_seconds)
        )
    
    async def stop_monitoring(
        self
    ) -> None:
        """Stop monitoring market conditions."""
        if not self._monitoring:
            logger.warning("Market monitoring not started")
            return
        
        logger.info("Stopping market monitoring")
        self._monitoring = False
        
        # Cancel update task
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            self._update_task = None
    
    async def _update_loop(
        self,
        update_interval_seconds: float
    ) -> None:
        """
        Background task for updating market conditions.
        
        Args:
            update_interval_seconds: Time between updates in seconds
        """
        logger.info("Starting market update loop")
        
        while self._monitoring:
            try:
                # Get current market condition
                market_condition = await self.get_current_market_condition()
                
                # Call registered callbacks
                for callback in self.callbacks:
                    try:
                        await callback(market_condition)
                    except Exception as e:
                        logger.error(f"Error in market update callback: {e}", exc_info=True)
            
            except asyncio.CancelledError:
                logger.info("Market update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in market update loop: {e}", exc_info=True)
            
            # Wait for next update
            try:
                await asyncio.sleep(update_interval_seconds)
            except asyncio.CancelledError:
                break
        
        logger.info("Market update loop stopped")