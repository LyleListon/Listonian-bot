"""Tests for MarketAnalyzer."""

import pytest
import time
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from ..analysis.market_analyzer import MarketAnalyzer, MarketCondition, MarketTrend, PricePoint

@pytest.fixture
async def web3_manager():
    """Create a mock Web3Manager instance."""
    manager = AsyncMock()
    manager.w3 = AsyncMock()
    manager.use_mcp_tool = AsyncMock(side_effect=lambda server, tool, args: {
        "crypto-price": {
            "ethereum": {"usd": 2000.0, "volume_24h": 1000000.0},
            "usd-coin": {"usd": 1.0, "volume_24h": 500000.0}
        },
        "market-analysis": {
            "metrics": {
                "volatility": 0.02,
                "volume": 1000000.0,
                "trend": "up"
            }
        }
    }.get(server))
    return manager

@pytest.fixture
def config():
    """Create test configuration."""
    return {
        "tokens": {
            "WETH": {
                "address": "0x123...",
                "decimals": 18
            },
            "USDC": {
                "address": "0x456...",
                "decimals": 6
            }
        },
        "dexes": {
            "baseswap": {
                "factory": "0x789...",
                "router": "0xabc...",
                "fee": 3000
            },
            "pancakeswap": {
                "factory": "0xdef...",
                "router": "0xghi...",
                "fee": 3000
            }
        },
        "market_update_interval": 1,
        "price_history_hours": 24,
        "min_data_points": 2,
        "trend_threshold": 0.02
    }

@pytest.fixture
async def market_analyzer(web3_manager, config):
    """Create MarketAnalyzer instance."""
    analyzer = MarketAnalyzer(web3_manager, config)
    return analyzer

@pytest.mark.asyncio
async def test_performance_metrics_format(market_analyzer):
    """Test performance metrics format for dashboard."""
    # Add some test transactions
    market_analyzer.transactions = [
        {
            'timestamp': time.time() - 3600,  # 1 hour ago
            'profit_usd': 1.5,
            'status': 'success'
        },
        {
            'timestamp': time.time() - 1800,  # 30 mins ago
            'profit_usd': 2.0,
            'status': 'success'
        }
    ]
    
    # Add market conditions
    market_analyzer.market_conditions = {
        "WETH": MarketCondition(
            price=Decimal("2000.0"),
            trend=MarketTrend(
                direction="up",
                strength=0.8,
                duration=3600,
                volatility=0.02,
                confidence=0.9
            ),
            volume_24h=Decimal("1000000.0"),
            liquidity=Decimal("10000000.0"),
            volatility_24h=0.02,
            price_impact=0.005,
            last_updated=time.time()
        )
    }
    
    metrics = await market_analyzer.get_performance_metrics()
    assert len(metrics) > 0
    
    # Verify metric structure
    metric = metrics[0]
    assert 'timestamp' in metric
    assert 'success_rate' in metric
    assert 'total_profit_usd' in metric
    assert 'portfolio_change_24h' in metric
    assert 'total_trades' in metric
    assert 'trades_24h' in metric
    assert 'active_opportunities' in metric
    assert 'dex_metrics' in metric
    
    # Verify values
    assert metric['total_trades'] == 2
    assert metric['trades_24h'] == 2
    assert metric['total_profit_usd'] == 3.5
    assert metric['portfolio_change_24h'] == 3.5
    assert isinstance(metric['dex_metrics'], dict)

@pytest.mark.asyncio
async def test_market_condition_updates(market_analyzer):
    """Test market condition updates with price caching."""
    # First update
    await market_analyzer._update_market_conditions()
    
    assert "WETH" in market_analyzer.market_conditions
    assert "USDC" in market_analyzer.market_conditions
    
    weth_condition = market_analyzer.market_conditions["WETH"]
    assert float(weth_condition.price) == 2000.0
    assert weth_condition.trend.direction in ["up", "down", "sideways"]
    assert 0 <= weth_condition.price_impact <= 1
    
    # Test price history
    assert "WETH" in market_analyzer.price_history
    assert len(market_analyzer.price_history["WETH"]) > 0
    
    # Verify price point structure
    price_point = market_analyzer.price_history["WETH"][-1]
    assert isinstance(price_point, PricePoint)
    assert float(price_point.price) == 2000.0
    assert price_point.timestamp > 0

