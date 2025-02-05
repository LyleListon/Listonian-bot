"""Test suite for data collection system."""

import pytest
import asyncio
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

from ..base import DataCollector, DataProcessor, DataStorage
from ..collectors.network import NetworkDataCollector
from ..collectors.pool import PoolDataCollector
from ..processors.normalizer import DataNormalizer
from ..processors.feature_extractor import FeatureExtractor
from ..storage.timeseries import TimeSeriesStorage
from ..coordinator import DataCollectionCoordinator

@pytest.fixture
def config():
    """Load test configuration."""
    return {
        'collectors': {
            'network': {
                'enabled': True,
                'interval_seconds': 1,
                'metrics': {
                    'base_fee': {'enabled': True},
                    'priority_fee': {'enabled': True}
                }
            },
            'pool': {
                'enabled': True,
                'interval_seconds': 1,
                'pools': [
                    {
                        'dex': 'test_dex',
                        'pairs': ['TEST/USDC']
                    }
                ]
            }
        },
        'processors': {
            'normalizer': {
                'scaling_method': 'standard',
                'window_size': 10
            },
            'feature_extractor': {
                'window_sizes': [10, 30],
                'combine_method': 'concat'
            }
        },
        'storage': {
            'database_path': ':memory:',  # Use in-memory SQLite
            'retention_days': 1
        }
    }

@pytest.fixture
async def web3_manager():
    """Create mock Web3Manager."""
    manager = AsyncMock()
    manager.web3 = AsyncMock()
    manager.web3.eth.get_block = AsyncMock(return_value={
        'baseFeePerGas': 1000000000,
        'gasUsed': 8000000,
        'gasLimit': 10000000,
        'number': 1000
    })
    manager.web3.eth.gas_price = 1000000000
    manager.web3.eth.max_priority_fee = AsyncMock(return_value=100000000)
    return manager

@pytest.fixture
async def dex_manager():
    """Create mock DEXManager."""
    manager = AsyncMock()
    manager.get_pool_contract = AsyncMock(return_value=AsyncMock())
    return manager

@pytest.mark.asyncio
async def test_network_collector(web3_manager, config):
    """Test NetworkDataCollector."""
    collector = NetworkDataCollector(web3_manager, config['collectors']['network'])
    
    # Test collection
    data = await collector.collect()
    assert data is not None
    assert 'base_fee' in data
    assert 'priority_fee' in data
    assert 'block_utilization' in data
    
    # Test validation
    is_valid, error = await collector.validate_data(data)
    assert is_valid
    assert error is None

@pytest.mark.asyncio
async def test_pool_collector(web3_manager, dex_manager, config):
    """Test PoolDataCollector."""
    collector = PoolDataCollector(
        web3_manager,
        dex_manager,
        config['collectors']['pool']
    )
    
    # Test collection
    data = await collector.collect()
    assert data is not None
    assert len(data) > 0  # Should have data for configured pools
    
    # Test validation
    is_valid, error = await collector.validate_data(data)
    assert is_valid
    assert error is None

@pytest.mark.asyncio
async def test_data_normalizer(config):
    """Test DataNormalizer."""
    normalizer = DataNormalizer(config['processors']['normalizer'])
    
    # Test normalization
    test_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'collector': 'network',
        'base_fee': 1000000000,
        'priority_fee': 100000000
    }
    
    normalized = await normalizer.process(test_data)
    assert normalized is not None
    assert 'normalized_data' in normalized
    assert 'base_fee' in normalized['normalized_data']

@pytest.mark.asyncio
async def test_feature_extractor(config):
    """Test FeatureExtractor."""
    extractor = FeatureExtractor(config['processors']['feature_extractor'])
    
    # Test feature extraction
    test_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'normalized_data': {
            'base_fee': 0.5,
            'priority_fee': 0.3
        }
    }
    
    features = await extractor.process(test_data)
    assert features is not None
    assert 'features' in features
    assert len(features['features']) > 0

@pytest.mark.asyncio
async def test_time_series_storage(config):
    """Test TimeSeriesStorage."""
    storage = TimeSeriesStorage(config['storage'])
    
    # Test storing data
    test_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'collector': 'network',
        'data': {'base_fee': 1000000000}
    }
    
    await storage.store(test_data)
    
    # Test retrieving data
    data = await storage.retrieve({
        'start_time': (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
        'end_time': datetime.utcnow().isoformat()
    })
    
    assert len(data) > 0
    assert data[0]['collector'] == 'network'

@pytest.mark.asyncio
async def test_coordinator(web3_manager, dex_manager, config):
    """Test DataCollectionCoordinator."""
    coordinator = DataCollectionCoordinator(config)
    
    # Test initialization
    success = await coordinator.initialize(web3_manager, dex_manager)
    assert success
    
    # Test starting collection
    await coordinator.start()
    
    # Wait for some data collection
    await asyncio.sleep(2)
    
    # Test getting status
    status = await coordinator.get_status()
    assert status is not None
    assert 'collectors' in status
    assert 'storage' in status
    
    # Test getting recent data
    data = await coordinator.get_recent_data(minutes=1)
    assert len(data) > 0
    
    # Test stopping collection
    await coordinator.stop()
    
    # Verify system stopped
    status = await coordinator.get_status()
    assert all(s == 'stopped' for s in status['collectors'].values())

@pytest.mark.asyncio
async def test_error_handling(web3_manager, dex_manager, config):
    """Test error handling in data collection system."""
    # Simulate network error
    web3_manager.web3.eth.get_block.side_effect = Exception("Network error")
    
    coordinator = DataCollectionCoordinator(config)
    await coordinator.initialize(web3_manager, dex_manager)
    await coordinator.start()
    
    # Wait for error to occur
    await asyncio.sleep(2)
    
    # Check error was logged
    status = await coordinator.get_status()
    assert len(status['errors']) > 0
    
    await coordinator.stop()

@pytest.mark.asyncio
async def test_pipeline_integration(web3_manager, dex_manager, config):
    """Test complete data collection pipeline."""
    coordinator = DataCollectionCoordinator(config)
    await coordinator.initialize(web3_manager, dex_manager)
    
    # Create test processor to verify pipeline
    class TestProcessor(DataProcessor):
        def __init__(self):
            self.processed_data = []
            
        async def process(self, data):
            self.processed_data.append(data)
            return data
    
    test_processor = TestProcessor()
    coordinator.processors['test'] = test_processor
    
    # Start collection
    await coordinator.start()
    
    # Wait for data to flow through pipeline
    await asyncio.sleep(2)
    
    # Verify data reached end of pipeline
    assert len(test_processor.processed_data) > 0
    
    await coordinator.stop()