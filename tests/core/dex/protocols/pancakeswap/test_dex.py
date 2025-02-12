"""Tests for PancakeSwap V3 DEX implementation."""

import asyncio
import pytest
from decimal import Decimal
import time

from src.core.dex.interfaces.types import (
    SwapParams,
    TokenAmount,
)
from src.core.dex.protocols.pancakeswap import (
    PancakeSwapV3,
    FeeTier,
)

from .fixtures.data import (
    ADDRESSES,
    AMOUNTS,
    TOKENS,
)


async def test_initialization(web3):
    """Test DEX initialization."""
    # Initialize with default addresses
    dex = PancakeSwapV3(web3)
    assert dex.factory_address == ADDRESSES['factory']
    assert dex.router_address == ADDRESSES['router']
    
    # Initialize with custom addresses
    dex = PancakeSwapV3(
        web3,
        factory_address="0x1234",
        router_address="0x5678"
    )
    assert dex.factory_address == "0x1234"
    assert dex.router_address == "0x5678"


async def test_get_pool(dex, weth_usdc_pool):
    """Test getting pool information."""
    # Get pool
    pool = await dex.get_pool(TOKENS['WETH'], TOKENS['USDC'])
    
    # Verify pool
    assert pool is not None
    assert pool.token0 == TOKENS['WETH']
    assert pool.token1 == TOKENS['USDC']
    assert pool.fee == Decimal('0.003')  # 0.3%
    assert pool.liquidity.token0_reserve.amount > 0
    assert pool.liquidity.token1_reserve.amount > 0


async def test_get_quote(dex, weth_usdc_pool):
    """Test getting swap quote."""
    # Get quote
    quote = await dex.get_quote(
        AMOUNTS['WETH_1'],
        TOKENS['USDC']
    )
    
    # Verify quote
    assert quote.input_amount == AMOUNTS['WETH_1']
    assert quote.output_amount.token == TOKENS['USDC']
    assert quote.output_amount.amount > 0
    assert quote.price_impact >= 0
    assert quote.gas_estimate > 0


async def test_get_price(dex, weth_usdc_pool):
    """Test getting current price."""
    # Get price
    price = await dex.get_price(TOKENS['WETH'], TOKENS['USDC'])
    
    # Verify price
    assert price > 0
    assert isinstance(price, Decimal)


async def test_execute_swap(dex, weth_usdc_pool):
    """Test executing swap."""
    # Get quote
    quote = await dex.get_quote(
        AMOUNTS['WETH_1'],
        TOKENS['USDC']
    )
    
    # Create swap parameters
    params = SwapParams(
        quote=quote,
        slippage=Decimal('0.005'),  # 0.5%
        deadline=int(time.time() + 60),
        recipient=dex.web3.provider.web3.eth.default_account
    )
    
    # Execute swap
    tx_hash = await dex.execute_swap(params)
    
    # Verify transaction hash
    assert isinstance(tx_hash, str)
    assert len(tx_hash) == 66  # '0x' + 64 hex chars


async def test_find_best_path(dex, weth_usdc_pool, usdc_dai_pool):
    """Test finding best swap path."""
    # Find path
    path, expected = await dex.find_best_path(
        TOKENS['WETH'],
        TOKENS['DAI'],
        AMOUNTS['WETH_1']
    )
    
    # Verify path
    assert len(path) == 3  # WETH -> USDC -> DAI
    assert path[0] == TOKENS['WETH'].address
    assert path[1] == TOKENS['USDC'].address
    assert path[2] == TOKENS['DAI'].address
    assert expected > 0


async def test_validate_pool(dex, weth_usdc_pool):
    """Test pool validation."""
    # Get pool
    pool = await dex.get_pool(TOKENS['WETH'], TOKENS['USDC'])
    
    # Validate pool
    is_valid = await dex.validate_pool(pool)
    assert is_valid is True


async def test_monitor_price(dex, weth_usdc_pool, mock_price_update):
    """Test price monitoring."""
    price_updates = []
    
    async def on_price_update(old_price: Decimal, new_price: Decimal):
        price_updates.append((old_price, new_price))
    
    # Start monitoring
    pool = await dex.get_pool(TOKENS['WETH'], TOKENS['USDC'])
    await dex.monitor_price(pool.address, on_price_update)
    
    # Simulate price update
    mock_price_update(
        weth_usdc_pool,
        int(2 ** 96 * 1.1),  # 10% price increase
        100  # New tick
    )
    
    # Wait for update
    await asyncio.sleep(0.1)
    
    # Verify update received
    assert len(price_updates) == 1
    assert price_updates[0][1] > price_updates[0][0]


async def test_error_handling(dex):
    """Test error handling."""
    # Test non-existent pool
    with pytest.raises(ValueError, match="Pool does not exist"):
        await dex.get_quote(
            AMOUNTS['WETH_1'],
            TokenAmount(
                token=TOKENS['DAI'],
                amount=Decimal('1000.0')
            )
        )
    
    # Test insufficient liquidity
    with pytest.raises(ValueError, match="Insufficient liquidity"):
        await dex.get_quote(
            TokenAmount(
                token=TOKENS['WETH'],
                amount=Decimal('1000000.0')  # Very large amount
            ),
            TOKENS['USDC']
        )
    
    # Test invalid slippage
    quote = await dex.get_quote(AMOUNTS['WETH_1'], TOKENS['USDC'])
    with pytest.raises(ValueError, match="Invalid slippage"):
        SwapParams(
            quote=quote,
            slippage=Decimal('1.0'),  # 100% slippage
            deadline=int(time.time() + 60),
            recipient=dex.web3.provider.web3.eth.default_account
        )