"""
Execution Adapter

This module contains adapters to integrate existing execution components
with the new arbitrage system architecture.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from ..interfaces import ExecutionStrategy, TransactionMonitor
from ..models import ArbitrageOpportunity, ExecutionResult, ExecutionStatus
from ...execution.arbitrage_executor import ArbitrageExecutor

logger = logging.getLogger(__name__)


class ArbitrageExecutorAdapter(ExecutionStrategy):
    """
    Adapter that converts the existing ArbitrageExecutor implementation
    to work with the new ExecutionStrategy interface.
    """

    def __init__(
        self,
        arbitrage_executor: ArbitrageExecutor,
        flash_loan_manager: Any,
        web3_manager: Any,
        config: Dict[str, Any] = None,
    ):
        """
        Initialize the execution strategy.

        Args:
            arbitrage_executor: Existing ArbitrageExecutor instance
            flash_loan_manager: FlashLoanManager instance
            web3_manager: Web3Manager instance for blockchain interactions
            config: Configuration dictionary
        """
        self.arbitrage_executor = arbitrage_executor
        self.flash_loan_manager = flash_loan_manager
        self.web3_manager = web3_manager
        self.config = config or {}

        logger.info("ArbitrageExecutorAdapter initialized")

    async def execute_opportunity(
        self, opportunity: ArbitrageOpportunity, **kwargs
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.

        Args:
            opportunity: Opportunity to execute
            **kwargs: Additional execution-specific parameters

        Returns:
            Result of the execution
        """
        logger.info(f"Executing opportunity {opportunity.id}")

        try:
            # Convert to format expected by ArbitrageExecutor
            execution_data = self._convert_to_execution_data(opportunity)

            # Execute opportunity
            result = await self.arbitrage_executor.execute_arbitrage(
                execution_data, **kwargs
            )

            # Check execution result
            if not result or not result.get("success", False):
                logger.warning(f"Execution failed for opportunity {opportunity.id}")
                error_message = (
                    result.get("error", "Unknown execution error")
                    if result
                    else "No execution result"
                )

                return ExecutionResult(
                    opportunity_id=opportunity.id,
                    success=False,
                    status=ExecutionStatus.FAILED,
                    error_message=error_message,
                    timestamp=time.time(),
                )

            # Create successful result
            tx_hash = result.get("transaction_hash")
            gas_used = result.get("gas_used")
            actual_profit = result.get("actual_profit")

            return ExecutionResult(
                opportunity_id=opportunity.id,
                success=True,
                transaction_hash=tx_hash,
                status=ExecutionStatus.PENDING,  # Will be updated by monitor
                gas_used=gas_used,
                actual_profit=actual_profit,
                timestamp=time.time(),
            )

        except Exception as e:
            logger.error(f"Error executing opportunity {opportunity.id}: {e}")
            return ExecutionResult(
                opportunity_id=opportunity.id,
                success=False,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                timestamp=time.time(),
            )

    def _convert_to_execution_data(
        self, opportunity: ArbitrageOpportunity
    ) -> Dict[str, Any]:
        """Convert ArbitrageOpportunity to format expected by ArbitrageExecutor."""
        # Extract route information
        route = []
        for step in opportunity.route.steps:
            route.append(
                {
                    "dex": step.dex_id,
                    "token_in": step.token_in_address,
                    "token_out": step.token_out_address,
                    "pool_address": step.pool_address,
                    "fee": step.pool_fee,
                    "pool_type": step.pool_type,
                }
            )

        # Create execution data
        return {
            "id": opportunity.id,
            "input_token": opportunity.route.input_token_address,
            "output_token": opportunity.route.output_token_address,
            "amount_in": opportunity.input_amount,
            "expected_output": opportunity.expected_output,
            "profit": opportunity.expected_profit,
            "route": route,
            "strategy": opportunity.strategy_type.value,
            "gas_limit": opportunity.gas_estimate.gas_limit,
            "gas_price": opportunity.gas_estimate.gas_price,
        }


