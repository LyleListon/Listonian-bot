"""Common test fixtures and configuration."""

import pytest
import asyncio
from typing import Dict, Any
# import aiohttp # Unused
from unittest.mock import AsyncMock, MagicMock, patch
from web3 import AsyncWeb3 # Removed Web3
# from web3.providers.async_base import AsyncBaseProvider # Unused

from ..web3.web3_manager import Web3Manager


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def mock_eth():
    """Create mock eth module."""
    eth = MagicMock()
    eth.contract = MagicMock()
    eth.get_transaction_count = AsyncMock(return_value=0)
    eth.send_raw_transaction = AsyncMock()
    eth.wait_for_transaction_receipt = AsyncMock()
    return eth


@pytest.fixture(scope="session")
async def mock_w3(mock_eth):
    """Create mock Web3 instance."""
    w3 = MagicMock(spec=AsyncWeb3)
    w3.eth = mock_eth
    w3.is_address = lambda x: len(x) == 42 and x.startswith("0x")
    w3.to_checksum_address = lambda x: x
    return w3


class MockWeb3Manager(Web3Manager):
    """Mock Web3Manager for testing."""

    def __init__(self):
        self.initialized = False
        self._web3 = None
        self.logger = MagicMock()
        self.logger.info = MagicMock()
        self.logger.error = MagicMock()

    async def connect(self):
        """Mock connect method."""
        self.initialized = True
        return True

    def load_abi(self, name: str) -> Dict:
        """Mock load_abi method."""
        return {}


@pytest.fixture(scope="session")
async def web3_manager(mock_w3):
    """Create and initialize Web3Manager instance with mocked web3."""
    manager = MockWeb3Manager()
    manager._web3 = mock_w3
    await manager.connect()
    return manager


@pytest.fixture
def token_addresses() -> Dict[str, str]:
    """Common token addresses for testing."""
    return {
        "WETH": "0x4200000000000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
    }


@pytest.fixture
def test_amounts() -> Dict[str, Dict[str, int]]:
    """Common test amounts for different tokens."""
    return {
        "WETH": {
            "small": int(0.1e18),  # 0.1 WETH
            "medium": int(1e18),  # 1 WETH
            "large": int(10e18),  # 10 WETH
        },
        "USDC": {
            "small": int(100e6),  # 100 USDC
            "medium": int(1000e6),  # 1000 USDC
            "large": int(10000e6),  # 10000 USDC
        },
        "DAI": {
            "small": int(100e18),  # 100 DAI
            "medium": int(1000e18),  # 1000 DAI
            "large": int(10000e18),  # 10000 DAI
        },
    }


@pytest.fixture
def dex_configs() -> Dict[str, Dict[str, Any]]:
    """DEX configurations for testing."""
    return {
        "sushiswap": {
            "name": "Sushiswap",
            "version": "v2",
            "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",  # Base Sushiswap router
            "factory": "0xc35DADB65012eC5796536bD9864eD8773aBc74C4",  # Base Sushiswap factory
            "fee": 3000,
        },
        "baseswap": {
            "name": "BaseSwap",
            "version": "v2",
            "factory": "0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB",
            "router": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
            "quoter": "0x4d47fd5a29904Dae0Ef51b1c450C9750F15D7856",
            "fee": 3000,
        },
    }


@pytest.fixture
def trading_pairs() -> Dict[str, Dict[str, Any]]:
    """Common trading pairs for testing."""
    return {
        "WETH-USDC": {
            "token0": "WETH",
            "token1": "USDC",
            "min_profit_usd": 0.10,
            "max_trade_size_usd": 1000.0,
            "slippage_tolerance": 0.005,
        },
        "WETH-DAI": {
            "token0": "WETH",
            "token1": "DAI",
            "min_profit_usd": 0.10,
            "max_trade_size_usd": 1000.0,
            "slippage_tolerance": 0.005,
        },
    }


@pytest.fixture(autouse=True)
def mock_base_dex():
    """Mock BaseDEXV2 for all tests."""
    with patch("arbitrage_bot.core.dex.base_dex_v2.BaseDEXV2") as mock:
        mock.get_quote_with_impact = AsyncMock()
        mock._calculate_price_impact = MagicMock()
        yield mock


def pytest_configure(config):
    """Configure pytest for the test suite."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
