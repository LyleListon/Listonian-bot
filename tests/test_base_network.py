"""Tests for Base network integration and parallel processing."""

import asyncio
import pytest
import time
from typing import Dict, Any

from arbitrage_bot.core import (
    BaseArbitrageSystem,
    ArbitrageOpportunity,
    ExecutionResult,
    OpportunityStatus,
    ExecutionStatus
)
from .test_arbitrage_system import (
    MockDiscoveryManager,
    MockExecutionManager,
    MockAnalyticsManager,
    MockMarketDataProvider
)

BASE_CONFIG = {
    "arbitrage": {
        "provider_url": "${BASE_RPC_URL}",
        "chain_id": 8453,
        "tokens": {
            "WETH": {
                "address": "0x4200000000000000000000000000000000000006",
                "decimals": 18,
                "min_amount": "0.01"
            },
            "USDbC": {
                "address": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA",
                "decimals": 6,
                "min_amount": "10"
            }
        },
        "auto_execute": False,
        "min_profit_threshold_eth": 0.01,
        "max_opportunities_per_cycle": 5,
        "discovery_interval_seconds": 30.0,
        "execution_interval_seconds": 60.0,
        "min_confidence_threshold": 0.7,
        "max_slippage_percent": 0.5,
        "max_gas_price_gwei": 50.0
    }
}

@pytest.mark.asyncio
async def test_base_token_addresses():
    """Test Base network token addresses are checksummed."""
    system = BaseArbitrageSystem(
        discovery_manager=MockDiscoveryManager(BASE_CONFIG),
        execution_manager=MockExecutionManager(BASE_CONFIG),
        analytics_manager=MockAnalyticsManager(BASE_CONFIG),
        market_data_provider=MockMarketDataProvider(BASE_CONFIG),
        config=BASE_CONFIG
    )
    
    try:
        await system.start()
        
        # Get opportunities
        opportunities = await system.discover_opportunities(max_results=1)
        assert len(opportunities) > 0
        
        # Verify WETH address
        opp = opportunities[0]
        assert opp.route.input_token_address == "0x4200000000000000000000000000000000000006"
        
        # Verify USDbC address
        assert opp.route.steps[0].output_token_address == "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA"
        
    finally:
        await system.stop()

@pytest.mark.asyncio
async def test_parallel_opportunity_detection():
    """Test parallel processing of opportunities."""
    # Create config with many tokens
    config = {
        "arbitrage": {
            **BASE_CONFIG["arbitrage"],
            "tokens": {
                f"TOKEN{i}": {
                    "address": f"0x{i:040x}",
                    "decimals": 18,
                    "min_amount": "0.01"
                } for i in range(20)  # 20 tokens for testing parallel processing
            }
        }
    }
    
    system = BaseArbitrageSystem(
        discovery_manager=MockDiscoveryManager(config),
        execution_manager=MockExecutionManager(config),
        analytics_manager=MockAnalyticsManager(config),
        market_data_provider=MockMarketDataProvider(config),
        config=config
    )
    
    try:
        await system.start()
        
        # Measure sequential processing time
        start_time = time.time()
        sequential_opps = []
        for i in range(20):
            opps = await system.discover_opportunities(max_results=1)
            sequential_opps.extend(opps)
        sequential_time = time.time() - start_time
        
        # Measure parallel processing time
        start_time = time.time()
        parallel_opps = await system.discover_opportunities(max_results=20)
        parallel_time = time.time() - start_time
        
        # Verify parallel is faster
        assert parallel_time < sequential_time
        assert len(parallel_opps) == len(sequential_opps)
        
    finally:
        await system.stop()

@pytest.mark.asyncio
async def test_concurrent_operations():
    """Test concurrent operations are thread-safe."""
    system = BaseArbitrageSystem(
        discovery_manager=MockDiscoveryManager(BASE_CONFIG),
        execution_manager=MockExecutionManager(BASE_CONFIG),
        analytics_manager=MockAnalyticsManager(BASE_CONFIG),
        market_data_provider=MockMarketDataProvider(BASE_CONFIG),
        config=BASE_CONFIG
    )
    
    try:
        await system.start()
        
        # Run multiple operations concurrently
        async def run_operations():
            tasks = [
                system.discover_opportunities(max_results=3),
                system.get_performance_metrics(),
                system.get_recent_opportunities(max_results=5),
                system.get_recent_executions(max_results=5)
            ]
            return await asyncio.gather(*tasks)
        
        # Run multiple times to stress test
        results = []
        for _ in range(5):
            batch_results = await run_operations()
            results.append(batch_results)
        
        # Verify all operations completed successfully
        for batch in results:
            assert len(batch) == 4  # 4 operations per batch
            assert isinstance(batch[0], list)  # opportunities
            assert isinstance(batch[1], dict)  # metrics
            assert isinstance(batch[2], list)  # recent opportunities
            assert isinstance(batch[3], list)  # recent executions
        
    finally:
        await system.stop()

@pytest.mark.asyncio
async def test_resource_cleanup():
    """Test proper cleanup of resources."""
    system = BaseArbitrageSystem(
        discovery_manager=MockDiscoveryManager(BASE_CONFIG),
        execution_manager=MockExecutionManager(BASE_CONFIG),
        analytics_manager=MockAnalyticsManager(BASE_CONFIG),
        market_data_provider=MockMarketDataProvider(BASE_CONFIG),
        config=BASE_CONFIG
    )
    
    # Test start-stop cycle
    await system.start()
    assert system.is_running
    await system.stop()
    assert not system.is_running
    
    # Test multiple start-stop cycles
    for _ in range(3):
        await system.start()
        assert system.is_running
        
        # Run some operations
        await system.discover_opportunities(max_results=3)
        await system.get_performance_metrics()
        
        await system.stop()
        assert not system.is_running
        
        # Verify market data provider is cleaned up
        assert not system.market_data_provider._monitoring
        assert system.market_data_provider._update_task is None

if __name__ == "__main__":
    """Run tests directly."""
    asyncio.run(test_base_token_addresses())
    asyncio.run(test_parallel_opportunity_detection())
    asyncio.run(test_concurrent_operations())
    asyncio.run(test_resource_cleanup())
    print("All Base network tests passed!")