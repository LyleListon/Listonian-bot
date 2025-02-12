"""Swap math utilities for PancakeSwap V3."""

from decimal import Decimal
from typing import Tuple

from .liquidity import (
    get_amount0_delta,
    get_amount1_delta,
)
from .ticks import (
    MAX_SQRT_RATIO,
    MIN_SQRT_RATIO,
    Q96,
    get_next_sqrt_price_from_input,
    get_next_sqrt_price_from_output,
)


def compute_swap_step(
    sqrt_ratio_current: int,
    sqrt_ratio_target: int,
    liquidity: int,
    amount_remaining: int,
    fee_pips: int,
    exact_in: bool,
    zero_for_one: bool
) -> Tuple[int, int, int, int]:
    """Compute a single step of a swap.
    
    Args:
        sqrt_ratio_current: Current sqrt price
        sqrt_ratio_target: Target sqrt price
        liquidity: Current liquidity
        amount_remaining: Remaining amount to swap
        fee_pips: Fee in pips (1/1000000)
        exact_in: True if exact input, False if exact output
        zero_for_one: True if swapping token0 for token1
        
    Returns:
        Tuple of (
            sqrt_ratio_next,
            amount_in,
            amount_out,
            fee_amount
        )
    """
    if zero_for_one:
        sqrt_ratio_target = max(sqrt_ratio_target, MIN_SQRT_RATIO)
        sqrt_ratio_next = min(
            sqrt_ratio_current,
            sqrt_ratio_target
        )
    else:
        sqrt_ratio_target = min(sqrt_ratio_target, MAX_SQRT_RATIO)
        sqrt_ratio_next = min(
            sqrt_ratio_current,
            sqrt_ratio_target
        )

    amount_in = 0
    amount_out = 0
    fee_amount = 0

    if exact_in:
        # Calculate max input amount
        max_amount_in = compute_max_amount_in(
            sqrt_ratio_current,
            sqrt_ratio_target,
            liquidity,
            zero_for_one
        )

        # Apply fee
        amount_remaining_less_fee = (
            amount_remaining * (1_000_000 - fee_pips)
        ) // 1_000_000

        if amount_remaining_less_fee < max_amount_in:
            # Can complete swap in this step
            sqrt_ratio_next = get_next_sqrt_price_from_input(
                sqrt_ratio_current,
                liquidity,
                amount_remaining_less_fee,
                zero_for_one
            )
        else:
            # Will only partially complete swap
            sqrt_ratio_next = sqrt_ratio_target

        amount_in = get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        ) if zero_for_one else get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        )

        amount_out = get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            False
        ) if zero_for_one else get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            False
        )

        # Calculate fee amount
        if amount_remaining > amount_in:
            fee_amount = amount_remaining - amount_in
        else:
            fee_amount = (amount_in * fee_pips) // (1_000_000 - fee_pips)

    else:  # exact_out
        # Calculate max output amount
        max_amount_out = compute_max_amount_out(
            sqrt_ratio_current,
            sqrt_ratio_target,
            liquidity,
            zero_for_one
        )

        if amount_remaining < max_amount_out:
            # Can complete swap in this step
            sqrt_ratio_next = get_next_sqrt_price_from_output(
                sqrt_ratio_current,
                liquidity,
                amount_remaining,
                zero_for_one
            )
        else:
            # Will only partially complete swap
            sqrt_ratio_next = sqrt_ratio_target

        amount_in = get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        ) if zero_for_one else get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        )

        amount_out = get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            False
        ) if zero_for_one else get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            False
        )

        # Calculate fee amount
        fee_amount = (amount_in * fee_pips) // 1_000_000

    return sqrt_ratio_next, amount_in, amount_out, fee_amount


def compute_max_amount_in(
    sqrt_ratio_current: int,
    sqrt_ratio_target: int,
    liquidity: int,
    zero_for_one: bool
) -> int:
    """Compute maximum input amount for price range.
    
    Args:
        sqrt_ratio_current: Current sqrt price
        sqrt_ratio_target: Target sqrt price
        liquidity: Current liquidity
        zero_for_one: True if swapping token0 for token1
        
    Returns:
        Maximum input amount
    """
    if zero_for_one:
        return get_amount0_delta(
            sqrt_ratio_target,
            sqrt_ratio_current,
            liquidity,
            True
        )
    else:
        return get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_target,
            liquidity,
            True
        )


def compute_max_amount_out(
    sqrt_ratio_current: int,
    sqrt_ratio_target: int,
    liquidity: int,
    zero_for_one: bool
) -> int:
    """Compute maximum output amount for price range.
    
    Args:
        sqrt_ratio_current: Current sqrt price
        sqrt_ratio_target: Target sqrt price
        liquidity: Current liquidity
        zero_for_one: True if swapping token0 for token1
        
    Returns:
        Maximum output amount
    """
    if zero_for_one:
        return get_amount1_delta(
            sqrt_ratio_target,
            sqrt_ratio_current,
            liquidity,
            False
        )
    else:
        return get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_target,
            liquidity,
            False
        )


def estimate_swap(
    sqrt_ratio_current: int,
    liquidity: int,
    amount: int,
    fee_pips: int,
    exact_in: bool,
    zero_for_one: bool
) -> Tuple[int, int, int]:
    """Estimate swap outcome.
    
    Args:
        sqrt_ratio_current: Current sqrt price
        liquidity: Current liquidity
        amount: Amount to swap
        fee_pips: Fee in pips (1/1000000)
        exact_in: True if exact input, False if exact output
        zero_for_one: True if swapping token0 for token1
        
    Returns:
        Tuple of (amount_in, amount_out, sqrt_ratio_next)
    """
    if exact_in:
        # Calculate amount after fees
        amount_after_fees = (
            amount * (1_000_000 - fee_pips)
        ) // 1_000_000

        # Calculate next sqrt price
        sqrt_ratio_next = get_next_sqrt_price_from_input(
            sqrt_ratio_current,
            liquidity,
            amount_after_fees,
            zero_for_one
        )

        # Calculate amounts
        amount_in = get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        ) if zero_for_one else get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        )

        amount_out = get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            False
        ) if zero_for_one else get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            False
        )

    else:  # exact_out
        # Calculate next sqrt price
        sqrt_ratio_next = get_next_sqrt_price_from_output(
            sqrt_ratio_current,
            liquidity,
            amount,
            zero_for_one
        )

        # Calculate amounts
        amount_in = get_amount0_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        ) if zero_for_one else get_amount1_delta(
            sqrt_ratio_current,
            sqrt_ratio_next,
            liquidity,
            True
        )

        amount_out = amount

        # Add fees to input amount
        amount_in = (amount_in * 1_000_000) // (1_000_000 - fee_pips)

    return amount_in, amount_out, sqrt_ratio_next