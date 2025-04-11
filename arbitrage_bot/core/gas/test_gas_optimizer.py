"""Tests for gas optimization system."""

import pytest
from unittest.mock import Mock, patch
from typing import Any, Dict

from unittest.mock import create_autospec, Mock, patch
from .gas_optimizer import GasOptimizer, create_gas_optimizer


# Create mock classes instead of importing
class MockWeb3Manager:
    def __init__(self):
        self.w3 = None


class MockDEXManager:
    def __init__(self):
        self.web3_manager = None


@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance."""
    mock = Mock()
    mock.eth = Mock()

    # Mock async gas_price property
    async def mock_gas_price():
        return 50000000000  # 50 gwei

    mock.eth.gas_price = mock_gas_price()
    return mock


@pytest.fixture
def mock_web3_manager(mock_web3):
    """Create a mock Web3Manager instance."""
    mock = create_autospec(MockWeb3Manager)
    mock.w3 = mock_web3
    return mock


@pytest.fixture
def mock_dex_manager(mock_web3_manager):
    """Create a mock DEXManager instance."""
    mock = create_autospec(MockDEXManager)
    mock.web3_manager = mock_web3_manager
    return mock


@pytest.mark.asyncio
async def test_get_web3_instance_from_web3_manager(mock_web3_manager, mock_dex_manager):
    """Test getting Web3 instance from web3_manager."""
    optimizer = GasOptimizer(
        dex_manager=mock_dex_manager, web3_manager=mock_web3_manager
    )
    w3 = optimizer.get_web3_instance()
    assert w3 == mock_web3_manager.w3


@pytest.mark.asyncio
async def test_get_web3_instance_from_dex_manager(mock_dex_manager):
    """Test getting Web3 instance from dex_manager when web3_manager is None."""
    optimizer = GasOptimizer(dex_manager=mock_dex_manager)
    w3 = optimizer.get_web3_instance()
    assert w3 == mock_dex_manager.web3_manager.w3


@pytest.mark.asyncio
async def test_get_web3_instance_handles_none():
    """Test handling of None values in Web3 instance retrieval."""
    mock_dex = create_autospec(MockDEXManager)
    mock_dex.web3_manager = None
    optimizer = GasOptimizer(dex_manager=mock_dex)
    w3 = optimizer.get_web3_instance()
    assert w3 is None


@pytest.mark.asyncio
async def test_update_gas_history(mock_web3_manager, mock_dex_manager):
    """Test gas history updates correctly."""
    optimizer = GasOptimizer(
        dex_manager=mock_dex_manager, web3_manager=mock_web3_manager
    )
    await optimizer._update_gas_history()
    assert len(optimizer.gas_prices) == optimizer.gas_history_window
    assert optimizer.gas_prices[-1] == 50000000000


@pytest.mark.asyncio
async def test_get_optimal_gas_price(mock_web3_manager, mock_dex_manager):
    """Test optimal gas price calculation."""
    optimizer = GasOptimizer(
        dex_manager=mock_dex_manager, web3_manager=mock_web3_manager
    )
    await optimizer._update_gas_history()
    optimal_price = await optimizer.get_optimal_gas_price()
    assert optimal_price == int(50000000000 * optimizer.gas_price_buffer)


@pytest.mark.asyncio
async def test_create_gas_optimizer(mock_web3_manager, mock_dex_manager):
    """Test gas optimizer creation."""
    optimizer = await create_gas_optimizer(
        dex_manager=mock_dex_manager, web3_manager=mock_web3_manager
    )
    assert isinstance(optimizer, GasOptimizer)
    assert optimizer.web3_manager == mock_web3_manager
    assert optimizer.dex_manager == mock_dex_manager


@pytest.mark.asyncio
async def test_create_gas_optimizer_fallback(mock_dex_manager):
    """Test gas optimizer creation falls back to dex_manager's web3_manager."""
    optimizer = await create_gas_optimizer(dex_manager=mock_dex_manager)
    assert isinstance(optimizer, GasOptimizer)
    assert optimizer.web3_manager == mock_dex_manager.web3_manager


@pytest.mark.asyncio
async def test_optimize_path_gas(mock_web3_manager, mock_dex_manager):
    """Test path gas optimization."""
    optimizer = GasOptimizer(
        dex_manager=mock_dex_manager, web3_manager=mock_web3_manager
    )
    paths = [
        {
            "dex_name": "TestDEX",
            "path": ["TokenA", "TokenB", "TokenC"],
            "quoter": True,  # v3 protocol
        }
    ]
    optimized = await optimizer.optimize_path_gas(paths)
    assert len(optimized) == 1
    assert "gas_limit" in optimized[0]
    assert "gas_price" in optimized[0]
    assert "gas_cost" in optimized[0]


@pytest.mark.asyncio
async def test_analyze_gas_usage(mock_web3_manager, mock_dex_manager):
    """Test gas usage analysis."""
    optimizer = GasOptimizer(
        dex_manager=mock_dex_manager, web3_manager=mock_web3_manager
    )
    await optimizer._update_gas_history()

    # Add some gas stats
    await optimizer.update_gas_stats("TestDEX", "v3", 300000, 3)

    analysis = await optimizer.analyze_gas_usage()
    assert "current_gas_price" in analysis
    assert "dex_stats" in analysis
    assert "protocol_stats" in analysis
    assert "recommendations" in analysis
