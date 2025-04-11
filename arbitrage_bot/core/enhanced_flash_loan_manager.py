"""
Enhanced Flash Loan Manager Module

This module provides advanced flash loan management with:
- Multi-path routing optimization
- Gas usage optimization
- Bundle preparation and validation
- Slippage protection
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, NamedTuple, Any
from decimal import Decimal
from eth_typing import ChecksumAddress
from web3 import Web3, exceptions

from ..utils.async_manager import AsyncLock
from .interfaces import Transaction, TokenPair, LiquidityData
from .web3.flashbots.flashbots_provider import FlashbotsProvider
from .memory.memory_bank import MemoryBank
from .finance.flash_loans.providers.balancer import BalancerFlashLoanProvider
from .finance.flash_loans.providers.aave import AaveFlashLoanProvider
from .finance.flash_loans.interfaces import FlashLoanParams, FlashLoanCallback

logger = logging.getLogger(__name__)


class RouteSegment(NamedTuple):
    """Represents a segment in a multi-path route."""

    dex_name: str
    token_in: ChecksumAddress
    token_out: ChecksumAddress
    amount_in: int
    min_amount_out: int
    pool_fee: int


class FlashLoanRoute(NamedTuple):
    """Complete flash loan route with multiple segments."""

    segments: List[RouteSegment]
    total_profit: int
    total_gas: int
    success_probability: float


# Note: UnifiedFlashLoanManager class removed as it appears unused by primary execution paths.
# The core logic resides in EnhancedFlashLoanManager below and specific providers.


class EnhancedFlashLoanManager:
    """Enhanced flash loan management with advanced routing and optimization."""

    def __init__(
        self,
        web3: Web3,
        flashbots_provider: FlashbotsProvider,
        memory_bank: MemoryBank,
        min_profit_threshold: int = Web3.to_wei(0.01, "ether"),  # 0.01 ETH
        max_slippage: Decimal = Decimal("0.005"),  # 0.5%
        max_paths: int = 3,  # Maximum number of parallel paths
    ):
        """Initialize the enhanced flash loan manager."""
        self.web3 = web3
        self.flashbots_provider = flashbots_provider
        self.memory_bank = memory_bank

        # Configuration
        self.min_profit_threshold = min_profit_threshold
        self.max_slippage = max_slippage
        self.max_paths = max_paths

        # Thread safety
        self._route_lock = AsyncLock()
        self._bundle_lock = AsyncLock()

        # Cache settings
        self._route_cache: Dict[str, Tuple[FlashLoanRoute, int]] = (
            {}
        )  # (route, timestamp)
        self._cache_ttl = 30  # 30 seconds TTL

        # Flash loan providers
        self._balancer_provider = None

    async def prepare_flash_loan_bundle(
        self, token_pair: TokenPair, amount: int, prices: Dict[str, Decimal]
    ) -> List[Transaction]:
        """
        Prepare an optimized flash loan bundle.

        Args:
            token_pair: Token pair for the arbitrage
            amount: Amount of flash loan
            prices: Current prices from different DEXs

        Returns:
            List of transactions for the bundle
        """
        async with self._bundle_lock:
            try:
                # Find optimal routes
                routes = await self._find_optimal_routes(token_pair, amount, prices)

                # Calculate gas costs and validate profitability
                gas_estimate = await self._estimate_total_gas(routes)
                if not await self._validate_profitability(routes, gas_estimate):
                    raise ValueError("Route not profitable after gas costs")

                # Prepare transactions
                transactions = []

                # Add flash loan initialization
                flash_loan_tx = await self._create_flash_loan_tx(amount)
                transactions.append(flash_loan_tx)

                # Add route transactions
                for route in routes:
                    route_txs = await self._create_route_transactions(route)
                    transactions.extend(route_txs)

                # Add flash loan repayment
                repayment_tx = await self._create_repayment_tx(amount, routes)
                transactions.append(repayment_tx)

                # Validate bundle
                if not await self._validate_bundle(transactions):
                    raise ValueError("Bundle validation failed")

                return transactions

            except Exception as e:
                logger.error(f"Failed to prepare flash loan bundle: {e}")
                raise

    async def _find_optimal_routes(
        self, token_pair: TokenPair, amount: int, prices: Dict[str, Decimal]
    ) -> List[Any]:  # TODO: Define or import FlashLoanRoute if needed
        """Find optimal arbitrage routes using parallel paths."""
        async with self._route_lock:
            # Get active DEXs
            dexes = await self.memory_bank.get_active_dexes()

            # Calculate potential routes
            all_routes = []
            for dex in dexes:
                # Get pool data
                pool_data = await dex.get_pool_data(token_pair)

                # Calculate optimal split if using this DEX
                split_amount = await self._calculate_optimal_split(
                    amount, pool_data, prices[dex.name]
                )

                if split_amount > 0:
                    # Calculate minimum output with slippage protection
                    min_out = int(split_amount * (1 - self.max_slippage))

                    # Create route segment
                    segment = RouteSegment(
                        dex_name=dex.name,
                        token_in=token_pair.token0,
                        token_out=token_pair.token1,
                        amount_in=split_amount,
                        min_amount_out=min_out,
                        pool_fee=pool_data.fee,
                    )

                    # Calculate route metrics
                    gas_estimate = await dex.estimate_swap_gas(token_pair, split_amount)
                    profit_estimate = await dex.calculate_profit(
                        token_pair, split_amount
                    )

                    route = FlashLoanRoute(
                        segments=[segment],
                        total_profit=profit_estimate,
                        total_gas=gas_estimate,
                        success_probability=0.95,  # Base probability
                    )

                    all_routes.append(route)

            # Sort routes by profitability
            all_routes.sort(key=lambda x: x.total_profit, reverse=True)

            # Select top routes within max_paths limit
            return all_routes[: self.max_paths]

    async def _calculate_optimal_split(
        self, total_amount: int, pool_data: LiquidityData, current_price: Decimal
    ) -> int:
        """Calculate optimal amount split for a pool."""
        # Consider pool liquidity
        max_amount = min(
            total_amount, int(pool_data.liquidity * Decimal("0.3"))
        )  # Use max 30% of liquidity

        # Calculate price impact
        price_impact = await self._calculate_price_impact(max_amount, pool_data)

        # Adjust amount based on price impact
        if price_impact > self.max_slippage:
            # Reduce amount to meet slippage requirement
            while price_impact > self.max_slippage and max_amount > 0:
                max_amount = int(max_amount * Decimal("0.9"))  # Reduce by 10%
                price_impact = await self._calculate_price_impact(max_amount, pool_data)

        return max_amount

    async def _calculate_price_impact(
        self, amount: int, pool_data: LiquidityData
    ) -> Decimal:
        """Calculate price impact for a given amount."""
        return Decimal(str(amount)) / Decimal(str(pool_data.liquidity))

    async def _estimate_total_gas(
        self, routes: List[Any]
    ) -> int:  # TODO: Define or import FlashLoanRoute if needed
        """Estimate total gas cost for all routes."""
        base_cost = 21000  # Base transaction cost
        flash_loan_cost = 90000  # Approximate flash loan overhead

        total_gas = base_cost + flash_loan_cost

        for route in routes:
            total_gas += route.total_gas

        return total_gas

    async def _validate_profitability(
        self,
        routes: List[Any],  # TODO: Define or import FlashLoanRoute if needed
        gas_estimate: int,
    ) -> bool:
        """Validate if routes are profitable after gas costs."""
        # Get current gas price
        gas_price = await self.flashbots_provider._estimate_gas_price()

        # Calculate total gas cost
        gas_cost = gas_estimate * gas_price.price

        # Calculate total profit
        total_profit = sum(route.total_profit for route in routes)

        # Add safety margin
        min_profit = int(
            self.min_profit_threshold * Decimal("1.1")
        )  # 10% safety margin

        return (total_profit - gas_cost) >= min_profit

    async def _create_flash_loan_tx(self, amount: int) -> Transaction:
        """Create flash loan initialization transaction."""
        try:
            # Initialize Balancer provider if not already done
            if self._balancer_provider is None:
                self._balancer_provider = BalancerFlashLoanProvider(
                    web3_client=self.web3,
                    config={
                        "network": "base",  # Use Base network as specified in config
                        "vault_address": self.web3.to_checksum_address(
                            "0xBA12222222228d8Ba445958a75a0704d566BF2C8"  # Balancer vault on Base
                        ),
                    },
                )
                await self._balancer_provider.initialize()

            # Get the token address (WETH is commonly used)
            weth_address = None
            for token in await self.memory_bank.get_token_list():
                if token.get("symbol") == "WETH":
                    weth_address = token.get("address")
                    break

            if not weth_address:
                raise ValueError("WETH token address not found")

            # Create flash loan parameters
            token_amounts = [
                {
                    "token_address": weth_address,
                    "amount": Decimal(str(amount))
                    / Decimal("1e18"),  # Convert to decimal
                    "raw_amount": amount,
                }
            ]

            # Get the receiver address (arbitrage contract)
            arbitrage_contract = await self.memory_bank.get_contract_address(
                "ArbitrageContract"
            )
            if not arbitrage_contract:
                raise ValueError("Arbitrage contract address not found")

            # Estimate gas
            gas_price = self.web3.eth.gas_price # gas_price is a property, not awaitable

            # Build transaction parameters
            tx_params = {
                "from": self.web3.eth.default_account,
                "gas": 500000,  # Estimate
                "gasPrice": gas_price,
            }

            # Create flash loan transaction
            tx = await self._balancer_provider.build_flash_loan_tx(
                tokens=[weth_address],
                amounts=[amount],
                target_contract=arbitrage_contract,
                callback_data=b"",  # Empty for now, will be filled by the contract
            )

            # Convert to Transaction object
            transaction = Transaction(
                from_=tx.get("from"), # Correct keyword argument is 'from_'
                to=tx.get("to"), # Correct keyword argument is 'to'
                data=tx.get("data"),
                gas=tx.get("gas"),
                gas_price=tx.get("gasPrice"), # Correct keyword argument is 'gas_price'
                value=tx.get("value", 0),
                nonce=tx.get("nonce"),
            )

            logger.info(f"Created flash loan transaction for {amount} wei")
            return transaction

        except Exception as e:
            logger.error(f"Failed to create flash loan transaction: {e}")
            raise

    async def _create_route_transactions(
        self, route: Any  # TODO: Define or import FlashLoanRoute if needed
    ) -> List[Transaction]:
        """Create transactions for a route."""
        transactions = []

        for segment in route.segments:
            # Get DEX interface
            dex = await self.memory_bank.get_dex(segment.dex_name)

            # Create swap transaction
            tx = await dex.create_swap_transaction(
                token_in=segment.token_in,
                token_out=segment.token_out,
                amount_in=segment.amount_in,
                min_amount_out=segment.min_amount_out,
            )

            transactions.append(tx)

        return transactions

    async def _create_repayment_tx(
        self,
        amount: int,
        routes: List[Any],  # TODO: Define or import FlashLoanRoute if needed
    ) -> Transaction:
        """
        Create flash loan repayment transaction.

        This transaction handles the repayment of the flash loan plus any fees,
        and captures the profit from the arbitrage operation.

        Args:
            amount: Original borrowed amount
            routes: List of routes used for arbitrage

        Returns:
            Transaction for repaying the flash loan
        """
        try:
            # Calculate total profit from all routes
            total_profit = sum(route.total_profit for route in routes)

            # Get the token address (WETH is commonly used)
            weth_address = None
            for token in await self.memory_bank.get_token_list():
                if token.get("symbol") == "WETH":
                    weth_address = token.get("address")
                    break

            if not weth_address:
                raise ValueError("WETH token address not found")

            # Get the arbitrage contract address
            arbitrage_contract = await self.memory_bank.get_contract_address(
                "ArbitrageContract"
            )
            if not arbitrage_contract:
                raise ValueError("Arbitrage contract address not found")

            # Load the arbitrage contract ABI
            arbitrage_abi = await self.memory_bank.load_abi("ArbitrageBot")
            if not arbitrage_abi:
                raise ValueError("Arbitrage contract ABI not found")

            # Create contract instance
            contract = self.web3.eth.contract(
                address=arbitrage_contract, abi=arbitrage_abi
            )

            # Calculate repayment amount (borrowed amount + fees)
            # For Balancer, fee is typically 0, but we add a small buffer
            fee_percentage = Decimal("0.0001")  # 0.01%
            fee_amount = int(amount * fee_percentage)
            repayment_amount = amount + fee_amount

            # Build repayment transaction
            repay_function = contract.functions.repayFlashLoan(
                weth_address, repayment_amount, total_profit
            )

            # Get current gas price (gas_price is a property, not awaitable)
            gas_price = self.web3.eth.gas_price

            # Create transaction
            tx = repay_function.build_transaction(
                {
                    "from": self.web3.eth.default_account,
                    "gas": 300000,  # Estimate
                    "gasPrice": gas_price,
                }
            )

            logger.info(
                f"Created repayment transaction for {repayment_amount} wei with profit {total_profit} wei"
            )
            return tx

        except Exception as e:
            logger.error(f"Failed to create repayment transaction: {e}")
            raise

    async def _validate_bundle(self, transactions: List[Transaction]) -> bool:
        """Validate the complete transaction bundle."""
        try:
            # Simulate bundle
            simulation = await self.flashbots_provider.simulate_bundle(transactions)

            if not simulation["success"]:
                logger.error(f"Bundle simulation failed: {simulation['error']}")
                return False

            # Validate profitability
            return await self.flashbots_provider._validate_bundle_profit(
                transactions, simulation
            )

        except Exception as e:
            logger.error(f"Bundle validation failed: {e}")
            return False


# Factory function to create a flash loan manager
async def create_enhanced_flash_loan_manager(
    web3_manager, config: Dict[str, Any] = None
) -> "EnhancedFlashLoanManager":  # Use forward reference string
    """
    Create and initialize an EnhancedFlashLoanManager instance.

    Args:
        web3_manager: Web3Manager instance
        config: Configuration dictionary

    Returns:
        Initialized EnhancedFlashLoanManager
    """
    try:
        # Create memory bank
        memory_bank = MemoryBank(
            storage_dir=config.get("storage", {}).get(
                "memory_bank_dir", "data/memory_bank"
            )
        )
        await memory_bank.initialize()

        # Create flashbots provider
        flashbots_provider = web3_manager.flashbots_provider

        # Create flash loan manager
        manager = EnhancedFlashLoanManager(
            web3=web3_manager.web3,
            flashbots_provider=flashbots_provider,
            memory_bank=memory_bank,
            min_profit_threshold=Web3.to_wei(
                config.get("flash_loan", {}).get("min_profit", "0.01"), "ether"
            ),
            max_slippage=Decimal(
                str(config.get("flash_loan", {}).get("max_slippage", "0.005"))
            ),
            max_paths=config.get("flash_loan", {}).get("max_paths", 3),
        )

        logger.info("EnhancedFlashLoanManager created successfully")
        return manager

    except Exception as e:
        logger.error(f"Failed to create EnhancedFlashLoanManager: {e}")
        raise


# Note: create_flash_loan_manager_sync function removed as it instantiated the
# removed UnifiedFlashLoanManager class and was likely only used by deprecated wrappers.
