"""Validation utilities for DEX operations."""

import logging
from decimal import Decimal
from typing import List, Optional, Tuple

from web3.types import ChecksumAddress

from ..interfaces.types import (
    LiquidityInfo,
    PoolInfo,
    SwapParams,
    Token,
    TokenAmount
)

logger = logging.getLogger(__name__)


def validate_pool_health(
    pool_info: PoolInfo,
    min_liquidity: Decimal = Decimal('1000')
) -> Tuple[bool, Optional[str]]:
    """Validate pool health and usability.
    
    Args:
        pool_info: Pool information
        min_liquidity: Minimum required liquidity in USD value
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check reserves
    if (pool_info.liquidity.token0_reserve.amount <= 0 or
            pool_info.liquidity.token1_reserve.amount <= 0):
        return False, "Pool has zero reserves"

    # Check total supply
    if pool_info.liquidity.total_supply <= 0:
        return False, "Pool has zero total supply"

    # Check liquidity value
    # TODO: Implement price lookup for USD value calculation
    
    return True, None


def validate_path(
    path: List[ChecksumAddress],
    known_pools: List[PoolInfo]
) -> Tuple[bool, Optional[str]]:
    """Validate trading path exists and is healthy.
    
    Args:
        path: List of token addresses in path
        known_pools: List of known pools
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(path) < 2:
        return False, "Path must contain at least 2 tokens"

    # Check each hop has a pool
    for i in range(len(path) - 1):
        token0, token1 = path[i], path[i + 1]
        pool_found = False
        
        for pool in known_pools:
            if ((pool.token0.address == token0 and pool.token1.address == token1) or
                    (pool.token0.address == token1 and pool.token1.address == token0)):
                pool_found = True
                # Validate pool health
                is_healthy, error = validate_pool_health(pool)
                if not is_healthy:
                    return False, f"Unhealthy pool in path: {error}"
                break
                
        if not pool_found:
            return False, f"No pool found for {token0}-{token1}"

    return True, None


def validate_swap_params(
    params: SwapParams,
    max_slippage: Decimal = Decimal('5.0')  # 5%
) -> Tuple[bool, Optional[str]]:
    """Validate swap parameters.
    
    Args:
        params: Swap parameters
        max_slippage: Maximum allowed slippage percentage
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check amounts
    if params.quote.input_amount.amount <= 0:
        return False, "Invalid input amount"
        
    if params.quote.output_amount.amount <= 0:
        return False, "Invalid output amount"

    # Check slippage
    if params.slippage > max_slippage:
        return False, f"Slippage too high: {params.slippage}% > {max_slippage}%"

    # Check deadline
    if params.deadline <= 0:
        return False, "Invalid deadline"

    # Check path
    if not params.quote.path or len(params.quote.path) < 2:
        return False, "Invalid path"

    # Check price impact
    if params.quote.price_impact.is_high:
        return False, f"High price impact: {params.quote.price_impact.percentage}%"

    return True, None


def validate_reserves_change(
    old_reserves: LiquidityInfo,
    new_reserves: LiquidityInfo,
    max_change: Decimal = Decimal('20.0')  # 20%
) -> Tuple[bool, Optional[str]]:
    """Validate if reserve changes are within acceptable limits.
    
    Args:
        old_reserves: Previous reserves
        new_reserves: Current reserves
        max_change: Maximum allowed percentage change
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    for old, new in [
        (old_reserves.token0_reserve, new_reserves.token0_reserve),
        (old_reserves.token1_reserve, new_reserves.token1_reserve)
    ]:
        if old.amount == 0:
            continue
            
        change = abs(new.amount - old.amount) / old.amount * 100
        if change > max_change:
            return False, (
                f"Reserve change too high: {change}% > {max_change}% "
                f"for {old.token.symbol}"
            )

    return True, None


def validate_token_pair(
    token0: Token,
    token1: Token
) -> Tuple[bool, Optional[str]]:
    """Validate token pair is valid for trading.
    
    Args:
        token0: First token
        token1: Second token
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check addresses
    if token0.address == token1.address:
        return False, "Cannot trade token with itself"

    # Check decimals
    if token0.decimals <= 0 or token0.decimals > 18:
        return False, f"Invalid decimals for {token0.symbol}"
    if token1.decimals <= 0 or token1.decimals > 18:
        return False, f"Invalid decimals for {token1.symbol}"

    return True, None