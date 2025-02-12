"""Tests for PancakeSwap V3 quoter."""

import pytest
from decimal import Decimal

from src.core.dex.protocols.pancakeswap.quoter import Quoter
from src.core.dex.protocols.pancakeswap.types import FeeTier

from .fixtures.data import AMOUNTS, TOKENS


async def test_get_quote(web3, factory, quoter, mock_pool):
    """Test getting quote for swap."""
    # Create pools
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Create quoter
    pool_manager = factory.pool_manager
    quoter_instance = Quoter(web3, pool_manager, quoter)
    
    # Get quote
    input_amount = AMOUNTS['WETH_1']
    output_token = TOKENS['USDC']
    output_amount, price_impact = await quoter_instance.get_quote(
        input_amount,
        output_token,
        FeeTier.MEDIUM
    )
    
    # Verify quote
    assert output_amount.token == output_token
    assert output_amount.amount > 0
    assert price_impact >= 0


async def test_get_quote_nonexistent_pool(web3, factory, quoter):
    """Test getting quote for non-existent pool."""
    # Create quoter
    pool_manager = factory.pool_manager
    quoter_instance = Quoter(web3, pool_manager, quoter)
    
    # Try to get quote
    input_amount = AMOUNTS['WETH_1']
    output_token = TOKENS['USDC']
    
    with pytest.raises(ValueError, match="Pool does not exist"):
        await quoter_instance.get_quote(
            input_amount,
            output_token,
            FeeTier.MEDIUM
        )


async def test_get_quote_insufficient_liquidity(web3, factory, quoter, mock_pool):
    """Test getting quote with insufficient liquidity."""
    # Create pool with low liquidity
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(
        weth,
        usdc,
        FeeTier.MEDIUM,
        liquidity=100  # Very low liquidity
    )
    
    # Create quoter
    pool_manager = factory.pool_manager
    quoter_instance = Quoter(web3, pool_manager, quoter)
    
    # Try to get quote for large amount
    input_amount = AMOUNTS['WETH_1'] * 1000000  # Very large amount
    output_token = TOKENS['USDC']
    
    with pytest.raises(ValueError, match="Insufficient liquidity"):
        await quoter_instance.get_quote(
            input_amount,
            output_token,
            FeeTier.MEDIUM
        )


async def test_get_quote_high_price_impact(web3, factory, quoter, mock_pool):
    """Test getting quote with high price impact."""
    # Create pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Create quoter
    pool_manager = factory.pool_manager
    quoter_instance = Quoter(web3, pool_manager, quoter)
    
    # Get quote for large amount
    input_amount = AMOUNTS['WETH_1'] * 1000  # Large amount
    output_token = TOKENS['USDC']
    output_amount, price_impact = await quoter_instance.get_quote(
        input_amount,
        output_token,
        FeeTier.MEDIUM
    )
    
    # Verify high price impact
    assert price_impact > Decimal('1.0')  # > 1%


async def test_simulate_swap(web3, factory, quoter, mock_pool):
    """Test simulating swap."""
    # Create pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Create quoter
    pool_manager = factory.pool_manager
    quoter_instance = Quoter(web3, pool_manager, quoter)
    
    # Simulate swap
    amount_in = 1000000  # 1 WETH in wei
    sqrt_price_limit = 2 ** 96  # 1:1 price limit
    pool_state = await pool_manager.get_pool(weth, usdc, FeeTier.MEDIUM)
    
    amount0, amount1, next_sqrt_price = await quoter_instance.simulate_swap(
        pool_state,
        amount_in,
        sqrt_price_limit,
        True,  # exact input
        True   # zero for one
    )
    
    # Verify simulation results
    assert amount0 > 0
    assert amount1 > 0
    assert next_sqrt_price != pool_state.sqrt_price_x96


async def test_estimate_swap(web3, factory, quoter, mock_pool):
    """Test estimating swap outcome."""
    # Create pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Create quoter
    pool_manager = factory.pool_manager
    quoter_instance = Quoter(web3, pool_manager, quoter)
    
    # Estimate swap
    amount = 1000000  # 1 WETH in wei
    pool_state = await pool_manager.get_pool(weth, usdc, FeeTier.MEDIUM)
    
    amount_in, amount_out, sqrt_price_next = await quoter_instance.estimate_swap(
        pool_state.sqrt_price_x96,
        pool_state.liquidity,
        amount,
        3000,  # 0.3% fee
        True,  # exact input
        True   # zero for one
    )
    
    # Verify estimation
    assert amount_in > 0
    assert amount_out > 0
    assert sqrt_price_next != pool_state.sqrt_price_x96