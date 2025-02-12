"""Tests for memory bank functionality."""

import pytest
import asyncio
import time
from typing import Dict, Any
from dataclasses import dataclass

from arbitrage_bot.core.memory.bank import MemoryBank, create_memory_bank
from arbitrage_bot.core.models.opportunity import Opportunity

@dataclass
class MockOpportunity(Opportunity):
    """Mock opportunity for testing."""
    buy_dex: str = "dex1"
    sell_dex: str = "dex2"
    token_pair: str = "TOKEN1/TOKEN2"
    profit_percent: float = 0.01
    buy_amount: float = 1000.0
    sell_amount: float = 1010.0
    estimated_gas: float = 50.0
    net_profit: float = 10.0
    priority: float = 0.8
    route_type: str = "direct"
    confidence_score: float = 0.9

@pytest.fixture
async def memory_bank():
    """Create memory bank instance for testing."""
    config = {
        "max_opportunities": 5,
        "cleanup_interval": 1,  # 1 second for testing
        "max_age": 2  # 2 seconds for testing
    }
    bank = await create_memory_bank(config)
    yield bank
    await bank.cleanup()

@pytest.mark.asyncio
async def test_initialization():
    """Test memory bank initialization."""
    # Test with empty config
    bank = MemoryBank()
    assert await bank.initialize({})
    assert bank.initialized
    assert bank.config["max_opportunities"] == 1000  # Default value
    await bank.cleanup()
    
    # Test with custom config
    config = {"max_opportunities": 500}
    bank = MemoryBank()
    assert await bank.initialize(config)
    assert bank.initialized
    assert bank.config["max_opportunities"] == 500
    await bank.cleanup()

@pytest.mark.asyncio
async def test_store_opportunities(memory_bank):
    """Test storing opportunities."""
    opportunities = [MockOpportunity() for _ in range(3)]
    await memory_bank.store_opportunities(opportunities)
    assert len(memory_bank.opportunities) == 3
    
    # Test max size limit
    more_opportunities = [MockOpportunity() for _ in range(3)]
    await memory_bank.store_opportunities(more_opportunities)
    assert len(memory_bank.opportunities) == 5  # Limited by config max_opportunities

@pytest.mark.asyncio
async def test_store_trade_result(memory_bank):
    """Test storing trade results."""
    opportunity = MockOpportunity()
    await memory_bank.store_trade_result(
        opportunity=opportunity.__dict__,
        success=True,
        net_profit=10.0,
        gas_cost=2.0,
        tx_hash="0x123"
    )
    assert len(memory_bank.trade_results) == 1
    result = memory_bank.trade_results[0]
    assert result["success"]
    assert result["net_profit"] == 10.0
    assert result["gas_cost"] == 2.0
    assert result["tx_hash"] == "0x123"

@pytest.mark.asyncio
async def test_get_recent_opportunities(memory_bank):
    """Test retrieving recent opportunities."""
    # Store some opportunities
    opportunities = [MockOpportunity() for _ in range(3)]
    await memory_bank.store_opportunities(opportunities)
    
    # Get recent opportunities
    recent = await memory_bank.get_recent_opportunities()
    assert len(recent) == 3
    
    # Test max age filter
    await asyncio.sleep(2.1)  # Wait for opportunities to expire
    recent = await memory_bank.get_recent_opportunities()
    assert len(recent) == 0

@pytest.mark.asyncio
async def test_get_trade_history(memory_bank):
    """Test retrieving trade history."""
    # Store some trade results
    opportunity = MockOpportunity()
    await memory_bank.store_trade_result(
        opportunity=opportunity.__dict__,
        success=True,
        net_profit=10.0
    )
    await memory_bank.store_trade_result(
        opportunity=opportunity.__dict__,
        success=False,
        error="Test error"
    )
    
    # Get all trades
    history = await memory_bank.get_trade_history()
    assert len(history) == 2
    
    # Get only successful trades
    successful = await memory_bank.get_trade_history(success_only=True)
    assert len(successful) == 1
    assert successful[0]["success"]

@pytest.mark.asyncio
async def test_get_statistics(memory_bank):
    """Test retrieving statistics."""
    # Store some opportunities and trades
    opportunities = [MockOpportunity() for _ in range(3)]
    await memory_bank.store_opportunities(opportunities)
    
    opportunity = MockOpportunity()
    await memory_bank.store_trade_result(
        opportunity=opportunity.__dict__,
        success=True,
        net_profit=10.0,
        gas_cost=2.0
    )
    await memory_bank.store_trade_result(
        opportunity=opportunity.__dict__,
        success=True,
        net_profit=15.0,
        gas_cost=3.0
    )
    await memory_bank.store_trade_result(
        opportunity=opportunity.__dict__,
        success=False,
        error="Test error"
    )
    
    # Get statistics
    stats = await memory_bank.get_statistics()
    assert stats["opportunities_count"] == 3
    assert stats["trades_count"] == 3
    assert stats["successful_trades"] == 2
    assert stats["total_profit"] == 25.0
    assert stats["total_gas_cost"] == 5.0
    assert stats["success_rate"] == 2/3
    assert stats["average_profit"] == 12.5

@pytest.mark.asyncio
async def test_cleanup_loop(memory_bank):
    """Test automatic cleanup of old data."""
    # Store some data
    opportunities = [MockOpportunity() for _ in range(3)]
    await memory_bank.store_opportunities(opportunities)
    
    opportunity = MockOpportunity()
    await memory_bank.store_trade_result(
        opportunity=opportunity.__dict__,
        success=True,
        net_profit=10.0
    )
    
    # Verify initial state
    assert len(memory_bank.opportunities) == 3
    assert len(memory_bank.trade_results) == 1
    
    # Wait for cleanup
    await asyncio.sleep(2.1)  # Wait for data to expire
    
    # Verify cleanup occurred
    assert len(memory_bank.opportunities) == 0
    assert len(memory_bank.trade_results) == 0

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in memory bank operations."""
    # Test initialization with invalid config
    bank = MemoryBank()
    config = {"max_opportunities": "invalid"}  # Invalid type
    assert not await bank.initialize(config)  # Should return False but not raise
    
    # Test operations on uninitialized bank
    bank = MemoryBank()  # Create new uninitialized bank
    await bank.store_opportunities([MockOpportunity()])  # Should log warning but not raise
    await bank.store_trade_result(
        opportunity=MockOpportunity().__dict__,
        success=True
    )  # Should log warning but not raise
    
    # Test cleanup on uninitialized bank
    await bank.cleanup()  # Should not raise

@pytest.mark.asyncio
async def test_concurrent_operations(memory_bank):
    """Test concurrent operations on memory bank."""
    async def store_opportunities():
        for _ in range(10):
            opportunities = [MockOpportunity() for _ in range(2)]
            await memory_bank.store_opportunities(opportunities)
            await asyncio.sleep(0.1)
    
    async def store_trades():
        for _ in range(10):
            await memory_bank.store_trade_result(
                opportunity=MockOpportunity().__dict__,
                success=True,
                net_profit=10.0
            )
            await asyncio.sleep(0.1)
    
    # Run operations concurrently
    await asyncio.gather(
        store_opportunities(),
        store_trades()
    )
    
    # Verify final state
    assert len(memory_bank.opportunities) == 5  # Limited by max_opportunities
    assert len(memory_bank.trade_results) == 10

if __name__ == "__main__":
    pytest.main([__file__])
