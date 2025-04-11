"""
Standard Execution Strategy

This module contains the implementation of the StandardExecutionStrategy,
which executes arbitrage opportunities using standard blockchain transactions.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, cast

from arbitrage_bot.core.dex.interfaces import DEX, Router  # Absolute import
from arbitrage_bot.core.web3.interfaces import (
    Web3Client,
    Transaction,
    TransactionReceipt,
)  # Absolute import
from arbitrage_bot.core.arbitrage.interfaces import (  # Absolute import
    ExecutionStrategy,
    GasEstimator,
)
from arbitrage_bot.core.arbitrage.models import (  # Absolute import
    ArbitrageOpportunity,
    ArbitrageRoute,
    ArbitrageStep,
    ExecutionResult,
    ExecutionStatus,
    TransactionInfo,
)

logger = logging.getLogger(__name__)


class StandardExecutionStrategy(ExecutionStrategy):
    """
    Standard execution strategy for arbitrage opportunities.

    This strategy executes arbitrage opportunities using standard blockchain
    transactions, with optional Flashbots integration for MEV protection.
    """

    def __init__(
        self,
        gas_estimator: Optional[GasEstimator] = None,
        config: Dict[str, Any] = None,
    ):
        """
        Initialize the standard execution strategy.

        Args:
            gas_estimator: Optional gas estimator for gas cost calculations
            config: Configuration dictionary
        """
        self.gas_estimator = gas_estimator
        self.config = config or {}

        # Configuration
        self.slippage_percentage = Decimal(
            self.config.get("slippage_percentage", "0.5")
        )  # 0.5%
        self.gas_limit_buffer = Decimal(
            self.config.get("gas_limit_buffer", "20")
        )  # 20% buffer on gas limit
        self.transaction_timeout = int(
            self.config.get("transaction_timeout", 60)
        )  # 60 seconds
        self.max_retries = int(
            self.config.get("max_retries", 1)
        )  # Maximum number of retries
        self.default_gas_limit = int(
            self.config.get("default_gas_limit", 500000)
        )  # Default gas limit

        # Locks
        self._execution_lock = asyncio.Lock()

        logger.info("StandardExecutionStrategy initialized")

    async def execute(
        self,
        opportunity: ArbitrageOpportunity,
        web3_client: Web3Client,
        dexes: Dict[str, DEX],
        **kwargs,
    ) -> ExecutionResult:
        """
        Execute an arbitrage opportunity.

        Args:
            opportunity: Arbitrage opportunity to execute
            web3_client: Web3 client for blockchain interactions
            dexes: Dictionary mapping DEX IDs to DEX instances
            **kwargs: Additional execution parameters

        Returns:
            Execution result
        """
        logger.info(f"Executing opportunity {opportunity.id} using standard strategy")

        # Extract execution parameters
        account_address = kwargs.get(
            "account_address", web3_client.get_default_account()
        )
        use_flashbots = kwargs.get("use_flashbots", False)
        priority_fee = kwargs.get("priority_fee", None)
        max_fee_per_gas = kwargs.get("max_fee_per_gas", None)
        custom_slippage = kwargs.get("slippage_percentage", self.slippage_percentage)

        # Verify account address
        if not account_address:
            logger.error("No account address provided for execution")
            return ExecutionResult(
                opportunity_id=opportunity.id,
                status=ExecutionStatus.FAILED,
                timestamp=int(time.time()),
                message="No account address provided",
                transaction_info=None,
                profit=None,
                gas_used=None,
                total_cost=None,
            )

        # Lock during execution to prevent concurrent modifications
        async with self._execution_lock:
            try:
                # Build transaction(s) for the opportunity
                transaction = await self._build_transaction(
                    opportunity=opportunity,
                    web3_client=web3_client,
                    dexes=dexes,
                    account_address=account_address,
                    slippage_percentage=custom_slippage,
                    **kwargs,
                )

                if not transaction:
                    logger.error(
                        f"Failed to build transaction for opportunity {opportunity.id}"
                    )
                    return ExecutionResult(
                        opportunity_id=opportunity.id,
                        status=ExecutionStatus.FAILED,
                        timestamp=int(time.time()),
                        message="Failed to build transaction",
                        transaction_info=None,
                        profit=None,
                        gas_used=None,
                        total_cost=None,
                    )

                # Estimate gas if not provided
                gas_limit = transaction.gas or await self._estimate_gas(
                    transaction=transaction, web3_client=web3_client
                )

                # Add buffer to gas limit
                gas_limit = int(gas_limit * (100 + self.gas_limit_buffer) / 100)
                transaction.gas = gas_limit

                # Set gas prices if not already set
                if not transaction.gas_price and not (
                    transaction.max_fee_per_gas and transaction.max_priority_fee_per_gas
                ):
                    if use_flashbots:
                        # For Flashbots, set max fee and priority fee
                        if not max_fee_per_gas:
                            gas_price = await web3_client.get_gas_price()
                            max_fee_per_gas = int(
                                gas_price * 1.1
                            )  # 10% above current gas price

                        if not priority_fee:
                            priority_fee = await web3_client.get_priority_fee()

                        transaction.max_fee_per_gas = max_fee_per_gas
                        transaction.max_priority_fee_per_gas = priority_fee
                    else:
                        # For standard transactions, just set gas price
                        gas_price = await web3_client.get_gas_price()
                        transaction.gas_price = gas_price

                # Submit transaction
                bundle_hash: Optional[str] = None
                tx_hash: Optional[str] = None

                if use_flashbots:
                    logger.info(
                        f"Submitting bundle for opportunity {opportunity.id} using Flashbots"
                    )
                    # Assuming send_flashbots_transaction now correctly returns a bundle_hash
                    bundle_hash = await web3_client.send_flashbots_bundle(transaction)
                    # We'll get the actual tx_hash later if wait_for_receipt is True
                else:
                    logger.info(
                        f"Submitting transaction for opportunity {opportunity.id}"
                    )
                    tx_hash = await web3_client.send_transaction(
                        transaction
                    )  # This should be the actual tx_hash

                submission_identifier = bundle_hash if use_flashbots else tx_hash
                if not submission_identifier:
                    log_msg = "bundle" if use_flashbots else "transaction"
                    logger.error(
                        f"Failed to submit {log_msg} for opportunity {opportunity.id}"
                    )
                    return ExecutionResult(
                        opportunity_id=opportunity.id,
                        status=ExecutionStatus.FAILED,
                        timestamp=int(time.time()),
                        message=f"Failed to submit {log_msg}",
                        transaction_info=None,
                        profit=None,
                        gas_used=None,
                        total_cost=None,
                    )

                # Create initial transaction info (tx_hash might be None for flashbots initially)
                transaction_info = TransactionInfo(
                    transaction_hash=tx_hash,  # May be None if using flashbots and not waiting
                    bundle_hash=bundle_hash,  # Store bundle hash if available
                    from_address=account_address,
                    to_address=transaction.to,
                    data=transaction.data,
                    value=transaction.value,
                    gas_limit=gas_limit,
                    gas_price=transaction.gas_price,
                    max_fee_per_gas=transaction.max_fee_per_gas,
                    priority_fee=transaction.max_priority_fee_per_gas,
                    nonce=transaction.nonce,
                    status=ExecutionStatus.SUBMITTED,  # Initial status
                    gas_used=None,
                    effective_gas_price=None,
                    block_number=None,
                    timestamp=int(time.time()),
                    error_message=None,
                )

                # Wait for confirmation if requested
                wait_for_receipt = kwargs.get("wait_for_receipt", False)
                if wait_for_receipt:
                    if use_flashbots:
                        logger.info(
                            f"Waiting for Flashbots bundle {bundle_hash} inclusion..."
                        )
                        try:
                            # Assuming web3_client has flashbots provider attached
                            bundle_stats = await web3_client.flashbots.wait_for_bundle(
                                bundle_hash, timeout=self.transaction_timeout
                            )

                            if bundle_stats and bundle_stats.get("included"):
                                logger.info(
                                    f"Bundle {bundle_hash} included in block {bundle_stats.get('blockNumber')}"
                                )
                                # Assuming the first transaction in the bundle is ours
                                if (
                                    bundle_stats.get("transactions")
                                    and len(bundle_stats["transactions"]) > 0
                                ):
                                    actual_tx_hash = bundle_stats["transactions"][
                                        0
                                    ].get("hash")
                                    transaction_info.transaction_hash = (
                                        actual_tx_hash  # Update with actual hash
                                    )
                                    logger.info(
                                        f"Actual transaction hash: {actual_tx_hash}"
                                    )

                                    # Now wait for the actual receipt using the real tx hash
                                    receipt = await self._wait_for_transaction_receipt(
                                        tx_hash=actual_tx_hash, web3_client=web3_client
                                    )
                                    if receipt:
                                        transaction_info.status = (
                                            ExecutionStatus.SUCCEEDED
                                            if receipt.status
                                            else ExecutionStatus.FAILED
                                        )
                                        transaction_info.gas_used = receipt.gas_used
                                        transaction_info.effective_gas_price = (
                                            receipt.effective_gas_price
                                        )
                                        transaction_info.block_number = (
                                            receipt.block_number
                                        )
                                        if not receipt.status:
                                            transaction_info.error_message = (
                                                "Transaction reverted on-chain"
                                            )
                                            logger.warning(
                                                f"Transaction {actual_tx_hash} included but failed (reverted)"
                                            )
                                        else:
                                            logger.info(
                                                f"Transaction {actual_tx_hash} succeeded on-chain"
                                            )
                                            # Recalculate cost based on actual receipt
                                            total_cost = (
                                                receipt.gas_used
                                                * receipt.effective_gas_price
                                            )
                                            # TODO: Potentially parse logs for actual profit
                                            return ExecutionResult(
                                                opportunity_id=opportunity.id,
                                                status=ExecutionStatus.SUCCEEDED,
                                                timestamp=int(time.time()),
                                                message="Flashbots bundle executed successfully",
                                                transaction_info=transaction_info,
                                                profit=opportunity.expected_profit,
                                                gas_used=receipt.gas_used,
                                                total_cost=total_cost,
                                            )
                                    else:
                                        # Should ideally not happen if bundle was included, but handle defensively
                                        transaction_info.status = (
                                            ExecutionStatus.UNKNOWN
                                        )
                                        transaction_info.error_message = (
                                            "Bundle included but receipt not found"
                                        )
                                        logger.error(
                                            f"Bundle {bundle_hash} included but failed to get receipt for tx {actual_tx_hash}"
                                        )

                                else:
                                    transaction_info.status = ExecutionStatus.UNKNOWN
                                    transaction_info.error_message = "Bundle included but no transaction hash found in stats"
                                    logger.error(
                                        f"Bundle {bundle_hash} included but no tx hash found in stats: {bundle_stats}"
                                    )
                            else:
                                # Bundle not included or stats indicate failure
                                transaction_info.status = ExecutionStatus.FAILED
                                transaction_info.error_message = (
                                    bundle_stats.get(
                                        "error", "Bundle not included or failed"
                                    )
                                    if bundle_stats
                                    else "Bundle not included (timeout or other issue)"
                                )
                                logger.warning(
                                    f"Flashbots bundle {bundle_hash} failed or not included. Stats: {bundle_stats}"
                                )

                        except TimeoutError:
                            transaction_info.status = ExecutionStatus.TIMED_OUT
                            transaction_info.error_message = (
                                f"Timeout waiting for bundle {bundle_hash}"
                            )
                            logger.warning(transaction_info.error_message)
                        except Exception as e:
                            transaction_info.status = ExecutionStatus.FAILED
                            transaction_info.error_message = (
                                f"Error waiting for bundle: {e}"
                            )
                            logger.error(transaction_info.error_message, exc_info=True)

                        # Return FAILED/TIMED_OUT result if bundle wasn't successfully executed and confirmed
                        return ExecutionResult(
                            opportunity_id=opportunity.id,
                            status=transaction_info.status,
                            timestamp=int(time.time()),
                            message=transaction_info.error_message
                            or "Bundle execution failed",
                            transaction_info=transaction_info,
                            profit=None,
                            gas_used=transaction_info.gas_used,
                            total_cost=(
                                transaction_info.gas_used
                                * transaction_info.effective_gas_price
                                if transaction_info.gas_used
                                and transaction_info.effective_gas_price
                                else None
                            ),
                        )

                    else:  # Standard transaction (not Flashbots)
                        logger.info(f"Waiting for transaction receipt for {tx_hash}")
                        receipt = await self._wait_for_transaction_receipt(
                            tx_hash=tx_hash, web3_client=web3_client
                        )
                        if receipt:
                            transaction_info.status = (
                                ExecutionStatus.SUCCEEDED
                                if receipt.status
                                else ExecutionStatus.FAILED
                            )
                            transaction_info.gas_used = receipt.gas_used
                            transaction_info.effective_gas_price = (
                                receipt.effective_gas_price
                            )
                            transaction_info.block_number = receipt.block_number
                            if receipt.status:
                                logger.info(f"Transaction {tx_hash} succeeded")
                                total_cost = (
                                    receipt.gas_used * receipt.effective_gas_price
                                )
                                return ExecutionResult(
                                    opportunity_id=opportunity.id,
                                    status=ExecutionStatus.SUCCEEDED,
                                    timestamp=int(time.time()),
                                    message="Transaction succeeded",
                                    transaction_info=transaction_info,
                                    profit=opportunity.expected_profit,  # TODO: Actual profit
                                    gas_used=receipt.gas_used,
                                    total_cost=total_cost,
                                )
                            else:
                                transaction_info.error_message = "Transaction reverted"
                                logger.warning(
                                    f"Transaction {tx_hash} failed (reverted)"
                                )
                                total_cost = (
                                    receipt.gas_used * receipt.effective_gas_price
                                )
                                return ExecutionResult(
                                    opportunity_id=opportunity.id,
                                    status=ExecutionStatus.FAILED,
                                    timestamp=int(time.time()),
                                    message="Transaction reverted",
                                    transaction_info=transaction_info,
                                    profit=None,
                                    gas_used=receipt.gas_used,
                                    total_cost=total_cost,
                                )
                        else:
                            # Timeout waiting for standard transaction receipt
                            transaction_info.status = ExecutionStatus.TIMED_OUT
                            transaction_info.error_message = (
                                f"Timeout waiting for receipt for tx {tx_hash}"
                            )
                            logger.warning(transaction_info.error_message)
                            return ExecutionResult(
                                opportunity_id=opportunity.id,
                                status=ExecutionStatus.TIMED_OUT,
                                timestamp=int(time.time()),
                                message=transaction_info.error_message,
                                transaction_info=transaction_info,
                                profit=None,
                                gas_used=None,
                                total_cost=None,
                            )

                # If not waiting for receipt, return the initial SUBMITTED status
                # Note: transaction_info.transaction_hash will be None for Flashbots here
                log_msg = "Bundle" if use_flashbots else "Transaction"
                return ExecutionResult(
                    opportunity_id=opportunity.id,
                    status=ExecutionStatus.SUBMITTED,
                    timestamp=int(time.time()),
                    message=f"{log_msg} submitted",
                    transaction_info=transaction_info,  # Includes bundle_hash if applicable
                    profit=opportunity.expected_profit,  # Still expected profit at this stage
                    gas_used=None,
                    total_cost=None,
                )

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
                    total_cost=None,
                )

    async def _build_transaction(
        self,
        opportunity: ArbitrageOpportunity,
        web3_client: Web3Client,
        dexes: Dict[str, DEX],
        account_address: str,
        slippage_percentage: Decimal,
        **kwargs,
    ) -> Optional[Transaction]:
        """
        Build a transaction for the arbitrage opportunity.

        Args:
            opportunity: Arbitrage opportunity to execute
            web3_client: Web3 client for blockchain interactions
            dexes: Dictionary mapping DEX IDs to DEX instances
            account_address: Account address to use for execution
            slippage_percentage: Slippage tolerance as percentage
            **kwargs: Additional parameters

        Returns:
            Transaction or None if building failed
        """
        try:
            # Check if route has at least one step
            if not opportunity.route.steps or len(opportunity.route.steps) < 1:
                logger.error(f"Opportunity {opportunity.id} has no steps in route")
                return None

            # Determine transaction type based on route
            if len(opportunity.route.steps) == 1:
                # Single step - direct swap
                return await self._build_single_swap_transaction(
                    step=opportunity.route.steps[0],
                    web3_client=web3_client,
                    dexes=dexes,
                    account_address=account_address,
                    slippage_percentage=slippage_percentage,
                    **kwargs,
                )
            elif (
                len(opportunity.route.steps) == 2
                and opportunity.route.steps[0].dex.id
                != opportunity.route.steps[1].dex.id
            ):
                # Two steps with different DEXes - cross-DEX arbitrage
                return await self._build_cross_dex_transaction(
                    route=opportunity.route,
                    web3_client=web3_client,
                    dexes=dexes,
                    account_address=account_address,
                    slippage_percentage=slippage_percentage,
                    **kwargs,
                )
            elif all(
                step.dex.id == opportunity.route.steps[0].dex.id
                for step in opportunity.route.steps
            ):
                # All steps on same DEX - triangular arbitrage
                return await self._build_triangular_transaction(
                    route=opportunity.route,
                    web3_client=web3_client,
                    dexes=dexes,
                    account_address=account_address,
                    slippage_percentage=slippage_percentage,
                    **kwargs,
                )
            else:
                # Complex arbitrage - use multi-step transaction
                return await self._build_multi_step_transaction(
                    route=opportunity.route,
                    web3_client=web3_client,
                    dexes=dexes,
                    account_address=account_address,
                    slippage_percentage=slippage_percentage,
                    **kwargs,
                )
        except Exception as e:
            logger.error(
                f"Error building transaction for opportunity {opportunity.id}: {e}"
            )
            return None

    async def _build_single_swap_transaction(
        self,
        step: ArbitrageStep,
        web3_client: Web3Client,
        dexes: Dict[str, DEX],
        account_address: str,
        slippage_percentage: Decimal,
        **kwargs,
    ) -> Optional[Transaction]:
        """
        Build a transaction for a single swap.

        Args:
            step: Arbitrage step to execute
            web3_client: Web3 client for blockchain interactions
            dexes: Dictionary mapping DEX IDs to DEX instances
            account_address: Account address to use for execution
            slippage_percentage: Slippage tolerance as percentage
            **kwargs: Additional parameters

        Returns:
            Transaction or None if building failed
        """
        try:
            # Get DEX
            dex_id = step.dex.id
            if dex_id not in dexes:
                logger.error(f"DEX {dex_id} not found")
                return None

            dex = dexes[dex_id]

            # Check if DEX is a Router
            if not isinstance(dex, Router):
                logger.error(f"DEX {dex_id} is not a Router")
                return None

            router = cast(Router, dex)

            # Get input and output details
            input_token_address = step.input_token.address
            output_token_address = step.output_token.address
            input_amount = step.input_token.amount

            # Calculate minimum output amount based on slippage
            expected_output_amount = step.output_token.amount
            min_output_amount = int(
                expected_output_amount * (100 - slippage_percentage) / 100
            )

            # Get deadline timestamp
            deadline_seconds = kwargs.get(
                "deadline_seconds", 60 * 20
            )  # 20 minutes default
            deadline = int(time.time()) + deadline_seconds

            # Build swap transaction
            swap_tx = await router.build_swap_transaction(
                input_token_address=input_token_address,
                output_token_address=output_token_address,
                input_amount=input_amount,
                min_output_amount=min_output_amount,
                recipient=account_address,
                deadline=deadline,
            )

            # Combine parameters into a transaction
            transaction = Transaction(
                to=router.contract_address,
                data=swap_tx.data,
                value=swap_tx.value or 0,
                from_address=account_address,
                gas=None,  # Will be estimated
                gas_price=None,  # Will be set later
                max_fee_per_gas=None,
                max_priority_fee_per_gas=None,
                nonce=None,  # Will be set by web3 client
            )

            return transaction
        except Exception as e:
            logger.error(f"Error building single swap transaction: {e}")
            return None

    async def _build_cross_dex_transaction(
        self,
        route: ArbitrageRoute,
        web3_client: Web3Client,
        dexes: Dict[str, DEX],
        account_address: str,
        slippage_percentage: Decimal,
        **kwargs,
    ) -> Optional[Transaction]:
        """
        Build a transaction for a cross-DEX arbitrage.

        Args:
            route: Arbitrage route to execute
            web3_client: Web3 client for blockchain interactions
            dexes: Dictionary mapping DEX IDs to DEX instances
            account_address: Account address to use for execution
            slippage_percentage: Slippage tolerance as percentage
            **kwargs: Additional parameters

        Returns:
            Transaction or None if building failed
        """
        try:
            # For cross-DEX arbitrage, we use a multi-contract interaction
            # This typically requires a custom contract or multicall
            # For now, we'll just use the first step and execute steps separately

            # Get the first step
            first_step = route.steps[0]

            # For simplicity in this implementation, build transaction for first step
            return await self._build_single_swap_transaction(
                step=first_step,
                web3_client=web3_client,
                dexes=dexes,
                account_address=account_address,
                slippage_percentage=slippage_percentage,
                **kwargs,
            )

            # NOTE: A complete implementation would use either:
            # 1. A custom arbitrage contract that can execute multiple swaps atomically
            # 2. A multicall contract to batch multiple transactions
            # 3. A flash loan to provide capital, execute swaps, and repay the loan in one transaction

        except Exception as e:
            logger.error(f"Error building cross-DEX transaction: {e}")
            return None

    async def _build_triangular_transaction(
        self,
        route: ArbitrageRoute,
        web3_client: Web3Client,
        dexes: Dict[str, DEX],
        account_address: str,
        slippage_percentage: Decimal,
        **kwargs,
    ) -> Optional[Transaction]:
        """
        Build a transaction for a triangular arbitrage.

        Args:
            route: Arbitrage route to execute
            web3_client: Web3 client for blockchain interactions
            dexes: Dictionary mapping DEX IDs to DEX instances
            account_address: Account address to use for execution
            slippage_percentage: Slippage tolerance as percentage
            **kwargs: Additional parameters

        Returns:
            Transaction or None if building failed
        """
        try:
            # For triangular arbitrage, we also need a multi-contract interaction
            # Since all steps are on the same DEX, this might be done with a specialized function
            # For now, just use the first step

            # Get the first step
            first_step = route.steps[0]

            # For simplicity, build transaction for first step
            return await self._build_single_swap_transaction(
                step=first_step,
                web3_client=web3_client,
                dexes=dexes,
                account_address=account_address,
                slippage_percentage=slippage_percentage,
                **kwargs,
            )

            # NOTE: A complete implementation would use either:
            # 1. A custom arbitrage contract that can execute multiple swaps atomically
            # 2. A multicall contract to batch multiple transactions

        except Exception as e:
            logger.error(f"Error building triangular transaction: {e}")
            return None

    async def _build_multi_step_transaction(
        self,
        route: ArbitrageRoute,
        web3_client: Web3Client,
        dexes: Dict[str, DEX],
        account_address: str,
        slippage_percentage: Decimal,
        **kwargs,
    ) -> Optional[Transaction]:
        """
        Build a transaction for a multi-step arbitrage.

        Args:
            route: Arbitrage route to execute
            web3_client: Web3 client for blockchain interactions
            dexes: Dictionary mapping DEX IDs to DEX instances
            account_address: Account address to use for execution
            slippage_percentage: Slippage tolerance as percentage
            **kwargs: Additional parameters

        Returns:
            Transaction or None if building failed
        """
        try:
            # For multi-step arbitrage, we need a complex transaction
            # This typically requires a custom arbitrage contract or multicall
            # For now, just use the first step

            # Get the first step
            first_step = route.steps[0]

            # For simplicity, build transaction for first step
            return await self._build_single_swap_transaction(
                step=first_step,
                web3_client=web3_client,
                dexes=dexes,
                account_address=account_address,
                slippage_percentage=slippage_percentage,
                **kwargs,
            )

            # NOTE: A complete implementation would use either:
            # 1. A custom arbitrage contract that can execute multiple swaps atomically
            # 2. A multicall contract to batch multiple transactions
            # 3. A flash loan to provide capital, execute swaps, and repay the loan in one transaction

        except Exception as e:
            logger.error(f"Error building multi-step transaction: {e}")
            return None

    async def _estimate_gas(
        self, transaction: Transaction, web3_client: Web3Client
    ) -> int:
        """
        Estimate gas for a transaction.

        Args:
            transaction: Transaction to estimate gas for
            web3_client: Web3 client for blockchain interactions

        Returns:
            Estimated gas limit
        """
        try:
            # Use gas estimator if available
            if self.gas_estimator:
                return await self.gas_estimator.estimate_gas(transaction)

            # Otherwise, use web3 client
            gas_estimate = await web3_client.estimate_gas(transaction)

            if gas_estimate:
                return gas_estimate
            else:
                logger.warning(
                    f"Failed to estimate gas, using default: {self.default_gas_limit}"
                )
                return self.default_gas_limit

        except Exception as e:
            logger.error(f"Error estimating gas: {e}")
            return self.default_gas_limit

    async def _wait_for_transaction_receipt(
        self, tx_hash: str, web3_client: Web3Client
    ) -> Optional[TransactionReceipt]:
        """
        Wait for a transaction receipt.

        Args:
            tx_hash: Transaction hash
            web3_client: Web3 client for blockchain interactions

        Returns:
            Transaction receipt or None if timeout
        """
        try:
            # Wait for transaction receipt with timeout
            receipt = await web3_client.wait_for_transaction_receipt(
                tx_hash=tx_hash, timeout=self.transaction_timeout
            )

            return receipt

        except Exception as e:
            logger.error(f"Error waiting for transaction receipt: {e}")
            return None


async def create_standard_execution_strategy(
    gas_estimator: Optional[GasEstimator] = None, config: Dict[str, Any] = None
) -> StandardExecutionStrategy:
    """
    Factory function to create a standard execution strategy.

    Args:
        gas_estimator: Optional gas estimator for gas cost calculations
        config: Configuration dictionary

    Returns:
        Initialized standard execution strategy
    """
    return StandardExecutionStrategy(gas_estimator=gas_estimator, config=config)
