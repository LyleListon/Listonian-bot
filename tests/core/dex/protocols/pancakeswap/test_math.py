"""Tests for PancakeSwap V3 math utilities."""

import pytest
from decimal import Decimal

from src.core.dex.protocols.pancakeswap.math import (
    MAX_SQRT_RATIO,
    MIN_SQRT_RATIO,
    MAX_TICK,
    MIN_TICK,
    Q96,
    calculate_optimal_amount,
    get_amount0_delta,
    get_amount1_delta,
    get_amounts_for_liquidity,
    get_fee_growth_inside,
    get_liquidity_for_amounts,
    get_next_sqrt_price_from_input,
    get_next_sqrt_price_from_output,
    get_sqrt_ratio_at_tick,
    get_tick_at_sqrt_ratio,
    price_to_sqrt_price_x96,
    price_to_tick,
    sqrt_price_x96_to_price,
    tick_to_price,
)


def test_price_to_tick_conversion():
    """Test price to tick conversion."""
    # Test common prices
    assert price_to_tick(Decimal('1.0')) == 0
    assert price_to_tick(Decimal('2.0')) == 6932
    assert price_to_tick(Decimal('0.5')) == -6932
    
    # Test boundaries
    min_price = tick_to_price(MIN_TICK)
    max_price = tick_to_price(MAX_TICK)
    assert MIN_TICK <= price_to_tick(min_price) <= MAX_TICK
    assert MIN_TICK <= price_to_tick(max_price) <= MAX_TICK


def test_tick_to_price_conversion():
    """Test tick to price conversion."""
    # Test common ticks
    assert tick_to_price(0) == Decimal('1.0')
    assert abs(tick_to_price(6932) - Decimal('2.0')) < Decimal('0.001')
    assert abs(tick_to_price(-6932) - Decimal('0.5')) < Decimal('0.001')
    
    # Test boundaries
    assert tick_to_price(MIN_TICK) > Decimal('0')
    assert tick_to_price(MAX_TICK) < Decimal('1000000')


def test_sqrt_price_conversions():
    """Test sqrt price conversions."""
    # Test common prices
    price = Decimal('1.0')
    sqrt_price = price_to_sqrt_price_x96(price)
    assert sqrt_price == Q96
    assert sqrt_price_x96_to_price(sqrt_price) == price
    
    # Test boundaries
    assert MIN_SQRT_RATIO <= price_to_sqrt_price_x96(Decimal('0.00001'))
    assert price_to_sqrt_price_x96(Decimal('100000')) <= MAX_SQRT_RATIO


def test_liquidity_calculations():
    """Test liquidity calculations."""
    # Test liquidity for amounts
    sqrt_price = Q96  # 1:1 price
    liquidity = get_liquidity_for_amounts(
        sqrt_price,  # Current price
        sqrt_price,  # Lower bound
        sqrt_price * 2,  # Upper bound
        1000000,  # token0 amount (1 unit)
        1000000   # token1 amount (1 unit)
    )
    assert liquidity > 0
    
    # Test amounts for liquidity
    amount0, amount1 = get_amounts_for_liquidity(
        sqrt_price,  # Current price
        sqrt_price,  # Lower bound
        sqrt_price * 2,  # Upper bound
        liquidity
    )
    assert amount0 > 0
    assert amount1 > 0


def test_amount_calculations():
    """Test amount calculations."""
    liquidity = 1000000  # 1M units
    sqrt_price_a = Q96  # 1:1 price
    sqrt_price_b = Q96 * 2  # 2:1 price
    
    # Test amount0 delta
    amount0 = get_amount0_delta(
        sqrt_price_a,
        sqrt_price_b,
        liquidity,
        True  # Round up
    )
    assert amount0 > 0
    
    # Test amount1 delta
    amount1 = get_amount1_delta(
        sqrt_price_a,
        sqrt_price_b,
        liquidity,
        True  # Round up
    )
    assert amount1 > 0


def test_next_sqrt_price_calculations():
    """Test next sqrt price calculations."""
    liquidity = 1000000  # 1M units
    sqrt_price = Q96  # 1:1 price
    amount = 1000000  # 1 unit
    
    # Test input amount
    next_price = get_next_sqrt_price_from_input(
        sqrt_price,
        liquidity,
        amount,
        True  # zero for one
    )
    assert next_price < sqrt_price
    
    # Test output amount
    next_price = get_next_sqrt_price_from_output(
        sqrt_price,
        liquidity,
        amount,
        True  # zero for one
    )
    assert next_price < sqrt_price


def test_fee_growth_calculation():
    """Test fee growth calculation."""
    fee_growth = get_fee_growth_inside(
        100,  # Global fee growth
        0,    # Lower tick
        10,   # Upper tick
        5,    # Current tick
        20,   # Fee growth outside lower
        30    # Fee growth outside upper
    )
    assert fee_growth >= 0


def test_invalid_inputs():
    """Test invalid inputs are handled."""
    # Test invalid tick
    with pytest.raises(ValueError):
        get_sqrt_ratio_at_tick(MAX_TICK + 1)
        
    # Test invalid sqrt price
    with pytest.raises(ValueError):
        get_tick_at_sqrt_ratio(MAX_SQRT_RATIO + 1)
        
    # Test invalid liquidity
    with pytest.raises(ValueError):
        get_liquidity_for_amounts(0, 0, 0, 0, 0)


def test_edge_cases():
    """Test edge cases."""
    # Test minimum values
    assert get_amount0_delta(MIN_SQRT_RATIO, MIN_SQRT_RATIO, 0, False) == 0
    assert get_amount1_delta(MIN_SQRT_RATIO, MIN_SQRT_RATIO, 0, False) == 0
    
    # Test maximum values
    assert get_amount0_delta(MAX_SQRT_RATIO, MAX_SQRT_RATIO, 0, False) == 0
    assert get_amount1_delta(MAX_SQRT_RATIO, MAX_SQRT_RATIO, 0, False) == 0
    
    # Test equal prices
    sqrt_price = Q96
    assert get_amount0_delta(sqrt_price, sqrt_price, 1000000, False) == 0
    assert get_amount1_delta(sqrt_price, sqrt_price, 1000000, False) == 0