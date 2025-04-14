"""Tests for helper functions."""

import pytest

from arbitrage_bot.common.utils.helpers import (
    calculate_percentage,
    calculate_price_impact,
    calculate_profit,
    calculate_roi,
    format_amount,
    safe_divide,
)


def test_format_amount():
    """Test format_amount function."""
    # Test with default decimals
    assert format_amount(1.23456789) == "1.234567890000000000"
    
    # Test with custom decimals
    assert format_amount(1.23456789, decimals=2) == "1.23"
    assert format_amount(1.23456789, decimals=4) == "1.2346"
    assert format_amount(1.23456789, decimals=0) == "1"


def test_calculate_percentage():
    """Test calculate_percentage function."""
    # Test normal case
    assert calculate_percentage(25, 100) == 25.0
    
    # Test zero total
    assert calculate_percentage(25, 0) == 0.0
    
    # Test zero value
    assert calculate_percentage(0, 100) == 0.0


def test_calculate_price_impact():
    """Test calculate_price_impact function."""
    # Test normal case
    assert calculate_price_impact(1.0, 3400.0, 3500.0) == pytest.approx(2.857143, abs=1e-6)
    
    # Test zero price impact
    assert calculate_price_impact(1.0, 3500.0, 3500.0) == 0.0
    
    # Test zero expected output
    assert calculate_price_impact(0.0, 0.0, 3500.0) == 0.0


def test_calculate_profit():
    """Test calculate_profit function."""
    # Test profitable trade without fees
    assert calculate_profit(1.0, 1.05) == 0.05
    
    # Test profitable trade with gas cost
    assert calculate_profit(1.0, 1.05, 0.01) == 0.04
    
    # Test profitable trade with gas cost and flash loan fee
    assert calculate_profit(1.0, 1.05, 0.01, 0.003) == 0.037
    
    # Test unprofitable trade
    assert calculate_profit(1.0, 0.98, 0.01) == -0.03


def test_calculate_roi():
    """Test calculate_roi function."""
    # Test profitable trade without fees
    assert calculate_roi(1.0, 1.05) == 5.0
    
    # Test profitable trade with gas cost
    assert calculate_roi(1.0, 1.05, 0.01) == 4.0
    
    # Test profitable trade with gas cost and flash loan fee
    assert calculate_roi(1.0, 1.05, 0.01, 0.003) == 3.7
    
    # Test unprofitable trade
    assert calculate_roi(1.0, 0.98, 0.01) == -3.0
    
    # Test zero input amount
    assert calculate_roi(0.0, 0.0) == 0.0


def test_safe_divide():
    """Test safe_divide function."""
    # Test normal division
    assert safe_divide(10.0, 2.0) == 5.0
    
    # Test division by zero with default
    assert safe_divide(10.0, 0.0) == 0.0
    
    # Test division by zero with custom default
    assert safe_divide(10.0, 0.0, default=float("inf")) == float("inf")
