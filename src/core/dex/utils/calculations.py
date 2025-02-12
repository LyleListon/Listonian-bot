"""Utility functions for DEX calculations."""

from decimal import Decimal
from typing import Tuple

from ..interfaces.types import PriceImpact, TokenAmount


def calculate_price_impact(
    input_amount: TokenAmount,
    output_amount: TokenAmount,
    spot_price: Decimal
) -> PriceImpact:
    """Calculate price impact for a swap.
    
    Args:
        input_amount: Input token amount
        output_amount: Output token amount
        spot_price: Current spot price
        
    Returns:
        PriceImpact calculation result
    """
    # Calculate actual price
    actual_price = (
        output_amount.amount / input_amount.amount
        if input_amount.amount != 0
        else Decimal(0)
    )

    # Calculate impact
    if spot_price == 0:
        return PriceImpact(
            percentage=Decimal(0),
            base_price=spot_price,
            actual_price=actual_price,
            is_high=False
        )

    impact = abs((actual_price - spot_price) / spot_price * 100)
    
    return PriceImpact(
        percentage=impact,
        base_price=spot_price,
        actual_price=actual_price,
        is_high=impact > Decimal('1.0')  # > 1% is considered high
    )


def calculate_optimal_amount(
    reserve0: Decimal,
    reserve1: Decimal,
    fee: Decimal
) -> Decimal:
    """Calculate optimal swap amount for maximum profit.
    
    Args:
        reserve0: Reserve of input token
        reserve1: Reserve of output token
        fee: Swap fee percentage
        
    Returns:
        Optimal input amount
    """
    # Using sqrt((r0 * r1 * (1 - fee)) / (1 + fee)) - r0
    # Derived from solving d(output)/d(input) = 0
    fee_multiplier = (Decimal(1) - fee)
    denominator = (Decimal(1) + fee)
    
    if reserve0 == 0 or reserve1 == 0:
        return Decimal(0)
        
    sqrt_term = (reserve0 * reserve1 * fee_multiplier).sqrt()
    optimal = (sqrt_term / denominator) - reserve0
    
    return max(optimal, Decimal(0))


def get_amount_out(
    amount_in: Decimal,
    reserve_in: Decimal,
    reserve_out: Decimal,
    fee: Decimal
) -> Decimal:
    """Calculate output amount for constant product AMM.
    
    Args:
        amount_in: Input amount
        reserve_in: Input token reserve
        reserve_out: Output token reserve
        fee: Swap fee percentage
        
    Returns:
        Expected output amount
    """
    if amount_in <= 0:
        return Decimal(0)
        
    amount_with_fee = amount_in * (Decimal(1) - fee)
    numerator = amount_with_fee * reserve_out
    denominator = reserve_in + amount_with_fee
    
    if denominator == 0:
        return Decimal(0)
        
    return numerator / denominator


def get_amount_in(
    amount_out: Decimal,
    reserve_in: Decimal,
    reserve_out: Decimal,
    fee: Decimal
) -> Decimal:
    """Calculate required input amount for desired output.
    
    Args:
        amount_out: Desired output amount
        reserve_in: Input token reserve
        reserve_out: Output token reserve
        fee: Swap fee percentage
        
    Returns:
        Required input amount
    """
    if amount_out <= 0:
        return Decimal(0)
        
    if amount_out >= reserve_out:
        raise ValueError("Insufficient liquidity")
        
    numerator = reserve_in * amount_out
    denominator = (reserve_out - amount_out) * (Decimal(1) - fee)
    
    if denominator == 0:
        raise ValueError("Invalid reserves")
        
    return (numerator / denominator) + Decimal(1)


def calculate_liquidity_bounds(
    reserve0: Decimal,
    reserve1: Decimal,
    current_price: Decimal,
    slippage: Decimal
) -> Tuple[Decimal, Decimal]:
    """Calculate safe liquidity bounds for a pool.
    
    Args:
        reserve0: Reserve of token0
        reserve1: Reserve of token1
        current_price: Current market price
        slippage: Maximum acceptable slippage
        
    Returns:
        Tuple of (min_amount, max_amount) for safe trades
    """
    # Calculate k (constant product)
    k = reserve0 * reserve1
    
    # Calculate price range
    min_price = current_price * (Decimal(1) - slippage)
    max_price = current_price * (Decimal(1) + slippage)
    
    # Calculate amount bounds
    max_amount = (k / min_price).sqrt() - reserve0
    min_amount = (k / max_price).sqrt() - reserve0
    
    return (
        max(min_amount, Decimal(0)),
        max(max_amount, Decimal(0))
    )