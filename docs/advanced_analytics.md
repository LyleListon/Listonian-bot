# Advanced Analytics

This document provides an overview of the advanced analytics components for the Listonian Arbitrage Bot. These components enable comprehensive profit tracking, performance analysis, and market insights to optimize arbitrage strategies.

## Components Overview

The advanced analytics system consists of the following components:

1. **Profit Tracker**: Tracks and analyzes profit metrics for arbitrage operations
2. **Performance Analyzer**: Analyzes trading performance with advanced metrics
3. **Trading Journal**: Manages detailed trade logging and analysis
4. **Market Analyzer**: Analyzes market trends and conditions
5. **Alert System**: Manages alerts for the arbitrage system
6. **Dashboard Generator**: Generates dashboard components for visualization
7. **Report Generator**: Generates reports for the arbitrage system

## Profit Tracking and Analysis

The `ProfitTracker` class provides comprehensive profit tracking and analysis:

- Historical performance tracking
- Profit attribution by token pair
- ROI calculation with various time frames
- Profit visualization with time series analysis

```python
from arbitrage_bot.core.analytics import create_profit_tracker

# Initialize profit tracker
profit_tracker = await create_profit_tracker()

# Track a trade profit
await profit_tracker.track_profit({
    'token_in': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',  # UNI (checksummed)
    'token_out': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH (checksummed)
    'amount_in': 10.0,
    'amount_out': 0.05,
    'profit': 0.02,
    'gas_cost': 0.005,
    'timestamp': datetime.utcnow(),
    'dexes': ['uniswap', 'sushiswap'],
    'path': ['0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2']
})

# Get profit metrics
profit_summary = await profit_tracker.get_profit_summary()
token_pair_profits = await profit_tracker.get_profit_by_token_pair(timeframe="24h")
roi = await profit_tracker.get_roi(timeframe="7d")
top_pairs = await profit_tracker.get_top_token_pairs(timeframe="30d", limit=5)
time_series = await profit_tracker.get_profit_time_series(timeframe="7d", interval="1h")
```

## Performance Analysis

The `PerformanceAnalyzer` class provides advanced performance analysis:

- Performance benchmarking against market indices
- Drawdown analysis
- Volatility calculation
- Risk-adjusted performance metrics (Sharpe, Sortino, Calmar ratios)

```python
from arbitrage_bot.core.analytics.performance_analyzer import PerformanceAnalyzer

# Initialize performance analyzer
performance_analyzer = PerformanceAnalyzer()
await performance_analyzer.initialize()

# Track performance
await performance_analyzer.track_performance({
    'portfolio_value': 10.5,
    'profit_loss': 0.2,
    'timestamp': datetime.utcnow(),
    'trade_count': 5,
    'gas_cost': 0.01
})

# Get performance metrics
metrics = await performance_analyzer.get_performance_metrics(timeframe="30d")
drawdown = await performance_analyzer.get_drawdown_analysis(timeframe="30d")

# Add benchmark data for comparison
await performance_analyzer.add_benchmark_data("ETH", {
    'values': [1500, 1550, 1600, 1580, 1620],
    'timestamps': [
        datetime.utcnow() - timedelta(days=4),
        datetime.utcnow() - timedelta(days=3),
        datetime.utcnow() - timedelta(days=2),
        datetime.utcnow() - timedelta(days=1),
        datetime.utcnow()
    ]
})

# Compare against benchmark
benchmark_comparison = await performance_analyzer.benchmark_performance("ETH", timeframe="7d")
```

## Trade Journaling

The `TradingJournal` class provides detailed trade logging and analysis:

- Detailed trade logging
- Trade categorization and tagging
- Trade outcome analysis
- Learning insights extraction

```python
from arbitrage_bot.core.analytics import create_trading_journal

# Initialize trading journal
trading_journal = await create_trading_journal()

# Log a trade
await trading_journal.log_trade({
    'token_in': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',  # UNI (checksummed)
    'token_out': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH (checksummed)
    'amount_in': 10.0,
    'amount_out': 0.05,
    'profit': 0.02,
    'gas_cost': 0.005,
    'timestamp': datetime.utcnow(),
    'dexes': ['uniswap', 'sushiswap'],
    'path': ['0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'],
    'category': 'profitable',
    'tags': ['high_profit', 'gas_efficient'],
    'notes': 'Good arbitrage opportunity between Uniswap and Sushiswap'
})

# Get trades with filtering
trades = await trading_journal.get_trades(
    timeframe="24h",
    category="profitable",
    tags=["high_profit"],
    success_only=True,
    limit=10
)

# Analyze trade outcomes
outcomes = await trading_journal.analyze_trade_outcomes(timeframe="7d")

# Extract learning insights
insights = await trading_journal.extract_learning_insights(timeframe="30d")
```

## Market Analysis

The `MarketAnalyzer` class provides sophisticated market analysis:

- Market trend detection
- Correlation analysis between tokens
- Volatility forecasting
- Liquidity depth analysis

