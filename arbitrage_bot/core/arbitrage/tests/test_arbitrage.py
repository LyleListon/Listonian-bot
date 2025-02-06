"""Test suite for arbitrage detection system."""

import pytest
import asyncio
import yaml
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
import numpy as np
from pathlib import Path

from ..detector import AggressiveArbitrageDetector, ArbitrageOpportunity
from ..risk_manager import RiskManager
from ...ml.models.manager import ModelManager
from ...dex.dex_manager import DEXManager

@pytest.fixture
def config():
    """Load test configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'default_config.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)

@pytest.fixture
def model_manager():
    """Create mock model manager."""
    manager = AsyncMock(spec=ModelManager)
    
    # Mock gas price prediction
    async def predict_gas_price():
        return {
            'predicted_price': 50000000000,  # 50 gwei
            'uncertainty': 0.1,
            'confidence': 0.9,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': {'volatility': 0.2}
        }
    manager.predict_gas_price = predict_gas_price
    
    # Mock liquidity prediction
    async def predict_liquidity():
        return {
            'liquidity': {
                'total': 1000000,
                'volume': 500000,
                'impact': 0.01
            },
            'uncertainty': 0.15,
            'confidence': 0.85,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': {'volatility': 0.3}
        }
    manager.predict_liquidity = predict_liquidity
    
    return manager

@pytest.fixture
def dex_manager():
    """Create mock DEX manager."""
    manager = AsyncMock(spec=DEXManager)
    
    # Mock pool data
    async def get_active_pools():
        return [
            {
                'address': '0x1',
                'dex': 'uniswap',
                'token0': '0xa',
                'token1': '0xb',
                'price': 1000,
                'liquidity': 1000000
            },
            {
                'address': '0x2',
                'dex': 'sushiswap',
                'token0': '0xa',
                'token1': '0xb',
                'price': 1002,
                'liquidity': 900000
            }
        ]
    manager.get_active_pools = get_active_pools
    
    # Mock token prices
    async def get_token_prices():
        return {
            '0xa': 1.0,
            '0xb': 1000.0
        }
    manager.get_token_prices = get_token_prices
    
    return manager

@pytest.mark.asyncio
async def test_opportunity_detection(config, model_manager, dex_manager):
    """Test arbitrage opportunity detection."""
    detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
    
    # Start detector
    await detector.start()
    
    # Wait for detection cycle
    await asyncio.sleep(1)
    
    # Check opportunities
    assert len(detector.opportunities) > 0
    
    # Verify opportunity structure
    opp = detector.opportunities[0]
    assert isinstance(opp, ArbitrageOpportunity)
    assert len(opp.path) > 0
    assert opp.expected_profit > 0
    assert 0 <= opp.confidence <= 1
    assert opp.gas_cost > 0
    assert opp.execution_time > 0
    assert opp.position_size > 0
    assert 0 <= opp.risk_score <= 1
    
    await detector.stop()

@pytest.mark.asyncio
async def test_risk_management(config):
    """Test risk management system."""
    risk_manager = RiskManager(config['risk_management'])
    
    # Test position sizing
    position_size = risk_manager.calculate_position_size(
        profit_potential=0.01,  # 1% profit
        uncertainty=0.1,
        current_volatility=0.2
    )
    assert position_size > 0
    assert position_size <= config['risk_management']['initial_capital']
    
    # Test risk limits
    within_limits, reason = risk_manager.check_risk_limits()
    assert within_limits
    assert reason is None
    
    # Test trade recording
    risk_manager.record_trade(
        trade_id='test1',
        position_size=10000,
        entry_price=1000,
        profit=100
    )
    
    metrics = risk_manager.get_metrics()
    assert metrics['capital'] > config['risk_management']['initial_capital']
    assert metrics['win_rate'] > 0

@pytest.mark.asyncio
async def test_ml_integration(config, model_manager, dex_manager):
    """Test integration with ML predictions."""
    detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
    await detector.start()
    
    # Get predictions
    gas_prediction = await model_manager.predict_gas_price()
    liquidity_prediction = await model_manager.predict_liquidity()
    
    # Find opportunities
    opportunities = await detector._find_opportunities(
        gas_prediction,
        liquidity_prediction
    )
    
    # Verify ML predictions influence opportunities
    assert len(opportunities) > 0
    for opp in opportunities:
        # Gas cost should reflect prediction
        assert abs(opp.gas_cost - gas_prediction['predicted_price']) < 1e-6
        
        # Position size should consider liquidity
        assert opp.position_size <= liquidity_prediction['liquidity']['total']
        
    await detector.stop()

@pytest.mark.asyncio
async def test_aggressive_behavior(config, model_manager, dex_manager):
    """Test aggressive trading behavior."""
    detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
    await detector.start()
    
    # Get opportunities
    await asyncio.sleep(1)
    opportunities = detector.opportunities
    
    # Verify aggressive characteristics
    if opportunities:
        opp = opportunities[0]
        
        # Should accept lower confidence
        assert opp.confidence >= 0.6  # Lower threshold
        
        # Should take larger positions
        assert opp.position_size >= 0.1 * config['detector']['max_position_size']
        
        # Should accept higher risk
        assert opp.risk_score >= 0.3  # More aggressive
        
    await detector.stop()

@pytest.mark.asyncio
async def test_performance_monitoring(config, model_manager, dex_manager):
    """Test performance monitoring."""
    detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
    await detector.start()
    
    # Simulate some trades
    for i in range(5):
        detector.performance_stats['trades_executed'] += 1
        detector.performance_stats['successful_trades'] += 1
        detector.performance_stats['total_profit'] += 100
        
    # Get status
    status = detector.get_status()
    
    # Verify metrics
    assert status['trades_executed'] == 5
    assert status['successful_trades'] == 5
    assert status['total_profit'] == 500
    assert 'risk_metrics' in status
    
    await detector.stop()

@pytest.mark.asyncio
async def test_error_handling(config, model_manager, dex_manager):
    """Test error handling."""
    detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
    
    # Mock error in predictions
    model_manager.predict_gas_price.side_effect = Exception("Prediction error")
    
    await detector.start()
    
    # Should handle error gracefully
    await asyncio.sleep(1)
    status = detector.get_status()
    
    # Should still be running
    assert len(detector.opportunities) == 0  # No opportunities due to error
    assert status['trades_executed'] == 0
    
    await detector.stop()

@pytest.mark.asyncio
async def test_concurrent_trades(config, model_manager, dex_manager):
    """Test handling of concurrent trades."""
    detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
    await detector.start()
    
    # Simulate multiple opportunities
    opportunities = [
        ArbitrageOpportunity(
            path=['0x1', '0x2'],
            expected_profit=100,
            confidence=0.9,
            gas_cost=50000000000,
            execution_time=1.0,
            position_size=10000,
            risk_score=0.8,
            timestamp=datetime.utcnow(),
            metadata={}
        )
        for _ in range(5)
    ]
    
    # Process opportunities
    for opp in opportunities:
        await detector._emit_opportunity(opp)
        
    # Verify trade tracking
    assert len(detector.active_trades) <= config['global']['max_concurrent_trades']
    
    await detector.stop()

@pytest.mark.asyncio
async def test_position_sizing(config, model_manager, dex_manager):
    """Test position sizing logic."""
    detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
    
    # Test different scenarios
    sizes = []
    
    # High confidence, low uncertainty
    size = detector._calculate_position_size(
        profit=0.01,
        gas_uncertainty=0.1,
        liquidity_uncertainty=0.1
    )
    sizes.append(size)
    
    # Low confidence, high uncertainty
    size = detector._calculate_position_size(
        profit=0.01,
        gas_uncertainty=0.4,
        liquidity_uncertainty=0.4
    )
    sizes.append(size)
    
    # Verify aggressive sizing
    assert sizes[0] > sizes[1]  # Larger size for better conditions
    assert sizes[0] >= 0.5 * config['detector']['max_position_size']  # Aggressive sizing