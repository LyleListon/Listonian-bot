"""Test suite for ML models."""

import pytest
import torch
import numpy as np
from unittest.mock import Mock, AsyncMock
import asyncio
from datetime import datetime
import yaml
from pathlib import Path

from ..online_lstm import OnlineLSTM
from ..predictors import GasPricePredictor, LiquidityPredictor
from ..manager import ModelManager
from ...feature_pipeline.pipeline import FeaturePipeline

@pytest.fixture
def config():
    """Load test configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)

@pytest.fixture
def feature_pipeline():
    """Create mock feature pipeline."""
    pipeline = AsyncMock(spec=FeaturePipeline)
    
    # Mock feature vector generation
    async def get_feature_vector(feature_set='standard'):
        if feature_set == 'minimal':
            return np.random.randn(60, 32), ['feature_' + str(i) for i in range(32)]
        else:
            return np.random.randn(120, 48), ['feature_' + str(i) for i in range(48)]
            
    pipeline.get_feature_vector = get_feature_vector
    
    # Mock feature retrieval
    async def get_features(feature_set='standard'):
        if feature_set == 'minimal':
            return {
                'gas': {
                    'base_fee': 1000000000,
                    'priority_fee': 100000000,
                    'volatility': 0.1
                }
            }
        else:
            return {
                'gas': {
                    'base_fee': 1000000000,
                    'priority_fee': 100000000,
                    'volatility': 0.1
                },
                'liquidity': {
                    'total_liquidity': 1000000,
                    'volume': 500000,
                    'price_impact': 0.01,
                    'volatility': 0.2
                }
            }
            
    pipeline.get_features = get_features
    
    return pipeline

@pytest.mark.asyncio
async def test_online_lstm():
    """Test base OnlineLSTM model."""
    config = {
        'input_size': 10,
        'hidden_size': 32,
        'num_layers': 2,
        'output_size': 2,
        'sequence_length': 20,
        'learning_rate': 0.001,
        'batch_size': 16,
        'memory_size': 1000
    }
    
    model = OnlineLSTM(config)
    
    # Test forward pass
    x = torch.randn(1, 20, 10)  # batch_size, sequence_length, input_size
    output, hidden = model(x)
    
    assert output.shape == (1, 2)  # batch_size, output_size
    assert len(hidden) == 2  # (h_n, c_n) for LSTM
    assert hidden[0].shape == (2, 1, 32)  # num_layers, batch_size, hidden_size
    
    # Test update
    features = np.random.randn(20, 10)
    target = np.array([1.0, 0.1])
    
    # Update multiple times
    for _ in range(100):
        model.update(features, target)
        
    # Check training stats
    stats = model.get_training_stats()
    assert 'loss_mean' in stats
    assert 'updates' in stats
    assert stats['updates'] == 100

@pytest.mark.asyncio
async def test_gas_price_predictor():
    """Test GasPricePredictor."""
    config = {
        'input_size': 32,
        'hidden_size': 64,
        'num_layers': 2,
        'sequence_length': 60,
        'learning_rate': 0.001,
        'batch_size': 16,
        'memory_size': 1000,
        'price_weight': 1.0,
        'volatility_weight': 0.5
    }
    
    predictor = GasPricePredictor(config)
    
    # Test prediction
    features = np.random.randn(60, 32)
    price, uncertainty, metadata = predictor.predict(features)
    
    assert isinstance(price, float)
    assert isinstance(uncertainty, float)
    assert 'confidence' in metadata
    
    # Test learning
    target = np.array([1000000000, 0.1])  # price, volatility
    
    # Update multiple times
    for _ in range(100):
        predictor.update(features, target)
        
    # Check performance
    stats = predictor.get_training_stats()
    assert 'loss_mean' in stats
    assert stats['updates'] == 100

@pytest.mark.asyncio
async def test_liquidity_predictor():
    """Test LiquidityPredictor."""
    config = {
        'input_size': 48,
        'hidden_size': 128,
        'num_layers': 2,
        'sequence_length': 120,
        'learning_rate': 0.001,
        'batch_size': 32,
        'memory_size': 1000,
        'liquidity_weight': 1.0,
        'volume_weight': 0.8,
        'impact_weight': 0.6
    }
    
    predictor = LiquidityPredictor(config)
    
    # Test prediction
    features = np.random.randn(120, 48)
    metrics, uncertainty, metadata = predictor.predict(features)
    
    assert len(metrics) == 3  # liquidity, volume, impact
    assert isinstance(uncertainty, float)
    assert 'confidence' in metadata
    
    # Test learning
    target = np.array([1000000, 500000, 0.01, 0.2])  # liquidity, volume, impact, volatility
    
    # Update multiple times
    for _ in range(100):
        predictor.update(features, target)
        
    # Check performance
    stats = predictor.get_training_stats()
    assert 'loss_mean' in stats
    assert stats['updates'] == 100

@pytest.mark.asyncio
async def test_model_manager(config, feature_pipeline):
    """Test ModelManager."""
    manager = ModelManager(feature_pipeline, config['model'])
    
    # Start manager
    await manager.start()
    
    # Test gas price prediction
    gas_prediction = await manager.predict_gas_price()
    assert 'predicted_price' in gas_prediction
    assert 'uncertainty' in gas_prediction
    assert 'confidence' in gas_prediction
    
    # Test liquidity prediction
    liquidity_prediction = await manager.predict_liquidity()
    assert 'liquidity' in liquidity_prediction
    assert 'uncertainty' in liquidity_prediction
    assert 'confidence' in liquidity_prediction
    
    # Test performance monitoring
    stats = manager.get_performance_stats()
    assert 'gas' in stats
    assert 'liquidity' in stats
    
    # Stop manager
    await manager.stop()

@pytest.mark.asyncio
async def test_online_learning(config, feature_pipeline):
    """Test online learning capabilities."""
    manager = ModelManager(feature_pipeline, config['model'])
    await manager.start()
    
    # Track predictions over time
    predictions = []
    
    # Simulate real-time updates
    for _ in range(10):
        # Get predictions
        gas_pred = await manager.predict_gas_price()
        liquidity_pred = await manager.predict_liquidity()
        
        predictions.append({
            'gas': gas_pred['predicted_price'],
            'liquidity': liquidity_pred['liquidity']['total']
        })
        
        # Wait for updates
        await asyncio.sleep(1)
        
    # Verify learning progress
    stats = manager.get_performance_stats()
    assert stats['gas']['model_stats']['updates'] > 0
    assert stats['liquidity']['model_stats']['updates'] > 0
    
    await manager.stop()

@pytest.mark.asyncio
async def test_error_handling(config, feature_pipeline):
    """Test error handling in models."""
    manager = ModelManager(feature_pipeline, config['model'])
    await manager.start()
    
    # Test invalid features
    feature_pipeline.get_feature_vector.side_effect = Exception("Feature error")
    
    # Should handle error gracefully
    prediction = await manager.predict_gas_price()
    assert prediction['uncertainty'] == float('inf')
    assert prediction['confidence'] == 0.0
    
    # Test invalid target
    feature_pipeline.get_features.side_effect = Exception("Target error")
    
    # Should continue running
    await asyncio.sleep(2)
    stats = manager.get_performance_stats()
    assert 'error' in stats['gas']['model_stats']
    
    await manager.stop()

@pytest.mark.asyncio
async def test_model_persistence(config, feature_pipeline, tmp_path):
    """Test model saving and loading."""
    # Configure save path
    config['model']['persistence']['save_path'] = str(tmp_path)
    config['model']['persistence']['enabled'] = True
    
    manager = ModelManager(feature_pipeline, config['model'])
    await manager.start()
    
    # Generate some predictions
    for _ in range(5):
        await manager.predict_gas_price()
        await manager.predict_liquidity()
        await asyncio.sleep(1)
        
    # Wait for save
    await asyncio.sleep(2)
    
    # Verify files were created
    save_files = list(tmp_path.glob('*.pt'))
    assert len(save_files) > 0
    
    await manager.stop()