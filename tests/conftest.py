"""Test configuration and fixtures."""

import os
import sys
import pytest

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import test dependencies
from arbitrage_bot.core import (
    BaseArbitrageSystem,
    ArbitrageOpportunity,
    ExecutionResult,
    OpportunityStatus,
    ExecutionStatus,
    TransactionStatus
)

from arbitrage_bot.core.interfaces import (
    ArbitrageSystem,
    OpportunityDiscoveryManager,
    OpportunityDetector,
    OpportunityValidator,
    ExecutionManager,
    ExecutionStrategy,
    TransactionMonitor,
    ArbitrageAnalytics,
    MarketDataProvider
)

# Make imports available to all tests
__all__ = [
    'BaseArbitrageSystem',
    'ArbitrageOpportunity',
    'ExecutionResult',
    'OpportunityStatus',
    'ExecutionStatus',
    'TransactionStatus',
    'ArbitrageSystem',
    'OpportunityDiscoveryManager',
    'OpportunityDetector',
    'OpportunityValidator',
    'ExecutionManager',
    'ExecutionStrategy',
    'TransactionMonitor',
    'ArbitrageAnalytics',
    'MarketDataProvider'
]

# Configure pytest
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
