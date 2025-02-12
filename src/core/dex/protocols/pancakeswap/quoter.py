"""Quote handling for PancakeSwap V3."""

import logging
from decimal import Decimal
from typing import List, Optional, Tuple

from web3.types import ChecksumAddress

from ...interfaces.types import TokenAmount
from ...utils import get_contract
from .constants import DEFAULT_SLIPPAGE, ERRORS
from .math import (
    compute_swap_step,
    estimate_swap,
    get_amount0_delta,
    get_amount1_delta,
    get_next_sqrt_price_from_input,
    get_next_sqrt_price_from_output,
    price_to_sqrt_price_x96,
)
from .pool import PoolManager
from .types import FeeTier, PoolState, SwapState, Token
from .validation import validate_price_impact, validate_pool_state

logger = logging.getLogger(__name__)


class Quoter:
    """Quote handler for PancakeSwap V3."""

    def __init__(
        self,
        web3_manager,
        pool_manager: PoolManager,
        quoter_address: ChecksumAddress
    ):
        """Initialize quoter.
        
        Args:
            web3_manager: Web3 manager instance
            pool_manager: Pool manager instance
            quoter_address: Quoter contract address
        """
        self.web3 = web3_manager
        self.pool_manager = pool_manager
        self.quoter = get_contract(
            web3_manager,
            quoter_address,
            'pancakeswap_quoter'
        )

    async def get_quote(
        self,
        input_amount: TokenAmount,
        output_token: Token,
        fee_tier: FeeTier,
        slippage: Decimal = DEFAULT_SLIPPAGE
    ) -> Tuple[TokenAmount, Decimal]:
        """Get quote for swap.
        
        Args:
            input_amount: Input token amount
            output_token: Output token
            fee_tier: Fee tier to use
            slippage: Slippage tolerance
            
        Returns:
            Tuple of (output amount, price impact)
            
        Raises:
            ValueError: If quote fails
        """
        try:
            # Get pool
            pool = await self.pool_manager.get_pool(
                input_amount.token,
                output_token,
                fee_tier
            )
            if not pool:
                raise ValueError(ERRORS['pool_not_found'])

            # Validate pool
            valid, error = validate_pool_state(pool)
            if not valid:
                raise ValueError(error)

            # Get quote from contract
            zero_for_one = input_amount.token.address == pool.token0.address
            quote_result = await self.quoter.functions.quoteExactInputSingle(
                input_amount.token.address,
                output_token.address,
                pool.fee.value,
                input_amount.to_wei(),
                0  # No sqrt price limit
            ).call()

            output_amount = TokenAmount(
                token=output_token,
                amount=Decimal(quote_result[0]) / Decimal(10 ** output_token.decimals)
            )

            # Calculate price impact
            price_impact = await self._calculate_price_impact(
                pool,
                input_amount,
                output_amount,
                zero_for_one
            )

            # Validate price impact
            valid, error = validate_price_impact(price_impact)
            if not valid:
                raise ValueError(error)

            return output_amount, price_impact

        except Exception as e:
            logger.error(f"Failed to get quote: {e}")
            raise ValueError(f"Failed to get quote: {e}")

    async def simulate_swap(
        self,
        pool: PoolState,
        amount_specified: int,
        sqrt_price_limit_x96: int,
        exact_input: bool,
        zero_for_one: bool
    ) -> Tuple[int, int, int]:
        """Simulate swap to get amounts and next sqrt price.
        
        Args:
            pool: Pool state
            amount_specified: Amount to swap
            sqrt_price_limit_x96: Price limit
            exact_input: True if exact input, False if exact output
            zero_for_one: True if swapping token0 for token1
            
        Returns:
            Tuple of (amount0, amount1, next_sqrt_price_x96)
        """
        state = SwapState(
            amount_specified_remaining=amount_specified,
            amount_calculated=0,
            sqrt_price_x96=pool.sqrt_price_x96,
            tick=pool.tick,
            liquidity=pool.liquidity,
            fee_growth_global=0
        )

        while state.amount_specified_remaining != 0:
            # Get next sqrt price
            sqrt_price_next = await self._get_next_sqrt_price(
                state,
                sqrt_price_limit_x96,
                pool.fee.value,
                exact_input,
                zero_for_one
            )

            # Compute swap step
            sqrt_ratio_next, amount_in, amount_out, fee = compute_swap_step(
                state.sqrt_price_x96,
                sqrt_price_next,
                state.liquidity,
                state.amount_specified_remaining,
                pool.fee.value,
                exact_input,
                zero_for_one
            )

            # Update state
            if exact_input:
                state.amount_specified_remaining -= (amount_in + fee)
                state.amount_calculated = state.amount_calculated + amount_out
            else:
                state.amount_specified_remaining -= amount_out
                state.amount_calculated = state.amount_calculated + amount_in + fee

            state.sqrt_price_x96 = sqrt_ratio_next

        return (
            state.amount_calculated,
            state.amount_specified_remaining,
            state.sqrt_price_x96
        )

    async def _calculate_price_impact(
        self,
        pool: PoolState,
        input_amount: TokenAmount,
        output_amount: TokenAmount,
        zero_for_one: bool
    ) -> Decimal:
        """Calculate price impact for swap.
        
        Args:
            pool: Pool state
            input_amount: Input amount
            output_amount: Output amount
            zero_for_one: True if swapping token0 for token1
            
        Returns:
            Price impact percentage
        """
        # Get amounts in pool units
        amount_in = input_amount.to_wei()
        amount_out = output_amount.to_wei()

        # Calculate expected output at current price
        if zero_for_one:
            expected_out = get_amount1_delta(
                pool.sqrt_price_x96,
                pool.sqrt_price_x96,
                amount_in,
                False
            )
        else:
            expected_out = get_amount0_delta(
                pool.sqrt_price_x96,
                pool.sqrt_price_x96,
                amount_in,
                False
            )

        # Calculate price impact
        if expected_out == 0:
            return Decimal(0)

        impact = abs(Decimal(expected_out - amount_out) / Decimal(expected_out))
        return impact * 100  # Convert to percentage

    async def _get_next_sqrt_price(
        self,
        state: SwapState,
        sqrt_price_limit_x96: int,
        fee_pips: int,
        exact_input: bool,
        zero_for_one: bool
    ) -> int:
        """Get next sqrt price for swap step.
        
        Args:
            state: Current swap state
            sqrt_price_limit_x96: Price limit
            fee_pips: Fee in pips (1/1000000)
            exact_input: True if exact input
            zero_for_one: True if swapping token0 for token1
            
        Returns:
            Next sqrt price
        """
        if exact_input:
            return get_next_sqrt_price_from_input(
                state.sqrt_price_x96,
                state.liquidity,
                state.amount_specified_remaining,
                zero_for_one
            )
        else:
            return get_next_sqrt_price_from_output(
                state.sqrt_price_x96,
                state.liquidity,
                state.amount_specified_remaining,
                zero_for_one
            )