"""
Flashbots Execution Strategy

This module contains the implementation of a Flashbots-based execution strategy
for arbitrage opportunities, which uses Flashbots to protect transactions from MEV.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, cast, Union
from decimal import Decimal

from ....web3.interfaces import Web3Client, Transaction, TransactionReceipt
from ....web3.flashbots import (
    FlashbotsProvider,
    FlashbotsBundle,
    BundleSimulator,
    FlashbotsBundleResponse,
    SimulationResult,
    create_flashbots_provider,
    create_flashbots_bundle,
    create_bundle_simulator,
)
from ...interfaces import ExecutionStrategy, ArbitrageOpportunity, ExecutionResult
from ...models import (
    ArbitrageOpportunity,
    ArbitrageStep,
    TransactionInfo,
    ExecutionResult,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


class FlashbotsExecutionStrategy(ExecutionStrategy):
    """
    Execution strategy that uses Flashbots for MEV protection.

    This strategy:
    1. Builds transaction bundles from arbitrage steps
    2. Simulates bundles to validate profitability
    3. Submits bundles privately via Flashbots
    4. Monitors bundle inclusion and execution
    """

    def __init__(self, web3_client: Web3Client, config: Dict[str, Any] = None):
        """
        Initialize the Flashbots execution strategy.

        Args:
            web3_client: Web3 client for blockchain interactions
            config: Configuration parameters for the strategy
        """
        self.web3_client = web3_client
        self.config = config or {}

        # Configuration
        self.flashbots_endpoint = self.config.get(
            "flashbots_endpoint", "https://relay.flashbots.net"
        )
        self.auth_signer_key = self.config.get("auth_signer_key", None)
        self.simulation_required = bool(self.config.get("simulation_required", True))
        self.min_profit_wei = int(self.config.get("min_profit_wei", 0))
        self.max_attempts = int(self.config.get("max_attempts", 3))
        self.inclusion_timeout = float(
            self.config.get("inclusion_timeout", 60.0)
        )  # 60 seconds
        self.block_wait_time = float(
            self.config.get("block_wait_time", 12.0)
        )  # ~12 seconds per block

        # Flashbots components
        self.flashbots_provider: Optional[FlashbotsProvider] = None
        self.bundle_simulator: Optional[BundleSimulator] = None

        # State
        self._execution_lock = asyncio.Lock()
        self._execution_stats = {
            "total_executed": 0,
            "successful": 0,
            "failed": 0,
            "aborted": 0,
            "errors": {},
        }

        logger.info("FlashbotsExecutionStrategy initialized")

    async def initialize(self) -> None:
        """Initialize the strategy by setting up Flashbots components."""
        logger.info("Initializing FlashbotsExecutionStrategy")

        try:
            # Create Flashbots provider
            self.flashbots_provider = await create_flashbots_provider(
                web3_client=self.web3_client,
                auth_signer_key=self.auth_signer_key,
                flashbots_endpoint=self.flashbots_endpoint,
                config=self.config.get("flashbots_provider_config", {}),
            )

            # Create bundle simulator
            self.bundle_simulator = await create_bundle_simulator(
                web3_client=self.web3_client,
                flashbots_provider=self.flashbots_provider,
                config=self.config.get("simulator_config", {}),
            )

            logger.info("FlashbotsExecutionStrategy initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing FlashbotsExecutionStrategy: {e}")
            raise

    async def execute(self, opportunity: ArbitrageOpportunity) -> ExecutionResult:
        """
        Execute an arbitrage opportunity using Flashbots.

        Args:
            opportunity: The arbitrage opportunity to execute

        Returns:
            Execution result with status, transactions, and profit information
        """
        async with self._execution_lock:
            logger.info(f"Executing opportunity {opportunity.id} with Flashbots")
            self._execution_stats["total_executed"] += 1

            execution_start = time.time()

            # Initialize result with pending status
            result = ExecutionResult(
                opportunity_id=opportunity.id,
                status=ExecutionStatus.PENDING,
                transactions=[],
                execution_time=0,
                profit_wei=0,
                cost_wei=0,
                error_message=None,
            )

            try:
                # Ensure Flashbots components are initialized
                if not self.flashbots_provider or not self.bundle_simulator:
                    await self.initialize()

                # Build and execute bundle
                bundle_result = await self._execute_with_flashbots(opportunity)

                # Process execution result
                if bundle_result.status == ExecutionStatus.SUCCESS:
                    self._execution_stats["successful"] += 1
                    logger.info(f"Opportunity {opportunity.id} executed successfully")
                elif bundle_result.status == ExecutionStatus.ABORTED:
                    self._execution_stats["aborted"] += 1
                    logger.warning(
                        f"Opportunity {opportunity.id} execution aborted: {bundle_result.error_message}"
                    )
                else:
                    self._execution_stats["failed"] += 1
                    error = bundle_result.error_message or "Unknown error"
                    self._execution_stats["errors"][error] = (
                        self._execution_stats["errors"].get(error, 0) + 1
                    )
                    logger.error(
                        f"Opportunity {opportunity.id} execution failed: {error}"
                    )

                # Calculate execution time
                bundle_result.execution_time = time.time() - execution_start

                return bundle_result

            except Exception as e:
                error_message = f"Error in Flashbots execution: {e}"
                self._execution_stats["failed"] += 1
                self._execution_stats["errors"][str(e)] = (
                    self._execution_stats["errors"].get(str(e), 0) + 1
                )

                logger.error(error_message)

                # Update result with error
                result.status = ExecutionStatus.FAILED
                result.error_message = error_message
                result.execution_time = time.time() - execution_start

                return result

    async def _execute_with_flashbots(
        self, opportunity: ArbitrageOpportunity
    ) -> ExecutionResult:
        """
        Execute an opportunity with Flashbots.

        Args:
            opportunity: Arbitrage opportunity to execute

        Returns:
            Execution result with details
        """
        # Initialize result
        result = ExecutionResult(
            opportunity_id=opportunity.id,
            status=ExecutionStatus.PENDING,
            transactions=[],
            execution_time=0,
            profit_wei=0,
            cost_wei=0,
            error_message=None,
        )

        # Create a bundle
        bundle = await create_flashbots_bundle(
            web3_client=self.web3_client,
            flashbots_provider=self.flashbots_provider,
            config=self.config.get("bundle_config", {}),
        )

        # Build transactions from opportunity steps
        transactions = await self._build_transactions_from_steps(opportunity.steps)

        if not transactions:
            result.status = ExecutionStatus.ABORTED
            result.error_message = (
                "No valid transactions could be built from opportunity steps"
            )
            return result

        # Add transactions to bundle
        await bundle.add_transactions(transactions)

        # Simulate bundle if required
        if self.simulation_required:
            simulation_result = await bundle.simulate()

            if not simulation_result or not simulation_result.get("success", False):
                error = (
                    simulation_result.get("error", "Unknown simulation error")
                    if simulation_result
                    else "Simulation failed"
                )
                result.status = ExecutionStatus.ABORTED
                result.error_message = f"Simulation error: {error}"
                return result

            # Check profitability
            if (
                not simulation_result.get("profitable", False)
                and self.min_profit_wei > 0
            ):
                profit = simulation_result.get("profit_wei", 0)
                result.status = ExecutionStatus.ABORTED
                result.error_message = (
                    f"Not profitable: {profit} wei < {self.min_profit_wei} wei minimum"
                )
                return result

            # Store profit and cost from simulation
            result.profit_wei = simulation_result.get("profit_wei", 0)
            result.cost_wei = simulation_result.get("cost_wei", 0)

        # Submit bundle
        bundle_response = await bundle.submit()

        if not bundle_response:
            result.status = ExecutionStatus.FAILED
            result.error_message = "Failed to submit bundle"
            return result

        # Track transaction hashes
        for tx_hash in bundle.tx_hashes:
            result.transactions.append(
                TransactionInfo(
                    transaction_hash=tx_hash,
                    status=None,
                    block_number=None,
                    timestamp=int(time.time()),
                )
            )

        # Wait for inclusion
        inclusion_success = await bundle.wait_for_inclusion(
            bundle_hash=bundle_response.bundle_hash, timeout=self.inclusion_timeout
        )

        if not inclusion_success:
            result.status = ExecutionStatus.FAILED
            result.error_message = (
                f"Bundle not included within {self.inclusion_timeout} seconds"
            )
            return result

        # Get transaction receipts
        receipts = await bundle.get_tx_receipts()

        # Update transaction info with receipts
        for i, receipt in enumerate(receipts):
            if i < len(result.transactions) and receipt:
                result.transactions[i].status = receipt.status
                result.transactions[i].block_number = receipt.block_number
                result.transactions[i].gas_used = receipt.gas_used
                result.transactions[i].effective_gas_price = receipt.effective_gas_price

        # Check if all transactions succeeded
        all_success = all(
            tx.status == True for tx in result.transactions if tx.status is not None
        )

        if all_success:
            result.status = ExecutionStatus.SUCCESS
        else:
            result.status = ExecutionStatus.FAILED
            result.error_message = "One or more transactions failed"

        return result

    async def _build_transactions_from_steps(
        self, steps: List[ArbitrageStep]
    ) -> List[Transaction]:
        """
        Build transactions from arbitrage steps.

        Args:
            steps: List of arbitrage steps

        Returns:
            List of transactions
        """
        transactions: List[Transaction] = []

        for step in steps:
            try:
                # Build transaction from step
                tx = Transaction(
                    from_address=step.from_address,
                    to_address=step.to_address,
                    data=step.data,
                    value=step.value,
                    gas=step.gas_limit,
                    gas_price=step.gas_price,
                    max_fee_per_gas=step.max_fee_per_gas,
                    max_priority_fee_per_gas=step.priority_fee,
                    nonce=None,  # Will be set automatically by the bundle
                )

                transactions.append(tx)

            except Exception as e:
                logger.error(
                    f"Error building transaction from step {step.step_id}: {e}"
                )

        return transactions

    async def abort(self, opportunity_id: str) -> bool:
        """
        Attempt to abort an ongoing execution.

        Args:
            opportunity_id: ID of the opportunity to abort

        Returns:
            True if abort was successful, False otherwise
        """
        logger.warning(f"Abort requested for opportunity {opportunity_id}")
        self._execution_stats["aborted"] += 1

        # We can't truly abort a submitted bundle, but this interface is required
        # In a real implementation, we might track executions by ID and cancel
        # any pending bundles that haven't been included yet

        return False

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary of execution statistics
        """
        stats = self._execution_stats.copy()

        # Add success rate
        total = stats["total_executed"]
        if total > 0:
            stats["success_rate"] = stats["successful"] / total
        else:
            stats["success_rate"] = 0.0

        # Add simulator stats if available
        if self.bundle_simulator:
            simulator_stats = self.bundle_simulator.get_statistics()
            stats["simulator"] = simulator_stats

        return stats

    async def close(self) -> None:
        """Close the strategy and release resources."""
        logger.info("Closing FlashbotsExecutionStrategy")

        if self.flashbots_provider:
            await self.flashbots_provider.close()

        # No specific cleanup needed for simulator


async def create_flashbots_strategy(
    web3_client: Web3Client, config: Dict[str, Any] = None
) -> FlashbotsExecutionStrategy:
    """
    Factory function to create a Flashbots execution strategy.

    Args:
        web3_client: Web3 client for blockchain interactions
        config: Configuration parameters

    Returns:
        Initialized Flashbots execution strategy
    """
    strategy = FlashbotsExecutionStrategy(web3_client=web3_client, config=config)

    await strategy.initialize()
    return strategy
