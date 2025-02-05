# Data Collection Configuration System

## Overview
A flexible configuration system that allows easy modification of:
- Data collectors
- Collection intervals
- Metrics to track
- Processing pipelines
- Storage options

## Configuration Structure

```yaml
# data_collection_config.yaml

# Global Settings
global:
  environment: "production"  # or "development", "testing"
  log_level: "INFO"
  storage:
    type: "timeseries"  # or "relational", "document"
    connection:
      host: "${DB_HOST}"
      port: "${DB_PORT}"
      database: "market_data"

# Network Data Collection
network_collection:
  enabled: true
  interval_seconds: 1
  metrics:
    base_fee:
      enabled: true
      priority: 1
      validation:
        min_value: 0
        max_value: 1000
        required: true
    
    priority_fee:
      enabled: true
      priority: 1
      validation:
        min_value: 0
        max_value: 500
        required: true
    
    block_utilization:
      enabled: true
      priority: 2
      validation:
        min_value: 0
        max_value: 1
        required: true
    
    pending_transactions:
      enabled: true
      priority: 2
      validation:
        min_value: 0
        required: true
    
    network_load:
      enabled: true
      priority: 3
      validation:
        min_value: 0
        max_value: 1
        required: false

# Pool Data Collection
pool_collection:
  enabled: true
  interval_seconds: 5
  pools:
    - dex: "uniswap_v3"
      pairs: ["WETH/USDC", "WETH/DAI"]
      fee_tiers: [500, 3000, 10000]
    - dex: "baseswap"
      pairs: ["WETH/USDC"]
      fee_tiers: [3000]
  
  metrics:
    reserves:
      enabled: true
      priority: 1
      validation:
        min_value: 0
        required: true
    
    volume:
      enabled: true
      priority: 1
      validation:
        min_value: 0
        required: true
    
    price_impact:
      enabled: true
      priority: 2
      validation:
        min_value: 0
        max_value: 1
        required: true
    
    concentration:
      enabled: true
      priority: 2
      validation:
        min_value: 0
        max_value: 1
        required: true
    
    utilization:
      enabled: true
      priority: 3
      validation:
        min_value: 0
        max_value: 1
        required: true

# Data Processing
processing:
  normalizers:
    standard_scaler:
      enabled: true
      metrics: ["base_fee", "priority_fee", "volume"]
    min_max_scaler:
      enabled: true
      metrics: ["block_utilization", "network_load", "concentration"]
    
  feature_extractors:
    gas_features:
      enabled: true
      window_sizes: [10, 30, 60]  # seconds
      features:
        - "mean"
        - "std"
        - "min"
        - "max"
        - "trend"
    
    liquidity_features:
      enabled: true
      window_sizes: [300, 900, 1800]  # seconds
      features:
        - "mean"
        - "std"
        - "volatility"
        - "trend"
        - "concentration"

# Storage Configuration
storage:
  metrics_retention:
    raw_data: "7d"
    processed_features: "30d"
    model_predictions: "90d"
  
  backup:
    enabled: true
    interval: "1d"
    retention: "90d"
  
  compression:
    enabled: true
    algorithm: "lz4"
    min_age: "1d"

# Monitoring
monitoring:
  collectors:
    latency:
      enabled: true
      threshold_ms: 1000
    
    accuracy:
      enabled: true
      metrics: ["gas_prediction", "liquidity_prediction"]
    
    coverage:
      enabled: true
      min_percentage: 95
  
  alerts:
    email:
      enabled: true
      recipients: ["${ALERT_EMAIL}"]
    
    discord:
      enabled: true
      webhook_url: "${DISCORD_WEBHOOK}"
    
    thresholds:
      collection_gap_seconds: 60
      prediction_accuracy: 0.8
      system_health: 0.9
```

## Configuration Management

```python
class ConfigManager:
    """Manage data collection configuration"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
        self.validators = self._init_validators()
        
    def _load_config(self) -> Dict:
        """Load and validate configuration"""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        
        # Validate configuration
        self._validate_config(config)
        
        # Replace environment variables
        config = self._replace_env_vars(config)
        
        return config
        
    def get_collector_config(
        self, 
        collector_name: str
    ) -> Dict:
        """Get configuration for specific collector"""
        if collector_name == 'network':
            return self.config['network_collection']
        elif collector_name == 'pool':
            return self.config['pool_collection']
        raise ValueError(f"Unknown collector: {collector_name}")
        
    def update_collector_config(
        self, 
        collector_name: str,
        updates: Dict
    ):
        """Update collector configuration"""
        if collector_name == 'network':
            self.config['network_collection'].update(updates)
        elif collector_name == 'pool':
            self.config['pool_collection'].update(updates)
        else:
            raise ValueError(f"Unknown collector: {collector_name}")
            
        # Save updated configuration
        self._save_config()
```

## Usage Examples

### 1. Initialize System

```python
# Initialize with configuration
config_manager = ConfigManager('data_collection_config.yaml')

# Create collection system
collection_system = DataCollectionSystem(config_manager)

# Start collection
await collection_system.initialize()
await collection_system.start_collection()
```

### 2. Add New Metric

```python
# Add new network metric
await collection_system.collectors['network'].add_metric(
    'new_metric',
    new_metric_collector_function
)

# Update configuration
config_manager.update_collector_config(
    'network',
    {
        'metrics': {
            'new_metric': {
                'enabled': True,
                'priority': 2,
                'validation': {
                    'min_value': 0,
                    'required': True
                }
            }
        }
    }
)
```

### 3. Add New Pool

```python
# Add new pool to tracking
await collection_system.collectors['pool'].add_pool(
    pool_address='0x...',
    dex_name='new_dex'
)

# Update configuration
config_manager.update_collector_config(
    'pool',
    {
        'pools': [
            {
                'dex': 'new_dex',
                'pairs': ['TOKEN1/TOKEN2'],
                'fee_tiers': [3000]
            }
        ]
    }
)
```

Would you like to start implementing this configuration system or any specific part of it?