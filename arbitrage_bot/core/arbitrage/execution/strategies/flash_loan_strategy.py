"""
Flash Loan Execution Strategy

This module contains the implementation for executing arbitrage opportunities
using flash loans for capital-efficient trades.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, cast

from web3 import Web3

from .....core.web3.interfaces import Web3Client
from .....core.finance.flash_loans import (
    FlashLoanProvider,
    FlashLoanCallback,
    FlashLoanParams,
    FlashLoanResult,
    FlashLoanStatus,
    TokenAmount,
    create_flash_loan_provider,
    get_best_provider,
    get_optimal_multi_token_provider,
    estimate_flash_loan_cost,
)
from ....arbitrage.interfaces import (
    ExecutionStrategy,
    ArbitrageOpportunity,
    ExecutionResult,
    ExecutionStatus,
)

logger = logging.getLogger(__name__)


class ArbitrageFlashLoanCallback(FlashLoanCallback):
    """
    Callback implementation for executing arbitrage during a flash loan.

    This callback handles the execution of arbitrage steps when flash loan
    funds are received, ensuring proper repayment of the loan plus any fees.
    """

    def __init__(
        self,
        web3_client: Web3Client,
        opportunity: ArbitrageOpportunity,
        execution_params: Dict[str, Any],
    ):
        """
        Initialize the callback with the arbitrage opportunity and parameters.

        Args:
            web3_client: Web3 client for blockchain interactions
            opportunity: Arbitrage opportunity to execute
            execution_params: Parameters for execution customization
        """
        self.web3_client = web3_client
        self.opportunity = opportunity
        self.execution_params = execution_params
        self.success = False
        self.error_message: Optional[str] = None
        self.profit_amount = Decimal("0")
        self.gas_used = 0
        self.execution_time = 0

        # Initialize execution state
        self._start_time = 0
        self._lock = asyncio.Lock()

    async def on_flash_loan(
        self,
        sender: str,
        tokens: List[str],
        amounts: List[int],
        fees: List[int],
        user_data: bytes,
    ) -> bool:
        """
        Execute arbitrage steps when flash loan is received.

        This method is called by the flash loan provider when funds are received.
        It must execute the arbitrage and ensure there are enough funds to repay
        the loan plus any fees.

        Args:
            sender: Address of the flash loan provider
            tokens: List of token addresses received
            amounts: List of token amounts received
            fees: List of fees to pay for each token
            user_data: Custom data for execution

        Returns:
            True if arbitrage was successfully executed and has enough funds
            to repay, False otherwise
        """
        async with self._lock:
            self._start_time = time.time()
            logger.info(f"Flash loan received from {sender}")
            logger.info(f"Tokens: {tokens}")
            logger.info(f"Amounts: {amounts}")
            logger.info(f"Fees: {fees}")

            try:
                # Decode user data if provided
                execution_data = {}
                if user_data:
                    import json

                    try:
                        execution_data = json.loads(user_data)
                    except Exception as e:
                        logger.warning(f"Failed to decode user data: {e}")

                # Log starting balances
                for token, amount in zip(tokens, amounts):
                    balance = await self._get_token_balance(token)
                    logger.info(f"Starting balance for {token}: {balance}")

                # Execute arbitrage steps
                # In a real implementation, this would execute the arbitrage route
                # For now, we'll just simulate a successful execution
                logger.info("Executing arbitrage steps...")

                # Record profit and gas used (placeholders for now)
                self.profit_amount = Decimal("0.1")  # 0.1 ETH profit as example
                self.gas_used = 250000  # Gas used as example

                # Check if we have enough tokens to repay the loan + fees
                for i, (token, amount, fee) in enumerate(zip(tokens, amounts, fees)):
                    required_amount = amount + fee
                    logger.info(
                        f"Required to repay: {required_amount} of token {token}"
                    )

                    # Get current balance
                    current_balance = await self._get_token_balance(token)
                    logger.info(f"Current balance: {current_balance}")

                    if current_balance < required_amount:
                        error_msg = (
                            f"Insufficient balance to repay flash loan: "
                            f"{current_balance} < {required_amount}"
                        )
                        logger.error(error_msg)
                        self.error_message = error_msg
                        return False

                logger.info("Arbitrage executed successfully with flash loan")
                self.success = True
                self.execution_time = time.time() - self._start_time
                return True

            except Exception as e:
                logger.error(f"Error executing arbitrage with flash loan: {e}")
                self.error_message = str(e)
                self.success = False
                self.execution_time = time.time() - self._start_time
                return False

    async def on_flash_loan_completed(self, result: FlashLoanResult) -> None:
        """
        Handle flash loan completion.

        Args:
            result: Result of the flash loan operation
        """
        logger.info("Flash loan completed successfully")
        logger.info(f"Transaction hash: {result.transaction_hash}")
        logger.info(f"Gas used: {result.gas_used}")

        if result.gas_used:
            self.gas_used = result.gas_used

        self.execution_time = time.time() - self._start_time

    async def on_flash_loan_failed(self, result: FlashLoanResult) -> None:
        """
        Handle flash loan failure.

        Args:
            result: Result of the flash loan operation
        """
        logger.error(f"Flash loan failed: {result.error_message}")
        logger.error(f"Status: {result.status}")

        self.success = False
        self.error_message = result.error_message
        self.execution_time = time.time() - self._start_time

    async def _get_token_balance(self, token_address: str) -> int:
        """
        Get the token balance for the current account.

        Args:
            token_address: Address of the token

        Returns:
            Current token balance
        """
        account = self.web3_client.get_default_account()
        return await self.web3_client.get_token_balance(token_address, account)


class FlashLoanExecutionStrategy(ExecutionStrategy):
    """
    Flash loan execution strategy for capital-efficient arbitrage.

    This strategy uses flash loans to execute arbitrage opportunities
    without requiring significant capital, using either Balancer (zero-fee)
    or Aave (0.09% fee) as providers depending on token support and liquidity.
    """

    def __init__(
        self, web3_client: Web3Client, config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the flash loan execution strategy.

        Args:
            web3_client: Web3 client for blockchain interactions
            config: Configuration parameters for the strategy
        """
        self.web3_client = web3_client
        self.config = config or {}

        # Configuration
        self.flash_loan_config = self.config.get("flash_loan", {})
        self.slippage_tolerance = Decimal(
            self.flash_loan_config.get("slippage_tolerance", "0.005")
        )  # Default 0.5%
        self.profit_threshold_multiplier = Decimal(
            self.flash_loan_config.get("profit_threshold_multiplier", "1.5")
        )  # Default 1.5x estimated fee
        self.gas_buffer = Decimal(
            self.flash_loan_config.get("gas_buffer", "1.2")
        )  # Default 20% buffer

        # Provider configuration
        self.balancer_config = self.flash_loan_config.get("balancer", {})
        self.aave_config = self.flash_loan_config.get("aave", {})

        # Combined provider config
        self.provider_config = {
            "balancer": self.balancer_config,
            "aave": self.aave_config,
        }

        # State
        self._is_initialized = False
        self._initialization_lock = asyncio.Lock()
        self._execution_lock = asyncio.Lock()
        self._cached_providers: Dict[str, FlashLoanProvider] = {}

    @property
    def name(self) -> str:
        """Get the name of the strategy."""
        return "FlashLoanStrategy"

    async def initialize(self) -> None:
        """
        Initialize the flash loan execution strategy.

        This method ensures that the strategy is ready to execute
        opportunities.
        """
        async with self._initialization_lock:
            if self._is_initialized:
                logger.debug("Flash loan execution strategy already initialized")
                return

            logger.info("Initializing flash loan execution strategy")

            # Check web3 client
            if not hasattr(self.web3_client, "get_default_account"):
                raise ValueError("Web3 client must implement get_default_account")

            # Pre-initialize providers for common tokens to speed up execution
            # This is optional but can reduce execution time
            if self.flash_loan_config.get("pre_initialize_providers", True):
                await self._pre_initialize_providers()

            self._is_initialized = True
            logger.info("Flash loan execution strategy initialized")

    async def _ensure_initialized(self) -> None:
        """Ensure the strategy is initialized."""
        if not self._is_initialized:
            await self.initialize()

    async def _pre_initialize_providers(self) -> None:
        """
        Pre-initialize providers for common tokens.

        This method creates and initializes providers for common tokens
        to speed up execution time.
        """
        try:
            # Common tokens to pre-initialize (addresses are network-specific)
            # For now, just use a few common tokens on mainnet
            common_tokens = {
                "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
                "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            }

            logger.info("Pre-initializing flash loan providers for common tokens")

            for token_name, token_address in common_tokens.items():
                try:
                    # Create provider and add to cache
                    provider = await get_best_provider(
                        self.web3_client,
                        token_address,
                        Decimal("1000"),  # Use 1000 as a default amount
                        self.provider_config,
                    )

                    # Add to cache
                    self._cached_providers[token_address.lower()] = provider
                    logger.info(f"Pre-initialized {provider.name} for {token_name}")

                except Exception as e:
                    logger.warning(
                        f"Failed to pre-initialize provider for {token_name}: {e}"
                    )

            logger.info(f"Pre-initialized {len(self._cached_providers)} providers")

        except Exception as e:
            logger.warning(f"Failed to pre-initialize providers: {e}")

    async def can_execute(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Determine if the opportunity can be executed with this strategy.

        Args:
            opportunity: Arbitrage opportunity to check

        Returns:
            True if the opportunity can be executed, False otherwise
        """
        await self._ensure_initialized()

        try:
            # Check if the opportunity has input token and amount
            if not opportunity.input_token or not opportunity.input_amount:
                logger.warning("Opportunity missing input token or amount")
                return False

            # Check if input token is supported by any provider
            token_address = opportunity.input_token.address
            amount = opportunity.input_amount

            # Try to find a provider that supports this token and amount
            try:
                # Check cached providers first
                if token_address.lower() in self._cached_providers:
                    provider = self._cached_providers[token_address.lower()]
                    if await provider.check_liquidity(token_address, amount):
                        return True

                # Try getting a provider
                provider = await get_best_provider(
                    self.web3_client, token_address, amount, self.provider_config
                )

                # Provider found, check liquidity
                has_liquidity = await provider.check_liquidity(token_address, amount)

                # Cache provider for future use
                if has_liquidity:
                    self._cached_providers[token_address.lower()] = provider
                    return True
                else:
                    await provider.close()
                    return False

            except ValueError:
                # No provider supports this token
                logger.info(f"No flash loan provider supports token {token_address}")
                return False

        except Exception as e:
            logger.error(f"Error checking if opportunity can be executed: {e}")
            return False

    async def get_estimated_cost(self, opportunity: ArbitrageOpportunity) -> Decimal:
        """
        Get the estimated cost of executing the opportunity.

        This method calculates the estimated cost of executing the opportunity,
        including flash loan fees and gas costs.

        Args:
            opportunity: Arbitrage opportunity to estimate costs for

        Returns:
            Estimated cost in the opportunity's output token
        """
        await self._ensure_initialized()

        try:
            # Get token and amount
            token_address = opportunity.input_token.address
            amount = opportunity.input_amount

            # Estimate flash loan fee
            fee_costs = await estimate_flash_loan_cost(
                self.web3_client, token_address, amount, self.provider_config
            )

            # Get lowest fee (Balancer should be 0)
            min_fee_provider = min(fee_costs.items(), key=lambda x: x[1])[0]
            min_fee = fee_costs[min_fee_provider]

            logger.info(
                f"Estimated flash loan fee: {min_fee} (provider: {min_fee_provider})"
            )

            # Estimate gas cost
            # This is just a placeholder, in real implementation you would
            # estimate the gas cost based on the complexity of the arbitrage
            estimated_gas = 400000  # Default gas estimate

            # TODO: Convert gas cost to token value
            # For now, just return the flash loan fee as the cost
            return min_fee

        except Exception as e:
            logger.error(f"Error estimating execution cost: {e}")
            return Decimal("999999999")  # High cost to avoid execution on error

    async def is_profitable(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Determine if the opportunity is profitable after costs.

        Args:
            opportunity: Arbitrage opportunity to check

        Returns:
            True if the opportunity is profitable after costs, False otherwise
        """
        await self._ensure_initialized()

        try:
            # Get expected profit
            expected_profit = opportunity.expected_profit

            # Get estimated cost
            estimated_cost = await self.get_estimated_cost(opportunity)

            # Calculate profit threshold (cost * multiplier)
            profit_threshold = estimated_cost * self.profit_threshold_multiplier

            # Check if expected profit exceeds threshold
            is_profitable = expected_profit > profit_threshold

            logger.info(
                f"Opportunity profitability: expected={expected_profit}, "
                f"cost={estimated_cost}, threshold={profit_threshold}, "
                f"profitable={is_profitable}"
            )

            return is_profitable

        except Exception as e:
            logger.error(f"Error checking if opportunity is profitable: {e}")
            return False

    async def execute(
        self,
        opportunity: ArbitrageOpportunity,
        execution_params: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute the arbitrage opportunity using flash loans.

        This method executes the arbitrage opportunity using flash loans
        to minimize capital requirements.

        Args:
            opportunity: Arbitrage opportunity to execute
            execution_params: Parameters for execution customization

        Returns:
            Result of the execution
        """
        await self._ensure_initialized()
        execution_params = execution_params or {}

        # Initialize result with pending status
        result = ExecutionResult(
            status=ExecutionStatus.PENDING,
            opportunity=opportunity,
            profit_amount=None,
            transaction_hash=None,
            error_message=None,
            gas_used=None,
            execution_time=None,
        )

        async with self._execution_lock:
            start_time = time.time()

            try:
                logger.info(f"Executing opportunity with flash loan: {opportunity.id}")

                # Check profitability
                if not await self.is_profitable(opportunity):
                    logger.warning(
                        f"Opportunity {opportunity.id} is not profitable after costs"
                    )
                    result.status = ExecutionStatus.REJECTED
                    result.error_message = "Not profitable after costs"
                    result.execution_time = time.time() - start_time
                    return result

                # Get token and amount
                token_address = opportunity.input_token.address
                amount = opportunity.input_amount

                # Create flash loan callback
                callback = ArbitrageFlashLoanCallback(
                    self.web3_client, opportunity, execution_params
                )

                # Create token amount
                token_amount = TokenAmount(token_address=token_address, amount=amount)

                # Create flash loan parameters
                params = FlashLoanParams(
                    token_amounts=[token_amount],
                    receiver_address=self.web3_client.get_default_account(),
                    slippage_tolerance=self.slippage_tolerance,
                    transaction_params=execution_params.get("transaction_params", {}),
                    callback_data=execution_params.get("callback_data", b""),
                )

                # Try with primary provider first
                primary_success = False

                try:
                    # Get best provider
                    provider = await get_best_provider(
                        self.web3_client, token_address, amount, self.provider_config
                    )

                    logger.info(f"Executing with primary provider: {provider.name}")

                    # Execute flash loan
                    flash_loan_result = await provider.execute_flash_loan(
                        params, callback
                    )

                    # Check result
                    if flash_loan_result.success:
                        primary_success = True
                        logger.info(
                            f"Successfully executed with primary provider {provider.name}"
                        )
                    else:
                        logger.warning(
                            f"Failed with primary provider {provider.name}: "
                            f"{flash_loan_result.error_message}"
                        )

                    # Close provider
                    await provider.close()

                except Exception as e:
                    logger.error(f"Error with primary provider: {e}")

                # If primary failed, try fallback provider
                if not primary_success:
                    logger.info("Trying fallback provider")

                    try:
                        # Current best provider failed, try others
                        # Try Aave if Balancer failed and vice versa
                        provider_type = (
                            "aave"
                            if "Balancer"
                            in self._cached_providers.get(
                                token_address.lower(), FlashLoanProvider
                            ).name
                            else "balancer"
                        )

                        provider = await create_flash_loan_provider(
                            provider_type,
                            self.web3_client,
                            self.provider_config.get(provider_type, {}),
                        )

                        logger.info(
                            f"Executing with fallback provider: {provider.name}"
                        )

                        # Check liquidity
                        if await provider.check_liquidity(token_address, amount):
                            # Execute flash loan
                            flash_loan_result = await provider.execute_flash_loan(
                                params, callback
                            )

                            # Check result
                            if flash_loan_result.success:
                                logger.info(
                                    f"Successfully executed with fallback provider {provider.name}"
                                )
                            else:
                                logger.warning(
                                    f"Failed with fallback provider {provider.name}: "
                                    f"{flash_loan_result.error_message}"
                                )
                        else:
                            logger.warning(
                                f"Fallback provider {provider.name} has insufficient liquidity"
                            )

                        # Close provider
                        await provider.close()

                    except Exception as e:
                        logger.error(f"Error with fallback provider: {e}")

                # Update result based on callback
                if callback.success:
                    result.status = ExecutionStatus.EXECUTED
                    result.profit_amount = callback.profit_amount
                    result.transaction_hash = getattr(
                        flash_loan_result, "transaction_hash", None
                    )
                    result.gas_used = callback.gas_used
                else:
                    result.status = ExecutionStatus.FAILED
                    result.error_message = callback.error_message

            except Exception as e:
                logger.error(f"Error executing opportunity with flash loan: {e}")
                result.status = ExecutionStatus.FAILED
                result.error_message = str(e)

            finally:
                result.execution_time = time.time() - start_time

            return result

    async def close(self) -> None:
        """Clean up resources used by the strategy."""
        logger.info("Closing flash loan execution strategy")

        # Close cached providers
        for token_address, provider in self._cached_providers.items():
            try:
                await provider.close()
            except Exception as e:
                logger.warning(f"Error closing provider for {token_address}: {e}")

        self._cached_providers = {}
        self._is_initialized = False
