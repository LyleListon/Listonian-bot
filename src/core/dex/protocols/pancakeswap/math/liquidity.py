"""Liquidity math utilities for PancakeSwap V3."""

from decimal import Decimal
from typing import Tuple

from .ticks import (
    MAX_SQRT_RATIO,
    MIN_SQRT_RATIO,
    Q96,
    get_sqrt_ratio_at_tick,
)


def get_liquidity_for_amounts(
    sqrt_ratio_x96: int,
    sqrt_ratio_a_x96: int,
    sqrt_ratio_b_x96: int,
    amount0: int,
    amount1: int
) -> int:
    """Calculate liquidity for given amounts.
    
    Args:
        sqrt_ratio_x96: Current sqrt price
        sqrt_ratio_a_x96: Lower sqrt price
        sqrt_ratio_b_x96: Upper sqrt price
        amount0: Amount of token0
        amount1: Amount of token1
        
    Returns:
        Liquidity amount
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

    if sqrt_ratio_x96 <= sqrt_ratio_a_x96:
        return get_liquidity_0(sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount0)
    elif sqrt_ratio_x96 < sqrt_ratio_b_x96:
        liquidity0 = get_liquidity_0(sqrt_ratio_x96, sqrt_ratio_b_x96, amount0)
        liquidity1 = get_liquidity_1(sqrt_ratio_a_x96, sqrt_ratio_x96, amount1)
        return min(liquidity0, liquidity1)
    else:
        return get_liquidity_1(sqrt_ratio_a_x96, sqrt_ratio_b_x96, amount1)


def get_liquidity_0(
    sqrt_ratio_a_x96: int,
    sqrt_ratio_b_x96: int,
    amount0: int
) -> int:
    """Calculate liquidity for token0.
    
    Args:
        sqrt_ratio_a_x96: Lower sqrt price
        sqrt_ratio_b_x96: Upper sqrt price
        amount0: Amount of token0
        
    Returns:
        Liquidity amount
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

    numerator = amount0 * sqrt_ratio_a_x96 * sqrt_ratio_b_x96
    denominator = sqrt_ratio_b_x96 - sqrt_ratio_a_x96
    return numerator // denominator // Q96


def get_liquidity_1(
    sqrt_ratio_a_x96: int,
    sqrt_ratio_b_x96: int,
    amount1: int
) -> int:
    """Calculate liquidity for token1.
    
    Args:
        sqrt_ratio_a_x96: Lower sqrt price
        sqrt_ratio_b_x96: Upper sqrt price
        amount1: Amount of token1
        
    Returns:
        Liquidity amount
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

    return (amount1 * Q96) // (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)


def get_amounts_for_liquidity(
    sqrt_ratio_x96: int,
    sqrt_ratio_a_x96: int,
    sqrt_ratio_b_x96: int,
    liquidity: int,
    round_up: bool = False
) -> Tuple[int, int]:
    """Calculate amounts for given liquidity.
    
    Args:
        sqrt_ratio_x96: Current sqrt price
        sqrt_ratio_a_x96: Lower sqrt price
        sqrt_ratio_b_x96: Upper sqrt price
        liquidity: Liquidity amount
        round_up: Whether to round up
        
    Returns:
        Tuple of (amount0, amount1)
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

    if sqrt_ratio_x96 <= sqrt_ratio_a_x96:
        return get_amount0_delta(
            sqrt_ratio_a_x96,
            sqrt_ratio_b_x96,
            liquidity,
            round_up
        ), 0
    elif sqrt_ratio_x96 < sqrt_ratio_b_x96:
        amount0 = get_amount0_delta(
            sqrt_ratio_x96,
            sqrt_ratio_b_x96,
            liquidity,
            round_up
        )
        amount1 = get_amount1_delta(
            sqrt_ratio_a_x96,
            sqrt_ratio_x96,
            liquidity,
            round_up
        )
        return amount0, amount1
    else:
        return 0, get_amount1_delta(
            sqrt_ratio_a_x96,
            sqrt_ratio_b_x96,
            liquidity,
            round_up
        )


def get_amount0_delta(
    sqrt_ratio_a_x96: int,
    sqrt_ratio_b_x96: int,
    liquidity: int,
    round_up: bool
) -> int:
    """Calculate token0 amount for liquidity change.
    
    Args:
        sqrt_ratio_a_x96: Lower sqrt price
        sqrt_ratio_b_x96: Upper sqrt price
        liquidity: Liquidity amount
        round_up: Whether to round up
        
    Returns:
        Amount of token0
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

    numerator = liquidity << 96
    denominator = sqrt_ratio_b_x96
    amount = (numerator * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)) // denominator

    if round_up and (numerator * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)) % denominator > 0:
        amount += 1

    return amount


def get_amount1_delta(
    sqrt_ratio_a_x96: int,
    sqrt_ratio_b_x96: int,
    liquidity: int,
    round_up: bool
) -> int:
    """Calculate token1 amount for liquidity change.
    
    Args:
        sqrt_ratio_a_x96: Lower sqrt price
        sqrt_ratio_b_x96: Upper sqrt price
        liquidity: Liquidity amount
        round_up: Whether to round up
        
    Returns:
        Amount of token1
    """
    if sqrt_ratio_a_x96 > sqrt_ratio_b_x96:
        sqrt_ratio_a_x96, sqrt_ratio_b_x96 = sqrt_ratio_b_x96, sqrt_ratio_a_x96

    amount = (liquidity * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)) // Q96

    if round_up and (liquidity * (sqrt_ratio_b_x96 - sqrt_ratio_a_x96)) % Q96 > 0:
        amount += 1

    return amount


def add_delta(x: int, y: int) -> int:
    """Add signed delta to unsigned value.
    
    Args:
        x: Unsigned value
        y: Signed delta
        
    Returns:
        Result of addition
    """
    if y < 0:
        return x - abs(y)
    else:
        return x + y