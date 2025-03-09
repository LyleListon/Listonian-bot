"""Stress tests for arbitrage system."""

import asyncio
import pytest
import time
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor

from arbitrage_bot.core import (
    BaseArbitrageSystem,
    ArbitrageOpportunity,
    ExecutionResult,
    OpportunityStatus,
    ExecutionStatus,
    TransactionStatus
)

from .mocks import (
    MockDiscoveryManager,
    MockExecutionManager,
    MockAnalyticsManager,
    MockMarketDataProvider
)

STRESS_CONFIG = {
    "arbitrage": {
        "provider_url": "${BASE_RPC_URL}",
        "chain_id": 8453,
        "tokens": {
            "WETH": {
                "address": "0x4200000000000000000000000000000006",
                "decimals": 18,
                "min_amount": "0.01"
            }
        },
        "flashbots": {
            "enabled": True,
            "relay_url": "https://relay-base.flashbots.net",
            "auth_signer_key": "${FLASHBOTS_AUTH_KEY}",
            "max_bundle_size": 5,
            "max_blocks_ahead": 3,
            "min_priority_fee": "1.5",
            "max_priority_fee": "3",
            "sandwich_detection": True,
            "frontrun_detection": True,
            "adaptive_gas": True
        }
    }
}

@pytest.mark.asyncio
async def test_concurrent_opportunity_discovery():
    """Test system under heavy concurrent opportunity discovery."""
    system = BaseArbitrageSystem(
        discovery_manager=MockDiscoveryManager(STRESS_CONFIG),
        execution_manager=MockExecutionManager(STRESS_CONFIG),
        analytics_manager=MockAnalyticsManager(STRESS_CONFIG),
        market_data_provider=MockMarketDataProvider(STRESS_CONFIG),
        config=STRESS_CONFIG
    )
    
    try:
        await system.start()
        
        # Run multiple discoveries concurrently
        async def discover_batch():
            return await system.discover_opportunities(max_results=10)
        
        # Run 50 concurrent discoveries
        tasks = [discover_batch() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        assert len(results) == 50
        for opportunities in results:
            assert len(opportunities) == 10
            for opp in opportunities:
                assert isinstance(opp, ArbitrageOpportunity)
                assert opp.status == OpportunityStatus.READY
        
    finally:
        await system.stop()

@pytest.mark.asyncio
async def test_concurrent_executions():
    """Test system under heavy concurrent executions."""
    system = BaseArbitrageSystem(
        discovery_manager=MockDiscoveryManager(STRESS_CONFIG),
        execution_manager=MockExecutionManager(STRESS_CONFIG),
        analytics_manager=MockAnalyticsManager(STRESS_CONFIG),
        market_data_provider=MockMarketDataProvider(STRESS_CONFIG),
        config=STRESS_CONFIG
    )
    
    try:
        await system.start()
        
        # Get opportunities
        opportunities = await system.discover_opportunities(max_results=20)
        assert len(opportunities) == 20
        
        # Execute all opportunities concurrently
        start_time = time.time()
        results = await asyncio.gather(*[
            system.execute_opportunity(opp, strategy_id="flashbots")
            for opp in opportunities
        ])
        execution_time = time.time() - start_time
        
        # Verify results
        assert len(results) == 20
        for result in results:
            assert isinstance(result, ExecutionResult)
            assert result.status == ExecutionStatus.SUCCESS
            assert result.transaction_details.status == TransactionStatus.CONFIRMED
        
        # Verify execution time is reasonable (should be much less than sequential)
        assert execution_time < len(opportunities) * 0.5  # 500ms per execution max
        
    finally:
        await system.stop()

@pytest.mark.asyncio
async def test_system_under_load():
    """Test system under heavy load with mixed operations."""
    system = BaseArbitrageSystem(
        discovery_manager=MockDiscoveryManager(STRESS_CONFIG),
        execution_manager=MockExecutionManager(STRESS_CONFIG),
        analytics_manager=MockAnalyticsManager(STRESS_CONFIG),
        market_data_provider=MockMarketDataProvider(STRESS_CONFIG),
        config=STRESS_CONFIG
    )
    
    try:
        await system.start()
        
        async def run_mixed_operations():
            # Discover opportunities
            opportunities = await system.discover_opportunities(max_results=5)
            
            # Execute some opportunities
            executions = await asyncio.gather(*[
                system.execute_opportunity(opp, strategy_id="flashbots")
                for opp in opportunities[:2]  # Execute first 2
            ])
            
            # Get metrics
            metrics = await system.get_performance_metrics()
            
            # Get recent data
            recent_opps = await system.get_recent_opportunities()
            recent_execs = await system.get_recent_executions()
            
            return {
                "opportunities": opportunities,
                "executions": executions,
                "metrics": metrics,
                "recent_opps": recent_opps,
                "recent_execs": recent_execs
            }
        
        # Run multiple operation sets concurrently
        tasks = [run_mixed_operations() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify results
        for result in results:
            assert len(result["opportunities"]) == 5
            assert len(result["executions"]) == 2
            assert isinstance(result["metrics"], dict)
            assert isinstance(result["recent_opps"], list)
            assert isinstance(result["recent_execs"], list)
        
    finally:
        await system.stop()

@pytest.mark.asyncio
async def test_resource_management_under_stress():
    """Test resource management under stress."""
    systems: List[BaseArbitrageSystem] = []
    
    try:
        # Create and start multiple systems
        for _ in range(5):
            system = BaseArbitrageSystem(
                discovery_manager=MockDiscoveryManager(STRESS_CONFIG),
                execution_manager=MockExecutionManager(STRESS_CONFIG),
                analytics_manager=MockAnalyticsManager(STRESS_CONFIG),
                market_data_provider=MockMarketDataProvider(STRESS_CONFIG),
                config=STRESS_CONFIG
            )
            await system.start()
            systems.append(system)
        
        # Run operations on all systems concurrently
        async def run_system_operations(system: BaseArbitrageSystem):
            opportunities = await system.discover_opportunities(max_results=5)
            await asyncio.gather(*[
                system.execute_opportunity(opp, strategy_id="flashbots")
                for opp in opportunities
            ])
            await system.get_performance_metrics()
        
        # Run operations on all systems
        await asyncio.gather(*[
            run_system_operations(system)
            for system in systems
        ])
        
    finally:
        # Stop all systems
        await asyncio.gather(*[
            system.stop()
            for system in systems
        ])
        
        # Verify all systems stopped
        assert all(not system.is_running for system in systems)
        
        # Verify all market data providers cleaned up
        assert all(
            not system.market_data_provider._monitoring
            for system in systems
        )
        assert all(
            system.market_data_provider._update_task is None
            for system in systems
        )

if __name__ == "__main__":
    """Run tests directly."""
    asyncio.run(test_concurrent_opportunity_discovery())
    asyncio.run(test_concurrent_executions())
    asyncio.run(test_system_under_load())
    asyncio.run(test_resource_management_under_stress())
    print("All stress tests passed!")