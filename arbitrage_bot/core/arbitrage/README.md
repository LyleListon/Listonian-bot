# Aggressive Arbitrage Detection System

ML-powered arbitrage detection system optimized for aggressive trading strategies.

## Features

- Real-time opportunity detection
- ML-based predictions for gas and liquidity
- Dynamic position sizing
- Advanced risk management
- Performance monitoring
- High-frequency trading support

## Architecture

### 1. Arbitrage Detector
- Real-time opportunity detection
- Path finding algorithms
- Profit calculation
- Execution timing
- Position sizing

### 2. Risk Manager
- Dynamic risk adjustment
- Position sizing
- Exposure tracking
- Performance monitoring
- Drawdown management

### 3. ML Integration
- Gas price predictions
- Liquidity predictions
- Uncertainty estimation
- Confidence scoring

## Quick Start

```python
from arbitrage_bot.core.arbitrage import AggressiveArbitrageDetector

# Initialize detector
detector = AggressiveArbitrageDetector(model_manager, dex_manager, config)
await detector.start()

# Monitor opportunities
status = detector.get_status()
print(f"Active Opportunities: {status['opportunities']}")
print(f"Active Trades: {status['active_trades']}")

# Check performance
stats = detector.get_performance_stats()
print(f"Total Profit: ${stats['total_profit']}")
print(f"Win Rate: {stats['successful_trades'] / stats['trades_executed']:.2%}")
```

## Configuration

The system uses YAML configuration files. See `config/default_config.yaml` for a complete example.

```yaml
detector:
  min_profit_threshold: 0.001  # 0.1% minimum profit
  risk_tolerance: 0.8         # Aggressive: 0.8 vs Conservative: 0.3
  max_position_size: 100000   # Maximum position size in USD

risk_management:
  max_drawdown: 0.15         # 15% maximum drawdown
  max_exposure: 0.8          # 80% maximum capital exposure
  recovery_threshold: 1.5    # Required recovery factor
```

## Components

### 1. Opportunity Detection

```python
# Get latest predictions
gas_prediction = await model_manager.predict_gas_price()
liquidity_prediction = await model_manager.predict_liquidity()

# Find opportunities
opportunities = await detector._find_opportunities(
    gas_prediction,
    liquidity_prediction
)
```

### 2. Risk Management

```python
# Calculate position size
position_size = risk_manager.calculate_position_size(
    profit_potential=0.01,  # 1% profit
    uncertainty=0.1,
    current_volatility=0.2
)

# Check risk limits
within_limits, reason = risk_manager.check_risk_limits()
```

### 3. Performance Tracking

```python
# Track trade
risk_manager.record_trade(
    trade_id='trade1',
    position_size=10000,
    entry_price=1000,
    profit=100
)

# Get metrics
metrics = risk_manager.get_metrics()
```

## Aggressive Strategy Features

1. Position Sizing
   - Larger positions for high-confidence opportunities
   - Dynamic sizing based on uncertainty
   - Kelly Criterion with aggressive fraction

2. Risk Management
   - Higher risk tolerance
   - Faster reaction to opportunities
   - Dynamic risk adjustment

3. Execution
   - Quick entry and exit
   - Multiple concurrent trades
   - Optimized gas strategies

## Best Practices

1. Configuration
   - Start with small positions
   - Gradually increase risk tolerance
   - Monitor performance closely
   - Set appropriate alerts

2. Risk Management
   - Monitor exposure levels
   - Track drawdown carefully
   - Use stop losses
   - Maintain reserves

3. Performance
   - Track all metrics
   - Monitor win rate
   - Analyze failed trades
   - Regular backups

4. System Health
   - Monitor resource usage
   - Check prediction accuracy
   - Validate opportunities
   - Regular maintenance

## Performance Tips

1. Speed Optimization
   ```python
   # Configure fast updates
   config['detector']['update_interval'] = 0.1  # 100ms
   ```

2. Risk Management
   ```python
   # Configure risk limits
   config['risk_management']['max_exposure'] = 0.8  # 80%
   config['risk_management']['max_drawdown'] = 0.15  # 15%
   ```

3. Position Sizing
   ```python
   # Configure aggressive sizing
   config['detector']['risk_tolerance'] = 0.8
   config['detector']['min_position_size'] = 1000
   ```

4. Monitoring
   ```python
   # Enable detailed monitoring
   config['monitoring']['track_metrics'] = True
   config['monitoring']['save_interval'] = 60
   ```

## Testing

Run the test suite:

```bash
pytest arbitrage_bot/core/arbitrage/tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License - see LICENSE file for details