@pytest.mark.asyncio
async def test_error_handling_and_fallbacks(market_analyzer):
    """Test error handling and fallback mechanisms."""
    # Test MCP tool failure
    market_analyzer.web3_manager.use_mcp_tool = AsyncMock(return_value=None)
    
    # Should still update with default values
    await market_analyzer._update_market_conditions()
    assert "WETH" in market_analyzer.market_conditions
    
    # Verify error was recorded
    assert len(market_analyzer.report_data['errors']) > 0
    
    # Test recovery after error
    market_analyzer.web3_manager.use_mcp_tool = AsyncMock(side_effect=lambda server, tool, args: {
        "crypto-price": {
            "ethereum": {"usd": 2000.0, "volume_24h": 1000000.0}
        }
    }.get(server))
    
    await market_analyzer._update_market_conditions()
    assert float(market_analyzer.market_conditions["WETH"].price) == 2000.0

@pytest.mark.asyncio
async def test_trend_calculation(market_analyzer):
    """Test market trend calculation."""
    # Add historical price points
    market_analyzer.price_history["WETH"] = [
        PricePoint(
            timestamp=time.time() - 3600,
            price=Decimal("1900.0"),
            volume=Decimal("1000000.0"),
            liquidity=Decimal("10000000.0")
        ),
        PricePoint(
            timestamp=time.time() - 1800,
            price=Decimal("1950.0"),
            volume=Decimal("1000000.0"),
            liquidity=Decimal("10000000.0")
        ),
        PricePoint(
            timestamp=time.time(),
            price=Decimal("2000.0"),
            volume=Decimal("1000000.0"),
            liquidity=Decimal("10000000.0")
        )
    ]
    
    trend = market_analyzer._calculate_trend("WETH")
    assert trend.direction == "up"
    assert trend.strength > 0
    assert trend.confidence > 0
    assert trend.duration > 0

@pytest.mark.asyncio
async def test_alert_generation(market_analyzer):
    """Test alert generation for market conditions."""
    # Add market condition with high volatility
    market_analyzer.market_conditions["WETH"] = MarketCondition(
        price=Decimal("2000.0"),
        trend=MarketTrend(
            direction="up",
            strength=0.8,
            duration=3600,
            volatility=0.15,  # High volatility
            confidence=0.9
        ),
        volume_24h=Decimal("1000000.0"),
        liquidity=Decimal("10000000.0"),
        volatility_24h=0.15,
        price_impact=0.005,
        last_updated=time.time()
    )
    
    await market_analyzer._check_alerts()
    
    # Verify alert was created
    assert len(market_analyzer.alerts) > 0
    alert = market_analyzer.alerts[-1]
    assert alert['level'] == 'warning'
    assert 'High volatility' in alert['message']

@pytest.mark.asyncio
async def test_report_generation(market_analyzer):
    """Test periodic report generation."""
    # Add some test data
    market_analyzer.transactions = [
        {
            'timestamp': time.time() - 3600,
            'profit_usd': 1.5,
            'status': 'success'
        }
    ]
    market_analyzer.alerts = [
        {
            'timestamp': time.time(),
            'level': 'warning',
            'message': 'Test alert'
        }
    ]
    
    await market_analyzer._generate_reports()
    
    # Verify report was generated
    assert market_analyzer.last_report_time > 0
    assert len(market_analyzer.report_data['trades']) > 0
    assert len(market_analyzer.report_data['alerts']) > 0

if __name__ == "__main__":
    pytest.main([__file__])
