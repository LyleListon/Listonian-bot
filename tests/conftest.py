"""
Common test fixtures and configuration.

This module provides:
1. Shared test fixtures
2. Mock implementations
3. Helper functions
4. Test configuration
"""

import os
import json
import pytest
import asyncio
import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / 'data'

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Load test configuration."""
    config_path = TEST_DATA_DIR / 'test_config.json'
    with open(config_path) as f:
        return json.load(f)

@pytest.fixture
def monitoring_data() -> Dict[str, Any]:
    """Load monitoring data."""
    data_path = TEST_DATA_DIR / 'monitoring_sample.json'
    with open(data_path) as f:
        return json.load(f)

@pytest.fixture
def dex_response() -> Dict[str, Any]:
    """Load DEX response data."""
    response_path = TEST_DATA_DIR / 'dex_response_baseswap.json'
    with open(response_path) as f:
        return json.load(f)

@pytest.fixture
def sample_transactions() -> Dict[str, Any]:
    """Load sample transaction data."""
    transactions_path = TEST_DATA_DIR / 'sample_transactions.json'
    with open(transactions_path) as f:
        return json.load(f)

@pytest.fixture
async def mock_web3_provider():
    """Mock Web3 provider."""
    class MockWeb3:
        async def eth_call(self, *args, **kwargs):
            return "0x" + "0" * 64
        
        async def eth_get_balance(self, *args, **kwargs):
            return "0x" + "0" * 64
        
        async def eth_get_block_number(self, *args, **kwargs):
            return 12345678
    
    return MockWeb3()

@pytest.fixture
async def mock_contract():
    """Mock contract instance."""
    class MockContract:
        async def functions(self):
            return self
        
        async def call(self, *args, **kwargs):
            return [
                "1234567890",  # sqrtPriceX96
                12345,         # tick
                "1000000"      # liquidity
            ]
    
    return MockContract()

@pytest.fixture
async def mock_pool():
    """Mock pool instance with standard V3 interface."""
    class MockPool:
        def __init__(self):
            self.token0 = "0x4200000000000000000000000000000000000006"
            self.token1 = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
            self.fee = 300
            self.liquidity = "1000000"
            self.sqrt_price_x96 = "1234567890"
            self.tick = 12345
        
        async def slot0(self):
            return [
                self.sqrt_price_x96,
                self.tick,
                0,  # observation index
                0,  # observation cardinality
                0,  # observation cardinality next
                0,  # fee protocol
                True  # unlocked
            ]
        
        async def liquidity(self):
            return self.liquidity
    
    return MockPool()

@pytest.fixture
def event_loop():
    """Create and provide a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()

@pytest.fixture
async def mock_cache():
    """Mock cache implementation."""
    class MockCache:
        def __init__(self):
            self._data = {}
        
        async def get(self, key: str) -> Optional[Any]:
            return self._data.get(key)
        
        async def set(self, key: str, value: Any, expire: Optional[int] = None) -> None:
            self._data[key] = value
        
        async def delete(self, key: str) -> None:
            self._data.pop(key, None)
    
    return MockCache()

@pytest.fixture
async def mock_db():
    """Mock database implementation."""
    class MockDB:
        async def execute(self, query: str, *args, **kwargs):
            return True
        
        async def fetchone(self):
            return [1]
        
        async def fetchall(self):
            return [[1, 'test']]
        
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
    
    return MockDB()

def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "async_test: mark test as async test"
    )
