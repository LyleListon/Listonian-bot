"""
Test SwapBased V3 integration.

This module tests:
1. Token symbol parsing
2. Pool data retrieval
3. Error handling
4. Edge cases
"""

import pytest
import asyncio
import logging
from typing import Dict, Any
from decimal import Decimal
from web3 import Web3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test fixtures
@pytest.fixture
async def swapbased_pool_contract():
    """Mock SwapBased V3 pool contract."""
    class MockContract:
        async def functions(self):
            return self
        
        async def currentState(self):
            return self
        
        async def call(self):
            return [
                "1234567890",  # sqrtPriceX96
                12345,         # tick
                "1000000"      # liquidity
            ]
    
    return MockContract()

@pytest.fixture
async def token_addresses():
    """Sample token addresses."""
    return {
        'WETH': '0x4200000000000000000000000000000000000006',
        'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
    }

# Test cases
@pytest.mark.asyncio
async def test_token_symbol_parsing():
    """Test case-insensitive token symbol parsing."""
    from arbitrage_bot.core.dex import get_token_symbol
    
    addresses = {
        'WETH': '0x4200000000000000000000000000000000000006',
        'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
    }
    
    # Test with checksummed address
    symbol = get_token_symbol(addresses['WETH'], addresses)
    assert symbol == 'WETH', "Failed to match checksummed address"
    
    # Test with lowercase address
    symbol = get_token_symbol(addresses['WETH'].lower(), addresses)
    assert symbol == 'WETH', "Failed to match lowercase address"
    
    # Test with unknown address
    symbol = get_token_symbol('0x0000000000000000000000000000000000000000', addresses)
    assert symbol == '', "Should return empty string for unknown address"

@pytest.mark.asyncio
async def test_pool_data_retrieval(swapbased_pool_contract):
    """Test SwapBased V3 pool data retrieval."""
    from arbitrage_bot.core.dex import get_pool_data
    
    data = await get_pool_data(swapbased_pool_contract, 'swapbased')
    
    assert 'sqrtPriceX96' in data, "Missing sqrtPriceX96"
    assert 'tick' in data, "Missing tick"
    assert 'liquidity' in data, "Missing liquidity"
    assert isinstance(data['tick'], int), "Tick should be integer"
    assert isinstance(data['liquidity'], str), "Liquidity should be string"

@pytest.mark.asyncio
async def test_pool_key_generation(token_addresses):
    """Test pool key generation with SwapBased V3."""
    from arbitrage_bot.core.dex import generate_pool_key
    
    pool_address = "0x0000000000000000000000000000000000000010"
    token0 = token_addresses['WETH']
    token1 = token_addresses['USDC']
    
    key = generate_pool_key('swapbased', pool_address, token0, token1)
    assert 'swapbased' in key.lower(), "DEX name not in pool key"
    assert 'weth' in key.lower(), "Token0 symbol not in pool key"
    assert 'usdc' in key.lower(), "Token1 symbol not in pool key"

@pytest.mark.asyncio
async def test_error_handling(swapbased_pool_contract):
    """Test error handling for SwapBased V3 operations."""
    from arbitrage_bot.core.dex import get_pool_data
    
    # Test with invalid contract
    with pytest.raises(Exception) as exc_info:
        await get_pool_data(None, 'swapbased')
    assert "Invalid contract" in str(exc_info.value)
    
    # Test with invalid DEX name
    with pytest.raises(ValueError) as exc_info:
        await get_pool_data(swapbased_pool_contract, 'unknown_dex')
    assert "Unsupported DEX" in str(exc_info.value)

@pytest.mark.asyncio
async def test_price_calculation():
    """Test price calculation with SwapBased V3 data."""
    from arbitrage_bot.core.dex import calculate_price
    
    pool_data = {
        'sqrtPriceX96': "1234567890",
        'tick': 12345,
        'liquidity': "1000000"
    }
    
    decimals0 = 18  # WETH
    decimals1 = 6   # USDC
    
    price = calculate_price(pool_data, decimals0, decimals1)
    assert isinstance(price, Decimal), "Price should be Decimal"
    assert price > 0, "Price should be positive"

@pytest.mark.asyncio
async def test_liquidity_validation():
    """Test liquidity validation for SwapBased V3."""
    from arbitrage_bot.core.dex import validate_liquidity
    
    pool_data = {
        'sqrtPriceX96': "1234567890",
        'tick': 12345,
        'liquidity': "1000000"
    }
    
    # Test with sufficient liquidity
    assert validate_liquidity(pool_data, Decimal('1.0')), "Should accept valid liquidity"
    
    # Test with insufficient liquidity
    assert not validate_liquidity(pool_data, Decimal('1000000.0')), "Should reject insufficient liquidity"

@pytest.mark.asyncio
async def test_edge_cases(swapbased_pool_contract):
    """Test edge cases in SwapBased V3 integration."""
    from arbitrage_bot.core.dex import get_pool_data
    
    # Test with zero liquidity
    class ZeroLiquidityContract:
        async def functions(self):
            return self
        
        async def currentState(self):
            return self
        
        async def call(self):
            return [
                "1234567890",  # sqrtPriceX96
                12345,         # tick
                "0"           # liquidity
            ]
    
    data = await get_pool_data(ZeroLiquidityContract(), 'swapbased')
    assert data['liquidity'] == "0", "Should handle zero liquidity"
    
    # Test with extreme tick values
    class ExtremeTick:
        async def functions(self):
            return self
        
        async def currentState(self):
            return self
        
        async def call(self):
            return [
                "1234567890",
                887272,  # max tick
                "1000000"
            ]
    
    data = await get_pool_data(ExtremeTick(), 'swapbased')
    assert data['tick'] == 887272, "Should handle extreme tick values"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])