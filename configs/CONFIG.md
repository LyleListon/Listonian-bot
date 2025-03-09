# Configuration Documentation

## Network Settings

### network.rpc_url
- **Type**: string
- **Default**: "http://localhost:8545"
- **Description**: RPC endpoint URL for blockchain interaction
- **Note**: Override this in environment-specific config or via BASE_RPC_URL environment variable

### network.chain_id
- **Type**: integer
- **Default**: 8453
- **Description**: Network chain ID (8453 for Base)
- **Note**: Must match the network of the RPC endpoint

### network.retry_count
- **Type**: integer
- **Default**: 3
- **Description**: Number of retry attempts for failed RPC calls
- **Range**: 1-10

## Trading Parameters

### trading.min_profit
- **Type**: number
- **Default**: 5.0
- **Description**: Minimum profit threshold in base currency (USDC)
- **Note**: Trades with lower potential profit will be ignored

### trading.gas_limit
- **Type**: integer
- **Default**: 350000
- **Description**: Maximum gas limit for transactions
- **Note**: Should be set based on network conditions

### trading.slippage
- **Type**: number
- **Default**: 0.5
- **Description**: Slippage tolerance percentage
- **Range**: 0-100

### trading.max_trades_per_block
- **Type**: integer
- **Default**: 3
- **Description**: Maximum number of trades to execute in a single block
- **Note**: Prevents overloading and ensures gas efficiency

### trading.pairs
- **Type**: array
- **Description**: Trading pair configurations
- **Fields**:
  - token0: First token in pair
  - token1: Second token in pair
  - min_amount: Minimum trade amount
  - max_amount: Maximum trade amount

## Monitoring Configuration

### monitoring.log_level
- **Type**: string
- **Default**: "INFO"
- **Options**: "DEBUG", "INFO", "WARNING", "ERROR"
- **Description**: Logging verbosity level

### monitoring.metrics_enabled
- **Type**: boolean
- **Default**: true
- **Description**: Enable/disable metrics collection

### monitoring.alert_threshold
- **Type**: number
- **Default**: 90.0
- **Description**: Threshold for system metric alerts
- **Note**: Alerts triggered when metrics exceed this value

### monitoring.collection_interval
- **Type**: integer
- **Default**: 5000
- **Description**: Interval for metrics collection in milliseconds

### monitoring.log_rotation
- **Type**: object
- **Description**: Log file rotation settings
- **Fields**:
  - max_size: Maximum log file size
  - backup_count: Number of backup files to keep

## Dashboard Configuration

### dashboard.port
- **Type**: integer
- **Default**: 5001
- **Description**: HTTP port for dashboard web interface
- **Range**: 1024-65535

### dashboard.websocket_port
- **Type**: integer
- **Default**: 8772
- **Description**: WebSocket server port for real-time updates
- **Range**: 1024-65535

### dashboard.update_interval
- **Type**: integer
- **Default**: 1000
- **Description**: UI update interval in milliseconds

### dashboard.auth_enabled
- **Type**: boolean
- **Default**: false
- **Description**: Enable/disable dashboard authentication

### dashboard.cors
- **Type**: object
- **Description**: CORS settings for dashboard API
- **Fields**:
  - enabled: Enable/disable CORS
  - origins: Allowed origin URLs

### dashboard.rate_limit
- **Type**: object
- **Description**: API rate limiting configuration
- **Fields**:
  - enabled: Enable/disable rate limiting
  - max_requests: Maximum requests per window
  - window_seconds: Time window in seconds

Last Updated: 2025-02-10