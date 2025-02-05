# Data Collection System

A modular and extensible system for collecting, processing, and storing blockchain and DEX data for ML-based arbitrage detection.

## Features

- Real-time data collection from blockchain and DEXs
- Configurable collection intervals and metrics
- Data normalization and feature extraction
- Time-series data storage
- Monitoring and health checks
- Extensible processing pipeline

## Components

### 1. Collectors

- **NetworkDataCollector**: Collects blockchain metrics
  - Gas prices
  - Block utilization
  - Network load
  - Transaction metrics

- **PoolDataCollector**: Collects DEX pool data
  - Reserves
  - Volume
  - Price impact
  - Liquidity metrics

### 2. Processors

- **DataNormalizer**: Normalizes raw data
  - Standard scaling
  - Min-max scaling
  - Rolling statistics

- **FeatureExtractor**: Extracts ML features
  - Time-based features
  - Technical indicators
  - Cross-metric features

### 3. Storage

- **TimeSeriesStorage**: Stores collected data
  - SQLite backend
  - Configurable retention
  - Data compression
  - Backup support

## Installation

```bash
# From project root
pip install -e .
```

## Quick Start

```python
from arbitrage_bot.core.data_collection.coordinator import DataCollectionCoordinator

# Initialize system
coordinator = DataCollectionCoordinator(config)
await coordinator.initialize(web3_manager, dex_manager)

# Start collection
await coordinator.start()

# Get recent data
data = await coordinator.get_recent_data(minutes=5)
print(f"Collected {len(data)} data points")
```

## Configuration

The system uses YAML configuration files. See `config/default_config.yaml` for a complete example.

```yaml
collectors:
  network:
    enabled: true
    interval_seconds: 1
    metrics:
      base_fee:
        enabled: true
        priority: 1
  
  pool:
    enabled: true
    interval_seconds: 5
    pools:
      - dex: "uniswap_v3"
        pairs: ["WETH/USDC"]
```

## Extending the System

### 1. Custom Collectors

```python
from arbitrage_bot.core.data_collection.base import DataCollector

class MyCollector(DataCollector):
    async def collect(self) -> Dict[str, Any]:
        # Implement collection logic
        return data
        
    async def validate_data(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        # Implement validation logic
        return is_valid, error_message
```

### 2. Custom Processors

```python
from arbitrage_bot.core.data_collection.base import DataProcessor

class MyProcessor(DataProcessor):
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Implement processing logic
        return processed_data
```

### 3. Custom Storage

```python
from arbitrage_bot.core.data_collection.base import DataStorage

class MyStorage(DataStorage):
    async def store(self, data: Dict[str, Any]):
        # Implement storage logic
        
    async def retrieve(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Implement retrieval logic
        return data
```

## Usage Examples

### 1. Basic Collection

```python
# Load configuration
with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize system
coordinator = DataCollectionCoordinator(config)
await coordinator.initialize(web3_manager, dex_manager)

# Start collection
await coordinator.start()

# Monitor system
while True:
    status = await coordinator.get_status()
    print(f"System Status: {status}")
    await asyncio.sleep(60)
```

### 2. Custom Processing Pipeline

```python
# Add custom processor
class MyProcessor(DataProcessor):
    async def process(self, data):
        processed = await super().process(data)
        processed['custom_feature'] = calculate_feature(processed)
        return processed

coordinator.processors['custom'] = MyProcessor(config)
```

### 3. Data Analysis

```python
# Get recent data
network_data = await coordinator.get_recent_data('network', minutes=5)
pool_data = await coordinator.get_recent_data('pool', minutes=5)

# Analyze patterns
for data_point in network_data:
    analyze_metrics(data_point)
```

## Testing

Run the test suite:

```bash
pytest arbitrage_bot/core/data_collection/tests/
```

## Monitoring

The system includes built-in monitoring:

```python
# Get system status
status = await coordinator.get_status()

# Check component health
for collector_name, collector_status in status['collectors'].items():
    if collector_status['status'] != 'running':
        print(f"Warning: {collector_name} not running!")

# Check recent data
recent_data = await coordinator.get_recent_data(minutes=1)
if not recent_data:
    print("Warning: No recent data collected!")
```

## Best Practices

1. **Configuration**
   - Use environment-specific configs
   - Validate all config values
   - Use reasonable intervals

2. **Data Collection**
   - Handle network errors gracefully
   - Implement proper backoff
   - Validate collected data

3. **Processing**
   - Keep processors focused
   - Handle missing data
   - Log processing errors

4. **Storage**
   - Regular backups
   - Data cleanup
   - Monitor storage usage

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License - see LICENSE file for details