class TransactionMonitorAdapter(TransactionMonitor):
    """
    Adapter for monitoring transactions using the existing infrastructure.
    """

    def __init__(self, web3_manager: Any, config: Dict[str, Any] = None):
        """
        Initialize the transaction monitor.

        Args:
            web3_manager: Web3Manager instance for blockchain interactions
            config: Configuration dictionary
        """
        self.web3_manager = web3_manager
        self.config = config or {}

        logger.info("TransactionMonitorAdapter initialized")

    async def monitor_transaction(
        self, transaction_hash: str, timeout_seconds: int = 60, **kwargs
    ) -> ExecutionResult:
        """
        Monitor a transaction until it completes or times out.

        Args:
            transaction_hash: Hash of the transaction to monitor
            timeout_seconds: How long to monitor before timing out
            **kwargs: Additional monitoring parameters

        Returns:
            Execution result with final status
        """
        logger.info(f"Monitoring transaction {transaction_hash}")

        opportunity_id = kwargs.get("opportunity_id", "unknown")
        start_time = time.time()
        end_time = start_time + timeout_seconds

        try:
            # Initialize result
            result = ExecutionResult(
                opportunity_id=opportunity_id,
                success=False,
                transaction_hash=transaction_hash,
                status=ExecutionStatus.PENDING,
                timestamp=start_time,
            )

            # Wait for transaction to be mined with timeout
            while time.time() < end_time:
                try:
                    # Get transaction receipt
                    tx_receipt = await self.web3_manager.get_transaction_receipt(
                        transaction_hash
                    )

                    if tx_receipt:
                        # Transaction was mined
                        status = tx_receipt.get("status")

                        if status == 1:
                            # Transaction successful
                            result.status = ExecutionStatus.CONFIRMED
                            result.success = True
                            result.block_number = tx_receipt.get("blockNumber")
                            result.gas_used = tx_receipt.get("gasUsed")
                            result.receipt = tx_receipt

                            # If profit not provided, try to calculate from receipt
                            if not result.actual_profit and kwargs.get(
                                "calculate_profit", False
                            ):
                                result.actual_profit = (
                                    await self._calculate_profit_from_receipt(
                                        tx_receipt, kwargs.get("opportunity")
                                    )
                                )

                            logger.info(
                                f"Transaction {transaction_hash} confirmed successfully"
                            )
                            return result
                        else:
                            # Transaction failed
                            result.status = ExecutionStatus.FAILED
                            result.success = False
                            result.block_number = tx_receipt.get("blockNumber")
                            result.gas_used = tx_receipt.get("gasUsed")
                            result.receipt = tx_receipt
                            result.error_message = "Transaction reverted on-chain"

                            logger.warning(
                                f"Transaction {transaction_hash} failed on-chain"
                            )
                            return result

                    # Wait before checking again
                    await asyncio.sleep(2)

                except Exception as e:
                    logger.error(f"Error checking transaction {transaction_hash}: {e}")
                    await asyncio.sleep(2)

            # Timeout reached
            result.status = ExecutionStatus.TIMEOUT
            result.error_message = (
                f"Transaction monitoring timed out after {timeout_seconds} seconds"
            )
            logger.warning(f"Monitoring timed out for transaction {transaction_hash}")
            return result

        except Exception as e:
            logger.error(f"Error monitoring transaction {transaction_hash}: {e}")
            return ExecutionResult(
                opportunity_id=opportunity_id,
                success=False,
                transaction_hash=transaction_hash,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                timestamp=time.time(),
            )

    async def _calculate_profit_from_receipt(
        self, receipt: Dict[str, Any], opportunity: Optional[ArbitrageOpportunity]
    ) -> Optional[int]:
        """Try to calculate actual profit from transaction receipt."""
        # This would require parsing events from the receipt
        # For simplicity, we'll return None for now
        return None


async def create_execution_adapter(
    arbitrage_executor: Optional[ArbitrageExecutor] = None,
    flash_loan_manager: Optional[Any] = None,
    web3_manager: Optional[Any] = None,
    gas_optimizer: Optional[Any] = None,
    config: Dict[str, Any] = None,
) -> ArbitrageExecutorAdapter:
    """
    Create and initialize an execution adapter.

    Args:
        arbitrage_executor: Existing ArbitrageExecutor instance, or None to create new
        flash_loan_manager: FlashLoanManager instance
        web3_manager: Web3Manager instance for blockchain interactions
        gas_optimizer: GasOptimizer instance (optional)
        config: Configuration dictionary

    Returns:
        Initialized execution adapter
    """
    from ...execution.arbitrage_executor import create_arbitrage_executor

    # Create arbitrage executor if not provided
    if arbitrage_executor is None:
        if flash_loan_manager is None or web3_manager is None:
            raise ValueError(
                "Either arbitrage_executor or both flash_loan_manager and web3_manager must be provided"
            )

        arbitrage_executor = await create_arbitrage_executor(
            web3_manager=web3_manager,
            flash_loan_manager=flash_loan_manager,
            gas_optimizer=gas_optimizer,
            config=config,
        )

    # Create adapter
    adapter = ArbitrageExecutorAdapter(
        arbitrage_executor=arbitrage_executor,
        flash_loan_manager=flash_loan_manager,
        web3_manager=web3_manager,
        config=config,
    )

    return adapter


async def create_transaction_monitor_adapter(
    web3_manager: Any, config: Dict[str, Any] = None
) -> TransactionMonitorAdapter:
    """
    Create and initialize a transaction monitor adapter.

    Args:
        web3_manager: Web3Manager instance for blockchain interactions
        config: Configuration dictionary

    Returns:
        Initialized transaction monitor adapter
    """
    return TransactionMonitorAdapter(web3_manager=web3_manager, config=config)
