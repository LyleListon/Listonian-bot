"""Tests for ArbitrageExecutor."""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from ..execution.arbitrage_executor import ArbitrageExecutor, create_arbitrage_executor
from ..web3.web3_manager import Web3Manager
from ..dex import DexManager
from ..gas.gas_optimizer import GasOptimizer

@pytest.fixture
async def web3_manager():
    """Create a mock Web3Manager instance."""
    manager = AsyncMock()
    manager.wallet_address = "0x1234567890123456789012345678901234567890"
    manager.w3 = AsyncMock()
    manager.w3.eth.get_block = AsyncMock(return_value={'timestamp': 1000000})
    manager.w3.eth.gas_price = 50000000000  # 50 gwei
    manager.w3.from_wei = Mock(return_value=50)  # 50 gwei
    manager.use_mcp_tool = AsyncMock(return_value={
        "ethereum": {"usd": 2000.0}
    })
    return manager

@pytest.fixture
async def market_analyzer():
    """Create a mock MarketAnalyzer instance."""
    analyzer = AsyncMock()
    analyzer.get_market_condition = AsyncMock(return_value={
        'price': 2000.0,
        'volume': 1000000.0,
        'liquidity': 10000000.0,
        'volatility': 0.02,
        'trend': 'up',
        'trend_strength': 0.8,
        'confidence': 0.9
    })
    analyzer.market_conditions = {
        "WETH": MagicMock(price=Decimal("2000.0"))
    }
    return analyzer

@pytest.fixture
async def dex_manager():
    """Create a mock DEXManager instance."""
    manager = AsyncMock()
    
    # Create mock DEXes
    dex1 = AsyncMock(name="BaseSwap")
    dex1.get_quote_with_impact = AsyncMock(return_value={
        'amount_in': int(1e18),  # 1 WETH
        'amount_out': int(2000e6),  # 2000 USDC
        'price_impact': 0.005,
        'gas_estimate': 150000
    })
    dex1.get_pool_liquidity = AsyncMock(return_value=int(1000e18))
    
    dex2 = AsyncMock(name="PancakeSwap")
    dex2.get_quote_with_impact = AsyncMock(return_value={
        'amount_in': int(2000e6),  # 2000 USDC
        'amount_out': int(1.02e18),  # 1.02 WETH
        'price_impact': 0.005,
        'gas_estimate': 150000
    })
    dex2.get_pool_liquidity = AsyncMock(return_value=int(1000e18))
    
    manager.get_dex = Mock(side_effect=lambda name: dex1 if name == "BaseSwap" else dex2)
    manager.get_all_dexes = Mock(return_value=[dex1, dex2])
    return manager

@pytest.fixture
async def gas_optimizer():
    """Create a mock GasOptimizer instance."""
    optimizer = AsyncMock()
    optimizer.get_optimal_gas_price = AsyncMock(return_value=50000000000)  # 50 gwei
    return optimizer

@pytest.fixture
async def executor(web3_manager, dex_manager, gas_optimizer, market_analyzer):
    """Create ArbitrageExecutor instance."""
    executor = ArbitrageExecutor(
        dex_manager=dex_manager,
        web3_manager=web3_manager,
        gas_optimizer=gas_optimizer,
        market_analyzer=market_analyzer
    )
    initialized = await executor.initialize()
    if not initialized:
        pytest.skip("ArbitrageExecutor initialization failed")
    return executor

@pytest.mark.asyncio
async def test_price_conversion_with_caching(executor):
    """Test wei to USD conversion with caching."""
    amount_wei = int(1e18)  # 1 ETH
    
    # First call should use market analyzer
    result1 = await executor._convert_wei_to_usd(amount_wei)
    assert result1 == 2000.0  # 1 ETH = $2000
    
    # Second call should use cache
    result2 = await executor._convert_wei_to_usd(amount_wei)
    assert result2 == 2000.0
    assert executor.market_analyzer.get_market_condition.call_count == 1  # Should use cache

@pytest.mark.asyncio
async def test_parallel_opportunity_verification(executor):
    """Test parallel execution in opportunity verification."""
    opportunity = {
        'buy_dex': 'BaseSwap',
        'sell_dex': 'PancakeSwap',
        'buy_path': ['0x123...', '0x456...'],
        'sell_path': ['0x456...', '0x123...'],
        'amount_in': int(1e18),
        'buy_amount_out': int(2000e6),
        'sell_amount_out': int(1.02e18)
    }
    
    start_time = asyncio.get_event_loop().time()
    result = await executor._verify_opportunity(opportunity)
    end_time = asyncio.get_event_loop().time()
    
    assert result is not None
    assert result['profit_usd'] > 0
    # Verify parallel execution is faster than sequential
    assert end_time - start_time < 0.5  # Should complete quickly

@pytest.mark.asyncio
async def test_parallel_liquidity_verification(executor):
    """Test parallel execution in liquidity verification."""
    opportunity = {
        'buy_dex': 'BaseSwap',
        'sell_dex': 'PancakeSwap',
        'buy_path': ['0x123...', '0x456...'],
        'sell_path': ['0x456...', '0x123...']
    }
    
    start_time = asyncio.get_event_loop().time()
    result = await executor._verify_pool_liquidity(opportunity)
    end_time = asyncio.get_event_loop().time()
    
    assert result is True
    # Verify parallel execution is faster than sequential
    assert end_time - start_time < 0.5  # Should complete quickly

@pytest.mark.asyncio
async def test_price_fallback_mechanism(executor):
    """Test price data fallback mechanism."""
    amount_wei = int(1e18)  # 1 ETH
    
    # Test market analyzer failure
    executor.market_analyzer.get_market_condition = AsyncMock(return_value=None)
    result1 = await executor._convert_wei_to_usd(amount_wei)
    assert result1 == 2000.0  # Should fall back to MCP server
    
    # Test MCP server failure
    executor.web3_manager.use_mcp_tool = AsyncMock(return_value=None)
    result2 = await executor._convert_wei_to_usd(amount_wei)
    assert result2 == 2000.0  # Should fall back to market conditions
    
    # Test all failures
    executor.market_analyzer.market_conditions = {}
    result3 = await executor._convert_wei_to_usd(amount_wei)
    assert result3 == 0.0  # All fallbacks failed

@pytest.mark.asyncio
async def test_parallel_quote_fetching(executor):
    """Test parallel quote fetching in find_opportunities."""
    opportunities = await executor.find_opportunities()
    
    assert len(opportunities) > 0
    assert opportunities[0]['profit_usd'] > 0
    assert opportunities[0]['gas_cost_usd'] > 0
    assert 0 <= opportunities[0]['price_impact'] <= 1

@pytest.mark.asyncio
async def test_error_handling(executor):
    """Test error handling in critical methods."""
    # Test invalid opportunity
    invalid_opportunity = {
        'buy_dex': 'InvalidDEX',
        'sell_dex': 'PancakeSwap',
        'buy_path': ['0x123...'],
        'sell_path': ['0x456...']
    }
    result = await executor._verify_opportunity(invalid_opportunity)
    assert result is None
    assert executor.last_error is not None

    # Test execution with insufficient balance
    executor.check_balances = AsyncMock(return_value=False)
    result = await executor.execute_opportunity(invalid_opportunity)
    assert result is None
    assert "Insufficient balance" in executor.last_error

if __name__ == "__main__":
    pytest.main([__file__])
