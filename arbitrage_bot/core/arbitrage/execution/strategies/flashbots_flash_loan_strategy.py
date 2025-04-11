"""
Flashbots Flash Loan Strategy

This module implements a strategy that combines flash loans with Flashbots
protection to execute arbitrage opportunities with maximum capital efficiency
and MEV protection.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union, Tuple

from ....finance.flash_loans.factory import FlashLoanFactory
from ....finance.flash_loans.interfaces import FlashLoanProvider, FlashLoanTransaction
from ....web3.flashbots.interfaces import FlashbotsBundle, BundleSimulationResult
from ....web3.flashbots.provider import FlashbotsProvider
from ....web3.flashbots.simulator import BundleSimulator
from ....web3.interfaces import Web3Client, Transaction
from ...interfaces import ArbitrageOpportunity
from ...execution.interfaces import ExecutionStrategy, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class FlashbotsFlashLoanStrategy(ExecutionStrategy):
    """
    A strategy that combines flash loans with Flashbots to execute arbitrage
    opportunities with maximum capital efficiency and MEV protection.

    This strategy uses flash loans to provide the capital for arbitrage,
    and Flashbots to protect against front-running and other MEV attacks.
    """

    def __init__(
        self,
        web3_client: Web3Client,
        flashbots_provider: FlashbotsProvider,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the Flashbots flash loan strategy.

        Args:
            web3_client: Web3 client for blockchain interactions
            flashbots_provider: Provider for Flashbots interactions
            config: Configuration parameters for the strategy
        """
        self.web3_client = web3_client
        self.flashbots_provider = flashbots_provider
        self.config = config or {}

        # Configuration
        self.flash_loan_config = self.config.get("flash_loan", {})
        self.flashbots_config = self.config.get("flashbots", {})

        # Parameters
        self.slippage_tolerance = Decimal(
            self.flash_loan_config.get("slippage_tolerance", "0.005")
        )
        self.profit_threshold_multiplier = Decimal(
            self.flash_loan_config.get("profit_threshold_multiplier", "1.5")
        )
        self.gas_buffer = Decimal(self.flash_loan_config.get("gas_buffer", "1.2"))
        self.max_wait_blocks = self.flashbots_config.get("max_wait_blocks", 5)

        # Components
        self.flash_loan_factory = None
        self.bundle_simulator = None

        # State
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """
        Initialize the strategy.

        This method sets up the flash loan factory and simulator,
        and ensures the strategy is ready for use.

        Returns:
            True if initialization succeeds, False otherwise
        """
        async with self._initialization_lock:
            if self._is_initialized:
                logger.debug("Flashbots flash loan strategy already initialized")
                return True

            try:
                logger.info("Initializing Flashbots flash loan strategy")

                # Initialize flash loan factory
                self.flash_loan_factory = FlashLoanFactory(
                    self.web3_client, config=self.flash_loan_config
                )
                await self.flash_loan_factory.initialize()

                # Initialize bundle simulator
                self.bundle_simulator = BundleSimulator(
                    self.web3_client, config=self.flashbots_config
                )
                await self.bundle_simulator.initialize()

                # Ensure Flashbots provider is initialized
                if not self.flashbots_provider._is_initialized:
                    await self.flashbots_provider.initialize()

                self._is_initialized = True
                logger.info("Flashbots flash loan strategy initialized successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to initialize Flashbots flash loan strategy: {e}")
                return False

    async def _ensure_initialized(self) -> None:
        """Ensure the strategy is initialized."""
        if not self._is_initialized:
            success = await self.initialize()
            if not success:
                raise RuntimeError("Failed to initialize Flashbots flash loan strategy")

    async def is_applicable(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Check if this strategy is applicable to the given opportunity.

        This strategy is applicable if flash loans are available for the
        required tokens and the opportunity is sufficiently profitable.

        Args:
            opportunity: Arbitrage opportunity to check

        Returns:
            True if the strategy is applicable, False otherwise
        """
        await self._ensure_initialized()

        try:
            # Check if flash loans are available
            flash_loan_token = opportunity.start_token
            flash_loan_amount = opportunity.required_amount

            provider = await self.flash_loan_factory.get_provider(
                flash_loan_token, flash_loan_amount
            )

            if not provider:
                logger.info(f"No flash loan provider available for {flash_loan_token}")
                return False

            # Check if the opportunity is sufficiently profitable
            return await self.is_profitable(opportunity)

        except Exception as e:
            logger.error(f"Error checking applicability: {e}")
            return False

    async def is_profitable(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Check if the opportunity is profitable using this strategy.

        This method takes into account flash loan fees, gas costs,
        and slippage to determine if the opportunity is profitable.

        Args:
            opportunity: Arbitrage opportunity to check

        Returns:
            True if the opportunity is profitable, False otherwise
        """
        await self._ensure_initialized()

        try:
            # Get flash loan provider and fee
            provider = await self.flash_loan_factory.get_provider(
                opportunity.start_token, opportunity.required_amount
            )

            if not provider:
                logger.info(
                    f"No flash loan provider available for {opportunity.start_token}"
                )
                return False

            fee_rate = provider.get_fee_rate()

            # Calculate flash loan fee
            flash_loan_fee = opportunity.required_amount * fee_rate

            # Estimate gas cost
            estimated_cost = await self.get_estimated_cost(opportunity)

            # Calculate minimum profit
            min_profit = flash_loan_fee + estimated_cost

            # Apply profit threshold multiplier
            required_profit = min_profit * self.profit_threshold_multiplier

            # Check if the opportunity is profitable
            is_profitable = opportunity.profit_amount > required_profit

            logger.info(
                f"Profit check: profit={opportunity.profit_amount}, "
                f"required={required_profit}, profitable={is_profitable}"
            )

            return is_profitable

        except Exception as e:
            logger.error(f"Error checking profitability: {e}")
            return False

    async def get_estimated_cost(self, opportunity: ArbitrageOpportunity) -> Decimal:
        """
        Get the estimated cost of executing the opportunity.

        This method estimates the gas cost of executing the opportunity,
        including flash loan and arbitrage transactions.

        Args:
            opportunity: Arbitrage opportunity to estimate cost for

        Returns:
            Estimated cost in the opportunity's start token
        """
        await self._ensure_initialized()

        try:
            # Get gas price
            gas_price = await self.web3_client.get_gas_price()

            # Estimate gas usage
            # This is a rough estimate and should be refined based on actual usage
            gas_estimate = 500000  # Base estimate for flash loan + arbitrage

            # Apply gas buffer for safety
            gas_with_buffer = int(gas_estimate * self.gas_buffer)

            # Calculate cost in ETH
            cost_eth = Decimal(gas_with_buffer) * Decimal(gas_price) / Decimal(10**18)

            # Convert to token cost
            # This is a simplified conversion and should be replaced with actual price
            # For now, we'll use a fixed conversion factor
            eth_price = Decimal("2000")  # ETH price in USD
            token_price = Decimal("1")  # Token price in USD
            token_cost = cost_eth * eth_price / token_price

            logger.debug(
                f"Estimated cost: gas={gas_with_buffer}, "
                f"gas_price={gas_price}, cost_eth={cost_eth}, "
                f"token_cost={token_cost}"
            )

            return token_cost

        except Exception as e:
            logger.error(f"Error estimating cost: {e}")
            return Decimal("0.01")  # Default cost estimate

    async def execute(
        self,
        opportunity: ArbitrageOpportunity,
        execution_params: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute the arbitrage opportunity using flash loans and Flashbots.

        This method borrows the required capital using a flash loan,
        executes the arbitrage, and repays the loan, all within a
        Flashbots bundle for MEV protection.

        Args:
            opportunity: Arbitrage opportunity to execute
            execution_params: Additional parameters for execution

        Returns:
            Result of the execution
        """
        await self._ensure_initialized()

        execution_params = execution_params or {}

        # Create a default result with status=FAILED
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            opportunity=opportunity,
            transaction_hash=None,
            gas_used=0,
            gas_price=0,
            profit_amount=Decimal("0"),
            profit_token=opportunity.start_token,
            error_message="Execution not attempted",
        )

        try:
            logger.info(f"Executing arbitrage opportunity: {opportunity}")

            # Check if the opportunity is profitable
            if not await self.is_profitable(opportunity):
                logger.warning("Opportunity is not profitable, skipping execution")
                result.error_message = "Opportunity is not profitable"
                return result

            # Get flash loan provider
            provider = await self.flash_loan_factory.get_provider(
                opportunity.start_token, opportunity.required_amount
            )

            if not provider:
                logger.error(
                    f"No flash loan provider available for {opportunity.start_token}"
                )
                result.error_message = "No flash loan provider available"
                return result

            # Prepare flash loan transaction
            flash_loan_tx = await self._prepare_flash_loan_transaction(
                provider, opportunity, execution_params
            )

            if not flash_loan_tx:
                logger.error("Failed to prepare flash loan transaction")
                result.error_message = "Failed to prepare flash loan transaction"
                return result

            # Create Flashbots bundle
            bundle = await self._create_flashbots_bundle(
                flash_loan_tx, execution_params
            )

            if not bundle:
                logger.error("Failed to create Flashbots bundle")
                result.error_message = "Failed to create Flashbots bundle"
                return result

            # Sign bundle
            signed_bundle = await self.flashbots_provider.sign_bundle(bundle)

            # Simulate bundle
            simulation_result = await self.bundle_simulator.simulate(signed_bundle)

            if not simulation_result.success:
                logger.error(f"Bundle simulation failed: {simulation_result.error}")
                result.error_message = (
                    f"Bundle simulation failed: {simulation_result.error}"
                )
                return result

            # Verify profitability from simulation
            is_profitable = await self.bundle_simulator.verify_profitability(
                simulation_result,
                min_profit_threshold=float(
                    execution_params.get("min_profit_threshold", 0.001)
                ),
            )

            if not is_profitable:
                logger.warning("Bundle is not profitable based on simulation")
                result.error_message = "Bundle is not profitable based on simulation"
                return result

            # Submit bundle
            submission_result = await self.flashbots_provider.submit_bundle(
                signed_bundle
            )

            if not submission_result.success:
                logger.error(f"Bundle submission failed: {submission_result.error}")
                result.error_message = (
                    f"Bundle submission failed: {submission_result.error}"
                )
                return result

            logger.info(f"Bundle submitted: {submission_result.bundle_hash}")

            # Wait for bundle inclusion
            target_block = (
                await self.web3_client.get_block_number() + bundle.blocks_into_future
            )
            stats = await self.flashbots_provider.wait_for_bundle_inclusion(
                submission_result.bundle_hash,
                target_block,
                max_wait_blocks=self.max_wait_blocks,
            )

            if not stats or not stats.get("is_included"):
                logger.warning(
                    f"Bundle not included within {self.max_wait_blocks} blocks"
                )
                result.error_message = (
                    f"Bundle not included within {self.max_wait_blocks} blocks"
                )
                return result

            # Bundle was included, update result
            block_number = stats.get("block_number")
            transaction_hash = stats.get("transaction_hash")
            gas_used = stats.get("gas_used", 0)
            gas_price = stats.get("gas_price", 0)

            logger.info(
                f"Bundle included in block {block_number}, "
                f"transaction hash: {transaction_hash}"
            )

            # Calculate actual profit
            actual_profit = await self._calculate_actual_profit(
                opportunity, stats, simulation_result
            )

            result.status = ExecutionStatus.EXECUTED
            result.transaction_hash = transaction_hash
            result.gas_used = gas_used
            result.gas_price = gas_price
            result.profit_amount = actual_profit
            result.error_message = None

            return result

        except Exception as e:
            logger.error(f"Error executing opportunity: {e}", exc_info=True)
            result.error_message = str(e)
            return result

    async def _prepare_flash_loan_transaction(
        self,
        provider: FlashLoanProvider,
        opportunity: ArbitrageOpportunity,
        execution_params: Dict[str, Any],
    ) -> Optional[FlashLoanTransaction]:
        """
        Prepare a flash loan transaction for the opportunity.

        This method creates a flash loan transaction that borrows the
        required capital, executes the arbitrage, and repays the loan.

        Args:
            provider: Flash loan provider to use
            opportunity: Arbitrage opportunity to execute
            execution_params: Additional parameters for execution

        Returns:
            Flash loan transaction or None if preparation fails
        """
        try:
            # Get account address
            account_address = execution_params.get("account_address")
            if not account_address:
                account_address = (await self.web3_client.get_accounts())[0]

            # Create flash loan transaction
            flash_loan_tx = FlashLoanTransaction(
                token_address=opportunity.start_token,
                amount=opportunity.required_amount,
                recipient=account_address,
                callback_data="0x",  # Will be filled by provider
            )

            # Add arbitrage data
            # This would normally include the data needed to execute the arbitrage
            # For now, we'll leave it empty

            return flash_loan_tx

        except Exception as e:
            logger.error(f"Error preparing flash loan transaction: {e}")
            return None

    async def _create_flashbots_bundle(
        self, flash_loan_tx: FlashLoanTransaction, execution_params: Dict[str, Any]
    ) -> Optional[FlashbotsBundle]:
        """
        Create a Flashbots bundle for the flash loan transaction.

        This method creates a bundle containing the flash loan transaction
        and any additional transactions needed for the arbitrage.

        Args:
            flash_loan_tx: Flash loan transaction to include in the bundle
            execution_params: Additional parameters for execution

        Returns:
            Flashbots bundle or None if creation fails
        """
        try:
            # Convert flash loan transaction to Web3 transaction
            # This is a simplified conversion and should be replaced with actual conversion
            tx = Transaction(
                from_address=flash_loan_tx.recipient,
                to_address=flash_loan_tx.token_address,
                data="0x",
                value=0,
                gas=500000,
                gas_price=None,  # Will be set by Flashbots
                nonce=None,  # Will be auto-filled
            )

            # Create bundle
            bundle = FlashbotsBundle(
                transactions=[tx],
                blocks_into_future=execution_params.get("blocks_into_future", 2),
            )

            return bundle

        except Exception as e:
            logger.error(f"Error creating Flashbots bundle: {e}")
            return None

    async def _calculate_actual_profit(
        self,
        opportunity: ArbitrageOpportunity,
        stats: Dict[str, Any],
        simulation_result: BundleSimulationResult,
    ) -> Decimal:
        """
        Calculate the actual profit from the executed opportunity.

        This method calculates the profit based on the state changes
        from the bundle execution.

        Args:
            opportunity: Executed arbitrage opportunity
            stats: Bundle inclusion statistics
            simulation_result: Simulation result

        Returns:
            Actual profit in the opportunity's start token
        """
        try:
            # Calculate profit from simulation and stats
            # This is a simplified calculation and should be replaced with actual calculation
            # based on state changes from the simulation

            # For now, we'll use the opportunity's profit amount
            actual_profit = opportunity.profit_amount

            # Subtract gas cost
            gas_cost = (
                Decimal(stats.get("gas_used", 0))
                * Decimal(stats.get("gas_price", 0))
                / Decimal(10**18)
            )

            # Convert gas cost to token cost
            # This is a simplified conversion and should be replaced with actual price
            eth_price = Decimal("2000")  # ETH price in USD
            token_price = Decimal("1")  # Token price in USD
            token_gas_cost = gas_cost * eth_price / token_price

            # Subtract gas cost and apply a safety factor
            actual_profit = actual_profit - token_gas_cost * Decimal("1.05")

            return max(actual_profit, Decimal("0"))

        except Exception as e:
            logger.error(f"Error calculating actual profit: {e}")
            return Decimal("0")

    async def close(self) -> None:
        """Close the strategy and clean up resources."""
        logger.info("Closing Flashbots flash loan strategy")
        if self.flash_loan_factory:
            await self.flash_loan_factory.close()
        if self.bundle_simulator:
            await self.bundle_simulator.close()
        self._is_initialized = False
