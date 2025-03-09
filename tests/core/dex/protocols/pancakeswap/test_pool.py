"""Tests for PancakeSwap V3 pool management."""

import pytest
from decimal import Decimal

from src.core.dex.protocols.pancakeswap.pool import PoolManager
from src.core.dex.protocols.pancakeswap.types import FeeTier

from .fixtures.data import TOKENS


async def test_get_pool(web3, factory, mock_pool):
    """Test getting pool information."""
    # Create pool manager
    pool_manager = PoolManager(web3)
    pool_manager._factory = factory
    
    # Create mock pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Get pool
    pool = await pool_manager.get_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Verify pool
    assert pool is not None
    assert pool.token0 == weth
    assert pool.token1 == usdc
    assert pool.fee == FeeTier.MEDIUM
    assert pool.liquidity > 0


async def test_get_nonexistent_pool(web3, factory):
    """Test getting non-existent pool."""
    # Create pool manager
    pool_manager = PoolManager(web3)
    pool_manager._factory = factory
    
    # Try to get non-existent pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = await pool_manager.get_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Verify no pool returned
    assert pool is None


async def test_get_pool_with_invalid_fee(web3, factory, mock_pool):
    """Test getting pool with invalid fee tier."""
    # Create pool manager
    pool_manager = PoolManager(web3)
    pool_manager._factory = factory
    
    # Create mock pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Try to get pool with wrong fee
    pool = await pool_manager.get_pool(weth, usdc, FeeTier.LOW)
    
    # Verify no pool returned
    assert pool is None


async def test_get_pool_with_reversed_tokens(web3, factory, mock_pool):
    """Test getting pool with reversed token order."""
    # Create pool manager
    pool_manager = PoolManager(web3)
    pool_manager._factory = factory
    
    # Create mock pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Get pool with reversed tokens
    pool = await pool_manager.get_pool(usdc, weth, FeeTier.MEDIUM)
    
    # Verify pool returned with correct token order
    assert pool is not None
    assert pool.token0 == weth
    assert pool.token1 == usdc


async def test_get_pool_price(web3, factory, mock_pool):
    """Test getting pool price."""
    # Create pool manager
    pool_manager = PoolManager(web3)
    pool_manager._factory = factory
    
    # Create mock pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(
        weth,
        usdc,
        FeeTier.MEDIUM,
        sqrt_price_x96=2 ** 96  # 1:1 price
    )
    
    # Get pool state
    state = await pool_manager.get_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Get price
    price = await pool_manager.get_pool_price(state)
    
    # Verify price
    assert price == Decimal('1.0')


async def test_get_ticks(web3, factory, mock_pool):
    """Test getting tick data."""
    # Create pool manager
    pool_manager = PoolManager(web3)
    pool_manager._factory = factory
    
    # Create mock pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Initialize some ticks
    pool.ticks = {
        -60: {'liquidity_net': 1000},
        0: {'liquidity_net': 2000},
        60: {'liquidity_net': -3000}
    }
    
    # Get pool state
    state = await pool_manager.get_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Get ticks
    ticks = await pool_manager.get_ticks(state, -100, 100)
    
    # Verify ticks
    assert len(ticks) == 3
    assert ticks[0]['liquidity_net'] == 1000
    assert ticks[60]['liquidity_net'] == -3000


async def test_get_observations(web3, factory, mock_pool):
    """Test getting price observations."""
    # Create pool manager
    pool_manager = PoolManager(web3)
    pool_manager._factory = factory
    
    # Create mock pool
    weth = TOKENS['WETH']
    usdc = TOKENS['USDC']
    pool = mock_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Initialize some observations
    pool.observations = [
        (0, 0, 0, True),
        (1, 100, 200, True),
        (2, 200, 400, True)
    ]
    
    # Get pool state
    state = await pool_manager.get_pool(weth, usdc, FeeTier.MEDIUM)
    
    # Get observations
    observations = await pool_manager.get_observations(state, 2)
    
    # Verify observations
    assert len(observations) == 2
    assert observations[-1].tick_cumulative == 200
    assert observations[-1].seconds_per_liquidity_cumulative == 400