"""
DEX Discovery Tests

This module contains tests for the DEX discovery system.
"""

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from arbitrage_bot.core.arbitrage.discovery.sources.base import DEXInfo, DEXProtocolType
from arbitrage_bot.core.arbitrage.discovery.sources.repository import DEXRepository
from arbitrage_bot.core.arbitrage.discovery.sources.validator import DEXValidator
from arbitrage_bot.core.arbitrage.discovery.sources.defillama import DefiLlamaSource
from arbitrage_bot.core.arbitrage.discovery.sources.manager import DEXDiscoveryManager


@pytest.fixture
def mock_web3_manager():
    """Create a mock Web3 manager."""
    mock = MagicMock()
    mock.w3 = MagicMock()
    mock.w3.is_address = lambda addr: True
    mock.w3.eth.get_code = AsyncMock(return_value=b'0x123456')
    mock.contract = MagicMock(return_value=MagicMock())
    return mock


@pytest.fixture
async def dex_repository():
    """Create a DEX repository for testing."""
    config = {
        "storage_dir": "tests/data/dexes",
        "storage_file": "test_dexes.json",
        "auto_save": True
    }
    
    # Create directory if it doesn't exist
    os.makedirs("tests/data/dexes", exist_ok=True)
    
    repository = DEXRepository(config)
    await repository.initialize()
    
    yield repository
    
    # Clean up
    await repository.cleanup()
    if os.path.exists("tests/data/dexes/test_dexes.json"):
        os.remove("tests/data/dexes/test_dexes.json")


@pytest.fixture
async def dex_validator(mock_web3_manager):
    """Create a DEX validator for testing."""
    validator = DEXValidator(mock_web3_manager)
    await validator.initialize()
    
    yield validator
    
    await validator.cleanup()


@pytest.fixture
async def mock_defillama_source():
    """Create a mock DefiLlama source."""
    source = MagicMock(spec=DefiLlamaSource)
    source.fetch_dexes = AsyncMock(return_value=[
        DEXInfo(
            name="test_dex_1",
            protocol_type=DEXProtocolType.UNISWAP_V2,
            version="v2",
            chain_id=8453,
            factory_address="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
            router_address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            source="defillama"
        ),
        DEXInfo(
            name="test_dex_2",
            protocol_type=DEXProtocolType.UNISWAP_V3,
            version="v3",
            chain_id=8453,
            factory_address="0x1F98431c8aD98523631AE4a59f267346ea31F984",
            router_address="0xE592427A0AEce92De3Edee1F18E0157C05861564",
            quoter_address="0xb27308f9F90D607463bb33eA1BeBb41C27CE5AB6",
            source="defillama"
        )
    ])
    source.initialize = AsyncMock(return_value=True)
    source.cleanup = AsyncMock()
    
    return source


@pytest.fixture
async def discovery_manager(mock_web3_manager, dex_repository, dex_validator, mock_defillama_source):
    """Create a DEX discovery manager for testing."""
    # Patch the _create_sources method to prevent it from overwriting our mock
    with patch.object(DEXDiscoveryManager, '_create_sources', new_callable=AsyncMock) as mock_create_sources:
        manager = DEXDiscoveryManager(
            web3_manager=mock_web3_manager,
            repository=dex_repository,
            validator=dex_validator,
            config={"chain_id": 8453}
        )
        
        # Set sources directly
        manager._sources = {"defillama": mock_defillama_source}
        
        await manager.initialize()
        
        yield manager
        
        await manager.cleanup()


@pytest.mark.asyncio
async def test_discover_dexes(discovery_manager, mock_defillama_source):
    """Test discovering DEXes."""
    # Mock validator to always return valid
    discovery_manager.validator.validate_dex = AsyncMock(return_value=(True, []))
    
    # Discover DEXes
    dexes = await discovery_manager.discover_dexes()
    
    # Check that DEXes were discovered
    assert len(dexes) == 2
    assert dexes[0].name == "test_dex_1"
    assert dexes[1].name == "test_dex_2"
    
    # Check that DEXes were added to repository
    repo_dexes = await discovery_manager.get_dexes()
    assert len(repo_dexes) == 2
    assert repo_dexes[0].name == "test_dex_1"
    assert repo_dexes[1].name == "test_dex_2"
    
    # Check that source was called
    mock_defillama_source.fetch_dexes.assert_called_once_with(8453)


@pytest.mark.asyncio
async def test_get_dex_by_address(discovery_manager, mock_defillama_source):
    """Test getting a DEX by address."""
    # Mock validator to always return valid
    discovery_manager.validator.validate_dex = AsyncMock(return_value=(True, []))
    
    # Discover DEXes
    await discovery_manager.discover_dexes()
    
    # Get DEX by address
    dex = await discovery_manager.get_dex_by_address("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
    
    # Check that DEX was found
    assert dex is not None
    assert dex.name == "test_dex_1"
    assert dex.factory_address == "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"


@pytest.mark.asyncio
async def test_validate_dex(discovery_manager):
    """Test validating a DEX."""
    # Create a DEX
    dex = DEXInfo(
        name="test_dex",
        protocol_type=DEXProtocolType.UNISWAP_V2,
        version="v2",
        chain_id=8453,
        factory_address="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        router_address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        source="test"
    )
    
    # Mock validator to return valid
    discovery_manager.validator.validate_dex = AsyncMock(return_value=(True, []))
    
    # Validate DEX
    is_valid, errors = await discovery_manager.validate_dex(dex)
    
    # Check that DEX was validated
    assert is_valid
    assert len(errors) == 0
    
    # Check that validator was called
    discovery_manager.validator.validate_dex.assert_called_once_with(dex)


@pytest.mark.asyncio
async def test_repository_persistence(dex_repository):
    """Test that the repository persists DEXes."""
    # Create a DEX
    dex = DEXInfo(
        name="test_dex",
        protocol_type=DEXProtocolType.UNISWAP_V2,
        version="v2",
        chain_id=8453,
        factory_address="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
        router_address="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
        source="test"
    )
    
    # Add DEX to repository
    await dex_repository.add_dex(dex)
    
    # Create a new repository
    new_repository = DEXRepository({
        "storage_dir": "tests/data/dexes",
        "storage_file": "test_dexes.json",
        "auto_save": True
    })
    await new_repository.initialize()
    
    # Check that DEX was loaded
    loaded_dex = await new_repository.get_dex("test_dex")
    assert loaded_dex is not None
    assert loaded_dex.name == "test_dex"
    assert loaded_dex.factory_address == "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
    
    # Clean up
    await new_repository.cleanup()