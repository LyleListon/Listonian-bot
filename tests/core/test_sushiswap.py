"""Tests for Sushiswap DEX implementation."""

import pytest
from decimal import Decimal
from web3 import Web3

from arbitrage_bot.core.dex import SushiswapDEX

@pytest.fixture
async def sushiswap_dex(web3_manager, sushiswap_config):
    """Create SushiswapDEX instance."""
    dex = SushiswapDEX(web3_manager, sushiswap_config)
    await dex.initialize()
    return dex

@pytest.mark.asyncio
async def test_initialization(sushiswap_dex):
    """Test DEX initialization."""
    assert sushiswap_dex.initialized
    assert sushiswap_dex.name == "Sushiswap"
    assert sushiswap_dex.fee == 3000
    assert sushiswap_dex.router is not None
    assert sushiswap_dex.factory is not None

@pytest.mark.asyncio
async def test_get_quote_with_impact(sushiswap_dex, weth_address, usdc_address):
    """Test quote calculation with price impact."""
    # Get quote for 1 WETH
    amount_in = Web3.to_wei(1, 'ether')
    path = [weth_address, usdc_address]
    
    quote = await sushiswap_dex.get_quote_with_impact(amount_in, path)
    
    assert quote is not None
    assert 'amount_in' in quote
    assert 'amount_out' in quote
    assert 'price_impact' in quote
    assert 'liquidity_depth' in quote
    assert quote['amount_in'] == amount_in
    assert quote['amount_out'] > 0
    assert 0 <= quote['price_impact'] <= 1
    assert quote['liquidity_depth'] > 0

@pytest.mark.asyncio
async def test_get_token_price(sushiswap_dex, usdc_address):
    """Test token price calculation."""
    price = await sushiswap_dex.get_token_price(usdc_address)
    
    assert price > 0
    assert isinstance(price, float)

@pytest.mark.asyncio
async def test_error_handling(sushiswap_dex, weth_address):
    """Test error handling."""
    # Test with invalid token address
    invalid_token = "0x0000000000000000000000000000000000000000"
    
    # Should handle invalid path gracefully
    quote = await sushiswap_dex.get_quote_with_impact(
        Web3.to_wei(1, 'ether'),
        [invalid_token, weth_address]
    )
    assert quote is None
    
    # Should handle invalid token price gracefully
    price = await sushiswap_dex.get_token_price(invalid_token)
    assert price == 0.0

@pytest.mark.asyncio
async def test_get_24h_volume(sushiswap_dex, weth_address, usdc_address):
    """Test 24h volume calculation."""
    volume = await sushiswap_dex.get_24h_volume(weth_address, usdc_address)
    
    assert isinstance(volume, Decimal)
    assert volume >= 0