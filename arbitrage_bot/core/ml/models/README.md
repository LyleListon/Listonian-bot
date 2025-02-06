# ML Models

Online learning LSTM models for real-time gas price and liquidity prediction.

## Features

- Online learning with continuous model updates
- Uncertainty estimation for predictions
- Performance monitoring and early stopping
- Model persistence and versioning
- GPU acceleration support
- Memory-efficient experience replay

## Architecture

### 1. Base Model (OnlineLSTM)
- LSTM layers with skip connections
- Dropout for regularization
- Gaussian NLL loss for uncertainty
- Experience replay buffer
- Gradient clipping

### 2. Specialized Models
- GasPricePredictor
  * Gas price and volatility prediction
  * Custom gas-specific features
  * Price-weighted loss function

- LiquidityPredictor
  * Multi-output prediction (liquidity, volume, impact)
  * Custom liquidity features
  * Component-weighted loss function

### 3. Model Manager
- Coordinates model updates
- Handles feature pipeline integration
- Monitors performance
- Manages model persistence

## Quick Start

```python
from arbitrage_bot.core.ml.models import ModelManager

# Initialize manager
manager = ModelManager(feature_pipeline, config)
await manager.start()

# Get gas price prediction
prediction = await manager.predict_gas_price()
print(f"Gas Price: {prediction['predicted_price']}")
print(f"Uncertainty: ±{prediction['uncertainty']}")
print(f"Confidence: {prediction['confidence']:.2%}")

# Get liquidity prediction
prediction = await manager.predict_liquidity()
print(f"Liquidity: {prediction['liquidity']['total']}")
print(f"Volume: {prediction['liquidity']['volume']}")
print(f"Impact: {prediction['liquidity']['impact']:.2%}")
```

## Configuration

The models use YAML configuration files. See `config/default_config.yaml` for a complete example.

```yaml
model_configs:
  gas:
    input_size: 32
    hidden_size: 128
    num_layers: 2
    learning_rate: 0.001
    batch_size: 32
    
  liquidity:
    input_size: 48
    hidden_size: 256
    num_layers: 3
    learning_rate: 0.0005
    batch_size: 64
```

## Model Components

### 1. LSTM Architecture

```python
class OnlineLSTM(nn.Module):
    def __init__(self, config):
        self.lstm = nn.LSTM(
            input_size=config['input_size'],
            hidden_size=config['hidden_size'],
            num_layers=config['num_layers']
        )
        self.fc1 = nn.Linear(hidden_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, output_size)
```

### 2. Online Learning

```python
# Update model with new data
features = feature_pipeline.get_features()
target = get_current_price()
model.update(features, target)

# Get prediction with uncertainty
prediction, uncertainty = model.predict(features)
```

### 3. Performance Monitoring

```python
# Get model statistics
stats = model.get_performance_stats()
print(f"Loss: {stats['loss_mean']:.4f}")
print(f"Updates: {stats['updates']}")
```

## Extending the Models

### 1. Custom Predictor

```python
from arbitrage_bot.core.ml.models import OnlineLSTM

class CustomPredictor(OnlineLSTM):
    def __init__(self, config):
        super().__init__(config)
        self.custom_weight = config.get('custom_weight', 1.0)
        
    def update(self, features, target):
        # Add custom features
        features = self._add_custom_features(features)
        super().update(features, target)
```

### 2. Custom Loss Function

```python
class CustomLoss(nn.Module):
    def forward(self, pred, target, uncertainty):
        # Implement custom loss
        return loss
```

### 3. Custom Features

```python
def _add_custom_features(self, features):
    # Calculate momentum
    momentum = features[-1] - features[0]
    
    # Add to features
    return np.concatenate([features, momentum])
```

## Best Practices

1. Model Configuration
   - Start with small models
   - Adjust batch size based on data
   - Monitor memory usage
   - Enable early stopping

2. Feature Engineering
   - Normalize inputs
   - Add domain-specific features
   - Track feature importance
   - Remove unused features

3. Training
   - Monitor loss curves
   - Check prediction uncertainty
   - Validate performance
   - Save checkpoints

4. Production
   - Enable GPU if available
   - Monitor resource usage
   - Set up alerting
   - Regular backups

## Testing

Run the test suite:

```bash
pytest arbitrage_bot/core/ml/models/tests/
```

## Performance Tips

1. GPU Acceleration
   ```python
   # Enable GPU
   device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
   model.to(device)
   ```

2. Memory Management
   ```python
   # Configure memory limits
   config['memory_size'] = 10000
   config['batch_size'] = 32
   ```

3. Feature Selection
   ```python
   # Track feature importance
   config['track_feature_importance'] = True
   ```

4. Model Persistence
   ```python
   # Enable saving
   config['persistence']['enabled'] = True
   config['persistence']['interval'] = 3600  # seconds
   ```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License - see LICENSE file for details