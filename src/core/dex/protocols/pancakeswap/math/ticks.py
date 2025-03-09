"""Tick math utilities for PancakeSwap V3."""

import math
from decimal import Decimal
from typing import Tuple

# Constants
MIN_TICK = -887272
MAX_TICK = 887272
Q96 = 2 ** 96
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342
MIN_SQRT_RATIO = 4295128739


def price_to_sqrt_price_x96(price: Decimal) -> int:
    """Convert price to Q96.96 square root price.
    
    Args:
        price: Price as decimal
        
    Returns:
        Square root price in Q96.96 format
    """
    return int((price * Decimal(2 ** 96)).sqrt())


def sqrt_price_x96_to_price(sqrt_price_x96: int) -> Decimal:
    """Convert Q96.96 square root price to price.
    
    Args:
        sqrt_price_x96: Square root price in Q96.96 format
        
    Returns:
        Price as decimal
    """
    return (Decimal(sqrt_price_x96) / Decimal(2 ** 96)) ** 2


def tick_to_price(tick: int) -> Decimal:
    """Convert tick index to price.
    
    Args:
        tick: Tick index
        
    Returns:
        Price as decimal
    """
    return Decimal(1.0001) ** tick


def price_to_tick(price: Decimal) -> int:
    """Convert price to closest tick index.
    
    Args:
        price: Price as decimal
        
    Returns:
        Closest tick index
    """
    return int(math.log(float(price), 1.0001))


def get_tick_at_sqrt_ratio(sqrt_ratio_x96: int) -> int:
    """Get tick index for square root price.
    
    Args:
        sqrt_ratio_x96: Square root price in Q96.96 format
        
    Returns:
        Tick index
    """
    ratio = Decimal(sqrt_ratio_x96) / Decimal(2 ** 96)
    return price_to_tick(ratio * ratio)


def get_sqrt_ratio_at_tick(tick: int) -> int:
    """Get square root price for tick index.
    
    Args:
        tick: Tick index
        
    Returns:
        Square root price in Q96.96 format
    """
    if tick < MIN_TICK:
        tick = MIN_TICK
    elif tick > MAX_TICK:
        tick = MAX_TICK
        
    price = tick_to_price(tick)
    return price_to_sqrt_price_x96(price)


def get_next_sqrt_price_from_input(
    sqrt_price_x96: int,
    liquidity: int,
    amount_in: int,
    zero_for_one: bool
) -> int:
    """Calculate next sqrt price from token input.
    
    Args:
        sqrt_price_x96: Current sqrt price
        liquidity: Current liquidity
        amount_in: Input amount
        zero_for_one: True if swapping token0 for token1
        
    Returns:
        Next sqrt price in Q96.96 format
    """
    if zero_for_one:
        # Swapping token0 for token1
        numerator = liquidity << 96
        denominator = liquidity + (amount_in * sqrt_price_x96)
        return (numerator // denominator) if denominator != 0 else 0
    else:
        # Swapping token1 for token0
        product = sqrt_price_x96 * ((amount_in << 96) // liquidity)
        return sqrt_price_x96 + (product // Q96)


def get_next_sqrt_price_from_output(
    sqrt_price_x96: int,
    liquidity: int,
    amount_out: int,
    zero_for_one: bool
) -> int:
    """Calculate next sqrt price from token output.
    
    Args:
        sqrt_price_x96: Current sqrt price
        liquidity: Current liquidity
        amount_out: Output amount
        zero_for_one: True if swapping token0 for token1
        
    Returns:
        Next sqrt price in Q96.96 format
    """
    if zero_for_one:
        # Swapping token0 for token1
        quotient = (amount_out << 96) // liquidity
        return sqrt_price_x96 + quotient
    else:
        # Swapping token1 for token0
        numerator = liquidity << 96
        denominator = liquidity - amount_out
        return (numerator // denominator) if denominator != 0 else MAX_SQRT_RATIO


def get_amount_delta(
    sqrt_ratio_a_x96: int,
    sqrt_ratio_b_x96: int,
    liquidity: int,
    round_up: bool
) -> Tuple[int, int]:
    """Calculate amount delta between two sqrt prices.
    
    Args:
        sqrt_ratio_a_x96: First sqrt price
        sqrt_ratio_b_x96: Second sqrt price
        liquidity: Liquidity amount
        round_up: Whether to round up
        
    Returns:
        Tuple of (amount0, amount1)
    """
    # Ensure sqrt_ratio_a_x96 <= sqrt_ratio_b_x96
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

    # Calculate amount0
    numerator = (liquidity << 96) * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)
    denominator = sqrt_ratio_b_x96
    amount0 = numerator // denominator

    # Calculate amount1
    amount1 = liquidity * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96) // Q96

    if round_up:
        if numerator % denominator > 0:
            amount0 += 1
        if amount1 % Q96 > 0:
            amount1 += 1

    return amount0, amount1


def get_fee_growth_inside(
    fee_growth_global: int,
    tick_lower: int,
    tick_upper: int,
    tick_current: int,
    fee_growth_outside_lower: int,
    fee_growth_outside_upper: int
) -> int:
    """Calculate fee growth inside a tick range.
    
    Args:
        fee_growth_global: Global fee growth
        tick_lower: Lower tick
        tick_upper: Upper tick
        tick_current: Current tick
        fee_growth_outside_lower: Fee growth outside lower tick
        fee_growth_outside_upper: Fee growth outside upper tick
        
    Returns:
        Fee growth inside tick range
    """
    # Calculate fee growth below
    fee_growth_below = (
        fee_growth_outside_lower
        if tick_current >= tick_lower
        else fee_growth_global - fee_growth_outside_lower
    )

    # Calculate fee growth above
    fee_growth_above = (
        fee_growth_outside_upper
        if tick_current < tick_upper
        else fee_growth_global - fee_growth_outside_upper
    )

    return fee_growth_global - fee_growth_below - fee_growth_above