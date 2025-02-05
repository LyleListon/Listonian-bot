"""Test suite for feature pipeline."""

import pytest
import asyncio
import yaml
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
import numpy as np

from ....data_collection.coordinator import DataCollectionCoordinator
from ..pipeline import FeaturePipeline
from ..real_time import RealTimeFeatures
from ..batch import BatchFeatures, BatchConfig

@pytest.fixture
def config():
    """Load test configuration."""
    return {
        'real_time': {
            'update_interval': 1,
            'feature_groups': {
                'gas': {'enabled': True},
                'liquidity': {'enabled': True}
            }
        },
        'batch': {
            'batch_config': {
                'update_interval': 5,
                'history_hours': 1,
                'min_samples': 10
            },
            'feature_groups': {
                'technical': {'enabled': True},
                'patterns': {'enabled': True}
            }
        },
        'feature_sets': {
            'minimal': ['gas', 'liquidity'],
            'full': ['gas', 'liquidity', 'technical', 'patterns']
        }
    }

@pytest.fixture
async def data_coordinator():
    """Create mock data coordinator."""
    coordinator = AsyncMock(spec=DataCollectionCoordinator)
    
    # Mock get_recent_data to return test data
    async def get_recent_data(collector=None, minutes=5):
        if collector == 'network':
            return [
                {
                    'timestamp': datetime.utcnow().isoformat(),
                    'base_fee': 1000000000,
                    'priority_fee': 100000000,
                    'block_utilization': 0.8
                }
                for _ in range(10)
            ]
        elif collector == 'pool':
            return [
                {
                    'timestamp': datetime.utcnow().isoformat(),
                    'liquidity': 1000000,
                    'volume': 500000,
                    'price_impact': 0.01
                }
                for _ in range(10)
            ]
        return []
        
    coordinator.get_recent_data = get_recent_data
    return coordinator

@pytest.mark.asyncio
async def test_real_time_features(data_coordinator, config):
    """Test real-time feature collection."""
    rt_features = RealTimeFeatures(data_coordinator, config['real_time'])
    
    # Start collection
    await rt_features.start()
    
    # Wait for some data collection
    await asyncio.sleep(2)
    
    # Get features
    features = await rt_features.get_features()
    
    # Verify gas features
    assert 'gas' in features
    assert 'base_fee' in features['gas']
    assert 'priority_fee' in features['gas']
    assert isinstance(features['gas']['base_fee'], (int, float))
    
    # Verify liquidity features
    assert 'liquidity' in features
    assert 'total_liquidity' in features['liquidity']
    assert isinstance(features['liquidity']['total_liquidity'], (int, float))
    
    # Stop collection
    await rt_features.stop()

@pytest.mark.asyncio
async def test_batch_features(data_coordinator, config):
    """Test batch feature collection."""
    batch_features = BatchFeatures(data_coordinator, config['batch'])
    
    # Start collection
    await batch_features.start()
    
    # Wait for batch processing
    await asyncio.sleep(6)  # Longer than batch interval
    
    # Get features
    features = await batch_features.get_features()
    
    # Verify technical features
    assert 'technical' in features
    assert 'rsi' in features['technical']
    assert isinstance(features['technical']['rsi'], float)
    
    # Verify pattern features
    assert 'patterns' in features
    assert 'trend_strength' in features['patterns']
    assert isinstance(features['patterns']['trend_strength'], float)
    
    # Stop collection
    await batch_features.stop()

@pytest.mark.asyncio
async def test_feature_pipeline(data_coordinator, config):
    """Test complete feature pipeline."""
    pipeline = FeaturePipeline(data_coordinator, config)
    
    # Start pipeline
    await pipeline.start()
    
    # Test minimal feature set
    minimal_features = await pipeline.get_features('minimal')
    assert 'gas' in minimal_features
    assert 'liquidity' in minimal_features
    
    # Test full feature set (wait for batch processing)
    await asyncio.sleep(6)
    full_features = await pipeline.get_features('full')
    assert 'technical' in full_features
    assert 'patterns' in full_features
    
    # Test feature vector
    feature_vector, feature_names = await pipeline.get_feature_vector('full')
    assert isinstance(feature_vector, np.ndarray)
    assert len(feature_vector) == len(feature_names)
    
    # Stop pipeline
    await pipeline.stop()

@pytest.mark.asyncio
async def test_feature_validation(data_coordinator, config):
    """Test feature validation."""
    pipeline = FeaturePipeline(data_coordinator, config)
    await pipeline.start()
    
    # Test valid features
    valid_features = {
        'gas': {
            'base_fee': 1000000000,
            'priority_fee': 100000000
        },
        'liquidity': {
            'total_liquidity': 1000000
        }
    }
    is_valid, error = await pipeline.validate_features(valid_features)
    assert is_valid
    assert error is None
    
    # Test invalid features (missing required group)
    invalid_features = {
        'gas': {
            'base_fee': 1000000000
        }
    }
    is_valid, error = await pipeline.validate_features(invalid_features)
    assert not is_valid
    assert error is not None
    
    # Test invalid features (invalid value)
    invalid_features = {
        'gas': {
            'base_fee': float('inf'),
            'priority_fee': 100000000
        },
        'liquidity': {
            'total_liquidity': 1000000
        }
    }
    is_valid, error = await pipeline.validate_features(invalid_features)
    assert not is_valid
    assert error is not None
    
    await pipeline.stop()

@pytest.mark.asyncio
async def test_performance_monitoring(data_coordinator, config):
    """Test performance monitoring."""
    pipeline = FeaturePipeline(data_coordinator, config)
    await pipeline.start()
    
    # Generate some load
    for _ in range(5):
        await pipeline.get_features('full')
        await asyncio.sleep(1)
    
    # Get performance stats
    stats = pipeline.get_performance_stats()
    
    # Verify stats structure
    assert 'computation_time' in stats
    assert 'mean' in stats['computation_time']
    assert 'std' in stats['computation_time']
    assert 'feature_counts' in stats
    assert 'error_counts' in stats
    
    # Verify reasonable values
    assert stats['computation_time']['mean'] > 0
    assert stats['computation_time']['mean'] < 1.0  # Should be fast in tests
    
    await pipeline.stop()

@pytest.mark.asyncio
async def test_error_handling(data_coordinator, config):
    """Test error handling."""
    pipeline = FeaturePipeline(data_coordinator, config)
    
    # Mock error in data collection
    data_coordinator.get_recent_data.side_effect = Exception("Test error")
    
    await pipeline.start()
    
    # Should handle error gracefully
    features = await pipeline.get_features('minimal')
    assert features == {}  # Empty but doesn't crash
    
    # Check error was logged
    stats = pipeline.get_performance_stats()
    assert stats['error_counts']['minimal'] > 0
    
    await pipeline.stop()

@pytest.mark.asyncio
async def test_feature_expiry(data_coordinator, config):
    """Test feature expiry."""
    # Set short expiry time for testing
    config['batch']['batch_config']['feature_expiry'] = 2  # 2 seconds
    
    pipeline = FeaturePipeline(data_coordinator, config)
    await pipeline.start()
    
    # Get initial features
    initial_features = await pipeline.get_features('full')
    assert len(initial_features) > 0
    
    # Wait for expiry
    await asyncio.sleep(3)
    
    # Features should be expired
    expired_features = await pipeline.get_features('full')
    assert len(expired_features) < len(initial_features)
    
    await pipeline.stop()