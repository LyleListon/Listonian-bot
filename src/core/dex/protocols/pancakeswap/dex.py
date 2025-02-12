"""PancakeSwap V3 DEX implementation."""

import asyncio
import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from web3.types import ChecksumAddress

from ...interfaces import (
    BaseDEX,
    DEXType,
    LiquidityInfo,
    PoolInfo,
    SwapParams,
    SwapQuote,
    Token,
    TokenAmount,
)
from ...utils import get_contract
from .constants import (
    ADDRESSES,
    DEFAULT_FEE_TIER,
    DEFAULT_SLIPPAGE,
    ERRORS,
    FEE_AMOUNTS,
    PROTOCOL_NAME,
)
from .math import (
    price_to_sqrt_price_x96,
    sqrt_price_x96_to_price,
)
from .pool import PoolManager
from .quoter import Quoter
from .types import FeeTier, PoolState
from .validation import (
    validate_fee_tier,
    validate_pool_state,
    validate_price_impact,
)

logger = logging.getLogger(__name__)


class PancakeSwapV3(BaseDEX):
    """PancakeSwap V3 DEX implementation."""

    def __init__(
        self,
        web3_manager,
        factory_address: Optional[ChecksumAddress] = None,
        router_address: Optional[ChecksumAddress] = None,
        quoter_address: Optional[ChecksumAddress] = None
    ):
        """Initialize PancakeSwap V3 DEX.
        
        Args:
            web3_manager: Web3 manager instance
            factory_address: Optional factory contract address
            router_address: Optional router contract address
            quoter_address: Optional quoter contract address
        """
        super().__init__(
            web3_manager=web3_manager,
            factory_address=factory_address or ADDRESSES['factory'],
            router_address=router_address or ADDRESSES['router'],
            protocol=DEXType.PANCAKESWAP_V3
        )
        
        # Initialize managers
        self.pool_manager = PoolManager(web3_manager)
        self.quoter = Quoter(
            web3_manager,
            self.pool_manager,
            quoter_address or ADDRESSES['quoter']
        )
        
        # Initialize contracts
        self._factory = get_contract(
            web3_manager,
            self.factory_address,
            'pancakeswap_factory'
        )
        self._router = get_contract(
            web3_manager,
            self.router_address,
            'pancakeswap_router'
        )
        
        # Event monitoring
        self._price_callbacks: Dict[str, List[callable]] = {}
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def get_pool(
        self,
        token0: Token,
        token1: Token
    ) -> Optional[PoolInfo]:
        """Get pool for token pair.
        
        Args:
            token0: First token
            token1: Second token
            
        Returns:
            Pool info if exists, None otherwise
        """
        try:
            # Try each fee tier
            for fee_tier in FeeTier:
                pool = await self.pool_manager.get_pool(
                    token0,
                    token1,
                    fee_tier
                )
                if pool:
                    return PoolInfo(
                        address=pool.address,
                        token0=pool.token0,
                        token1=pool.token1,
                        fee=Decimal(pool.fee.value) / Decimal(1_000_000),
                        liquidity=LiquidityInfo(
                            token0_reserve=TokenAmount(
                                token=pool.token0,
                                amount=pool.liquidity
                            ),
                            token1_reserve=TokenAmount(
                                token=pool.token1,
                                amount=pool.liquidity
                            ),
                            total_supply=pool.liquidity,
                            updated_at=0  # Not used in V3
                        ),
                        protocol=self.protocol
                    )
            return None
            
        except Exception as e:
            logger.error(f"Failed to get pool: {e}")
            return None

    async def get_pools(self) -> List[PoolInfo]:
        """Get all available pools.
        
        Returns:
            List of pool information
        """
        # TODO: Implement pool discovery
        return []

    async def get_quote(
        self,
        input_amount: TokenAmount,
        output_token: Token,
        path: Optional[List[ChecksumAddress]] = None
    ) -> SwapQuote:
        """Get quote for swap.
        
        Args:
            input_amount: Input token amount
            output_token: Output token
            path: Optional specific path to use
            
        Returns:
            Swap quote with price impact
            
        Raises:
            ValueError: If no valid path exists
        """
        try:
            # Get quote
            output_amount, price_impact = await self.quoter.get_quote(
                input_amount,
                output_token,
                DEFAULT_FEE_TIER
            )

            # Estimate gas
            gas_estimate = await self._router.functions.exactInputSingle(
                (
                    input_amount.token.address,
                    output_token.address,
                    FEE_AMOUNTS[DEFAULT_FEE_TIER],
                    self.web3.provider.web3.eth.default_account,
                    2 ** 256 - 1,  # Deadline
                    input_amount.to_wei(),
                    0,  # Min output for estimation
                    0   # Price limit
                )
            ).estimate_gas()

            return SwapQuote(
                input_amount=input_amount,
                output_amount=output_amount,
                price_impact=price_impact,
                path=[input_amount.token.address, output_token.address],
                gas_estimate=gas_estimate
            )

        except Exception as e:
            logger.error(f"Failed to get quote: {e}")
            raise ValueError(f"Failed to get quote: {e}")

    async def get_price(
        self,
        base_token: Token,
        quote_token: Token
    ) -> Decimal:
        """Get current price between tokens.
        
        Args:
            base_token: Base token
            quote_token: Quote token
            
        Returns:
            Current price (quote per base)
            
        Raises:
            ValueError: If no valid path exists
        """
        try:
            # Get pool
            pool = await self.pool_manager.get_pool(
                base_token,
                quote_token,
                DEFAULT_FEE_TIER
            )
            if not pool:
                raise ValueError(ERRORS['pool_not_found'])

            # Validate pool
            valid, error = validate_pool_state(pool)
            if not valid:
                raise ValueError(error)

            # Calculate price from sqrt price
            price = sqrt_price_x96_to_price(pool.sqrt_price_x96)
            
            # Adjust if tokens are reversed
            if base_token.address != pool.token0.address:
                price = Decimal(1) / price

            return price

        except Exception as e:
            logger.error(f"Failed to get price: {e}")
            raise ValueError(f"Failed to get price: {e}")

    async def execute_swap(
        self,
        params: SwapParams
    ) -> str:
        """Execute swap transaction.
        
        Args:
            params: Swap parameters
            
        Returns:
            Transaction hash
            
        Raises:
            ValueError: If swap validation fails
            Web3Error: If transaction fails
        """
        try:
            # Build transaction
            tx = await self._router.functions.exactInputSingle(
                (
                    params.quote.input_amount.token.address,
                    params.quote.output_amount.token.address,
                    FEE_AMOUNTS[DEFAULT_FEE_TIER],
                    params.recipient,
                    params.deadline,
                    params.quote.input_amount.to_wei(),
                    params._calculate_min_out(),
                    price_to_sqrt_price_x96(params.quote.output_amount.amount)
                )
            ).build_transaction({
                'from': self.web3.provider.web3.eth.default_account,
                'gas': int(params.quote.gas_estimate * 1.1)  # Add 10% buffer
            })

            # Send transaction
            return await self.web3.send_transaction(tx)

        except Exception as e:
            logger.error(f"Failed to execute swap: {e}")
            raise ValueError(f"Failed to execute swap: {e}")

    async def find_best_path(
        self,
        input_token: Token,
        output_token: Token,
        amount: Optional[TokenAmount] = None
    ) -> Tuple[List[ChecksumAddress], Decimal]:
        """Find best path between tokens.
        
        Args:
            input_token: Input token
            output_token: Output token
            amount: Optional amount to optimize for
            
        Returns:
            Tuple of (path, expected output amount)
            
        Raises:
            ValueError: If no valid path exists
        """
        # TODO: Implement path finding
        # For now, just return direct path
        path = [input_token.address, output_token.address]
        
        # Get expected output
        if amount:
            quote = await self.get_quote(amount, output_token)
            expected = quote.output_amount.amount
        else:
            expected = Decimal(0)
            
        return path, expected

    async def validate_pool(
        self,
        pool_info: PoolInfo
    ) -> bool:
        """Validate pool health and status.
        
        Args:
            pool_info: Pool to validate
            
        Returns:
            True if pool is healthy and usable
        """
        try:
            pool = await self.pool_manager.get_pool(
                pool_info.token0,
                pool_info.token1,
                DEFAULT_FEE_TIER
            )
            if not pool:
                return False
                
            valid, _ = validate_pool_state(pool)
            return valid
            
        except Exception:
            return False

    async def monitor_price(
        self,
        pool_address: ChecksumAddress,
        callback: callable
    ) -> None:
        """Monitor price changes for pool.
        
        Args:
            pool_address: Pool to monitor
            callback: Function to call on price change
        """
        # Add callback
        if pool_address not in self._price_callbacks:
            self._price_callbacks[pool_address] = []
        self._price_callbacks[pool_address].append(callback)
        
        # Start monitoring if not already
        if pool_address not in self._monitoring_tasks:
            task = asyncio.create_task(
                self._monitor_pool(pool_address)
            )
            self._monitoring_tasks[pool_address] = task

    async def _monitor_pool(
        self,
        pool_address: ChecksumAddress
    ) -> None:
        """Monitor pool for price changes.
        
        Args:
            pool_address: Pool to monitor
        """
        try:
            # Get pool contract
            pool = get_contract(
                self.web3,
                pool_address,
                'pancakeswap_pool'
            )
            
            # Subscribe to events
            event_filter = pool.events.Swap.create_filter(
                fromBlock='latest'
            )
            
            while True:
                events = await event_filter.get_new_entries()
                for event in events:
                    # Get new price
                    sqrt_price_x96 = event.args.sqrtPriceX96
                    price = sqrt_price_x96_to_price(sqrt_price_x96)
                    
                    # Notify callbacks
                    for callback in self._price_callbacks[pool_address]:
                        await callback(price)
                        
                await asyncio.sleep(1)  # Poll every second
                
        except Exception as e:
            logger.error(f"Price monitoring failed: {e}")
            # Remove task
            if pool_address in self._monitoring_tasks:
                del self._monitoring_tasks[pool_address]