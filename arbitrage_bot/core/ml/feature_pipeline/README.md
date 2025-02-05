# ML Feature Pipeline

A scalable and flexible pipeline for real-time and batch feature processing, designed for ML-based arbitrage detection.

## Features

- Hybrid architecture combining real-time and batch processing
- Configurable feature sets for different use cases
- Comprehensive feature validation
- Performance monitoring
- Automatic feature expiry
- Easy integration with ML models

## Architecture

### 1. Real-time Features
- Gas prices and trends
- Liquidity metrics
- Market activity
- Network status

### 2. Batch Features
- Technical indicators
- Market patterns
- Cross-metric correlations
- Volatility metrics

### 3. Feature Sets
- Minimal: Essential features for basic operation
- Standard: Common features for normal operation
- Full: Complete feature set for advanced analysis

## Quick Start

```python
from arbitrage_bot.core.ml.feature_pipeline import FeaturePipeline

# Initialize pipeline
pipeline = FeaturePipeline(data_coordinator, config)
await pipeline.start()

# Get real-time features
features = await pipeline.get_features('minimal')
print(f"Gas Price: {features['gas']['base_fee']}")

# Get ML-ready feature vector
X, feature_names = await pipeline.get_feature_vector('full')
prediction = model.predict(X.reshape(1, -1))
```

## Configuration

The pipeline uses YAML configuration files. See `config/default_config.yaml` for a complete example.

```yaml
real_time:
  update_interval: 1  # seconds
  feature_groups:
    gas:
      enabled: true
      metrics: [base_fee, priority_fee]

batch:
  update_interval: 300  # seconds
  history_hours: 24
  feature_groups:
    technical:
      enabled: true
      indicators: [rsi, bollinger_bands]
```

## Feature Groups

### Real-time Features

1. Gas Metrics
   - Base fee
   - Priority fee
   - Block utilization
   - Gas price trends

2. Liquidity Metrics
   - Pool reserves
   - Trading volume
   - Price impact
   - Utilization rates

3. Market Metrics
   - Network load
   - Pending transactions
   - Competition level
   - Market activity

### Batch Features

1. Technical Indicators
   - Moving averages
   - RSI
   - Bollinger Bands
   - Volume profiles

2. Market Patterns
   - Trend strength
   - Mean reversion
   - Momentum
   - Volatility regimes

3. Correlation Analysis
   - Gas-liquidity correlation
   - Gas-volume correlation
   - Cross-pool correlations

4. Volatility Metrics
   - Standard deviation
   - Skewness
   - Kurtosis
   - Value at Risk

## Usage Examples

### 1. Basic Usage

```python
# Initialize pipeline
pipeline = FeaturePipeline(data_coordinator, config)
await pipeline.start()

# Get real-time features
features = await pipeline.get_features('minimal')

# Get batch features
batch_features = await pipeline.get_features('full')

# Stop pipeline
await pipeline.stop()
```

### 2. ML Model Integration

```python
# Get feature vector for ML model
X, feature_names = await pipeline.get_feature_vector('full')

# Make prediction
prediction = model.predict(X.reshape(1, -1))

# Get feature importance
importance = dict(zip(feature_names, model.feature_importances_))
```

### 3. Custom Feature Sets

```python
# Define custom feature set in config
config['feature_sets']['custom'] = {
    'groups': ['gas', 'technical'],
    'update_interval': 1
}

# Get custom features
features = await pipeline.get_features('custom')
```

### 4. Performance Monitoring

```python
# Monitor pipeline performance
while True:
    stats = pipeline.get_performance_stats()
    print(f"Computation Time: {stats['computation_time']['mean']:.3f}s")
    await asyncio.sleep(60)
```

## Best Practices

1. Feature Selection
   - Start with minimal feature set
   - Add features gradually
   - Monitor feature importance
   - Remove unused features

2. Performance Optimization
   - Adjust update intervals
   - Use appropriate feature sets
   - Monitor resource usage
   - Enable feature expiry

3. Data Quality
   - Enable validation
   - Monitor error rates
   - Set appropriate thresholds
   - Handle missing data

4. Scaling Considerations
   - Use batch processing for complex features
   - Adjust history windows
   - Monitor memory usage
   - Configure backup storage

## Testing

Run the test suite:

```bash
pytest arbitrage_bot/core/ml/feature_pipeline/tests/
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License - see LICENSE file for details