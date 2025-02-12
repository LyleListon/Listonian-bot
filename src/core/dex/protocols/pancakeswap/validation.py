"""Validation utilities for PancakeSwap V3."""

import logging
from decimal import Decimal
from typing import Optional, Tuple

from .constants import (
    DEFAULT_SLIPPAGE,
    ERRORS,
    FEE_TIERS,
    MAX_PRICE,
    MAX_TICK_TRAVEL,
    MIN_LIQUIDITY,
    MIN_PRICE,
)
from .math import (
    MAX_TICK,
    MIN_TICK,
    get_tick_at_sqrt_ratio,
    price_to_tick,
    tick_to_price,
)
from .types import FeeTier, PoolState

logger = logging.getLogger(__name__)


def validate_fee_tier(fee_tier: FeeTier) -> Tuple[bool, Optional[str]]:
    """Validate fee tier is supported.
    
    Args:
        fee_tier: Fee tier to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if fee_tier not in FEE_TIERS:
        return False, ERRORS['invalid_fee_tier']
    return True, None


def validate_price_limits(
    price: Decimal,
    slippage: Decimal = DEFAULT_SLIPPAGE
) -> Tuple[bool, Optional[str]]:
    """Validate price is within allowed range.
    
    Args:
        price: Price to validate
        slippage: Slippage tolerance
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Add slippage buffer
    min_price = MIN_PRICE * (1 - slippage)
    max_price = MAX_PRICE * (1 + slippage)
    
    if price < min_price or price > max_price:
        return False, ERRORS['invalid_price_limit']
    return True, None


def validate_tick(tick: int) -> Tuple[bool, Optional[str]]:
    """Validate tick is within allowed range.
    
    Args:
        tick: Tick to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if tick < MIN_TICK or tick > MAX_TICK:
        return False, f"Tick {tick} outside allowed range [{MIN_TICK}, {MAX_TICK}]"
    return True, None


def validate_sqrt_price(sqrt_price_x96: int) -> Tuple[bool, Optional[str]]:
    """Validate sqrt price is valid.
    
    Args:
        sqrt_price_x96: Sqrt price in Q96.96 format
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        tick = get_tick_at_sqrt_ratio(sqrt_price_x96)
        return validate_tick(tick)
    except Exception as e:
        return False, f"Invalid sqrt price: {e}"


def validate_tick_range(
    tick_lower: int,
    tick_upper: int
) -> Tuple[bool, Optional[str]]:
    """Validate tick range is valid.
    
    Args:
        tick_lower: Lower tick
        tick_upper: Upper tick
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate individual ticks
    valid, error = validate_tick(tick_lower)
    if not valid:
        return False, error
        
    valid, error = validate_tick(tick_upper)
    if not valid:
        return False, error
        
    # Validate range
    if tick_lower >= tick_upper:
        return False, "Lower tick must be less than upper tick"
        
    # Validate range size
    if tick_upper - tick_lower > MAX_TICK_TRAVEL:
        return False, f"Tick range too large (max {MAX_TICK_TRAVEL})"
        
    return True, None


def validate_price_range(
    price_lower: Decimal,
    price_upper: Decimal,
    slippage: Decimal = DEFAULT_SLIPPAGE
) -> Tuple[bool, Optional[str]]:
    """Validate price range is valid.
    
    Args:
        price_lower: Lower price
        price_upper: Upper price
        slippage: Slippage tolerance
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate individual prices
    valid, error = validate_price_limits(price_lower, slippage)
    if not valid:
        return False, error
        
    valid, error = validate_price_limits(price_upper, slippage)
    if not valid:
        return False, error
        
    # Convert to ticks and validate range
    tick_lower = price_to_tick(price_lower)
    tick_upper = price_to_tick(price_upper)
    return validate_tick_range(tick_lower, tick_upper)


def validate_pool_state(
    pool: PoolState,
    min_liquidity: int = MIN_LIQUIDITY
) -> Tuple[bool, Optional[str]]:
    """Validate pool state is healthy.
    
    Args:
        pool: Pool state to validate
        min_liquidity: Minimum required liquidity
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check liquidity
    if pool.liquidity < min_liquidity:
        return False, ERRORS['insufficient_liquidity']
        
    # Validate sqrt price
    valid, error = validate_sqrt_price(pool.sqrt_price_x96)
    if not valid:
        return False, error
        
    # Validate tick
    valid, error = validate_tick(pool.tick)
    if not valid:
        return False, error
        
    # Validate fee tier
    valid, error = validate_fee_tier(pool.fee)
    if not valid:
        return False, error
        
    # Check if pool is locked
    if not pool.unlocked:
        return False, "Pool is locked"
        
    return True, None


def validate_price_impact(
    price_impact: Decimal,
    max_impact: Decimal = Decimal("0.01")  # 1%
) -> Tuple[bool, Optional[str]]:
    """Validate price impact is acceptable.
    
    Args:
        price_impact: Price impact percentage
        max_impact: Maximum allowed impact
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if price_impact > max_impact:
        return False, ERRORS['price_impact_high']
    return True, None