```python
from arbitrage_bot.core.analytics.market_analyzer import MarketAnalyzer

# Initialize market analyzer
market_analyzer = MarketAnalyzer()
await market_analyzer.initialize()

# Track price data
await market_analyzer.track_price(
    token_address='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH (checksummed)
    price_data={
        'price': 1600.0,
        'timestamp': datetime.utcnow(),
        'source': 'uniswap'
    }
)

# Track liquidity data
await market_analyzer.track_liquidity(
    token_address='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH (checksummed)
    liquidity_data={
        'liquidity': 5000000.0,
        'timestamp': datetime.utcnow(),
        'dex': 'uniswap',
        'pool_address': '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640'  # ETH/USDC pool
    }
)

# Detect market trend
trend = await market_analyzer.detect_market_trend(
    token_address='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    timeframe="24h"
)

# Analyze token correlation
correlation = await market_analyzer.analyze_token_correlation(
    token_addresses=[
        '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH
        '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984',  # UNI
        '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'   # USDC
    ],
    timeframe="7d"
)

# Forecast volatility
volatility = await market_analyzer.forecast_volatility(
    token_address='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    timeframe="7d"
)
```

## Alerting System

The `AlertSystem` class provides alerting capabilities:

- Threshold-based alerts
- Anomaly detection alerts
- Predictive alerts
- Notification delivery through multiple channels

```python
from arbitrage_bot.core.analytics import create_alert_system

# Initialize alert system with configuration
alert_system = await create_alert_system({
    'alert_channels': ['log', 'email'],
    'alert_thresholds': {
        'profit': {
            'warning': {'operator': '<', 'value': 0.01},
            'error': {'operator': '<', 'value': 0}
        },
        'gas_cost': {
            'warning': {'operator': '>', 'value': 0.05}
        }
    },
    'email': {
        'recipients': ['alerts@example.com']
    }
})

# Add a custom alert
await alert_system.add_alert(
    alert_type="custom",
    message="Unusual market activity detected",
    severity="warning",
    data={'token': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'price_change': -5.2}
)

# Check threshold alerts
await alert_system.check_threshold_alerts({
    'profit': 0.005,
    'gas_cost': 0.06
})

# Check for anomalies
await alert_system.check_anomaly_alerts(
    metric_name="gas_price",
    current_value=120,
    historical_values=[80, 85, 82, 78, 83, 81, 79, 84, 82, 80]
)

# Get alerts with filtering
alerts = await alert_system.get_alerts(
    alert_type="threshold",
    severity="warning",
    start_time=datetime.utcnow() - timedelta(days=1),
    limit=10
)

# Get alert summary
summary = await alert_system.get_alert_summary()
```

## Integration with Existing System

To integrate these components with the existing analytics system:

```python
from arbitrage_bot.core.analytics import create_analytics_system
from arbitrage_bot.core.analytics import create_profit_tracker
from arbitrage_bot.core.analytics import create_trading_journal
from arbitrage_bot.core.analytics import create_alert_system
from arbitrage_bot.core.analytics.market_analyzer import MarketAnalyzer
from arbitrage_bot.core.analytics.performance_analyzer import PerformanceAnalyzer

async def initialize_analytics():
    # Create core components
    analytics_system = await create_analytics_system()
    profit_tracker = await create_profit_tracker()
    trading_journal = await create_trading_journal()
    alert_system = await create_alert_system()
    
    # Create additional components
    market_analyzer = MarketAnalyzer()
    await market_analyzer.initialize()
    
    performance_analyzer = PerformanceAnalyzer()
    await performance_analyzer.initialize()
    
    # Return all components
    return {
        'analytics_system': analytics_system,
        'profit_tracker': profit_tracker,
        'trading_journal': trading_journal,
        'alert_system': alert_system,
        'market_analyzer': market_analyzer,
        'performance_analyzer': performance_analyzer
    }
```

## Example Usage

See the `examples/advanced_analytics_example.py` file for a complete example of how to use these components together.

## Best Practices

1. **Initialize components at startup**: Initialize all analytics components when your application starts to ensure they're ready to track data.

2. **Track data in real-time**: Log trades and performance metrics as they happen to ensure accurate analysis.

3. **Use appropriate timeframes**: Different timeframes provide different insights. Use shorter timeframes (1h, 24h) for immediate feedback and longer timeframes (7d, 30d) for trend analysis.

4. **Set meaningful alert thresholds**: Configure alert thresholds based on your risk tolerance and performance expectations.

5. **Regularly review insights**: Regularly review the learning insights from the trading journal to improve your arbitrage strategies.

6. **Benchmark against market**: Use the performance analyzer's benchmarking capabilities to compare your performance against relevant market indices.

7. **Monitor liquidity depth**: Use the market analyzer to monitor liquidity depth across DEXes to identify the best opportunities.

8. **Implement circuit breakers**: Use the alert system to implement circuit breakers that can pause trading if certain conditions are met.

## Configuration Options

Each component accepts a configuration dictionary that can be used to customize its behavior. Common configuration options include:

- `storage_dir`: Directory for storing analytics data
- `cache_ttl`: Time-to-live for cached data (in seconds)
- `alert_channels`: Notification channels for alerts
- `alert_thresholds`: Threshold values for different metrics
- `anomaly_sensitivity`: Sensitivity for anomaly detection
- `report_formats`: Supported formats for report generation

Refer to each component's documentation for specific configuration options.