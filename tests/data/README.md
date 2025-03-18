# Test Data and Fixtures

This directory contains test data and fixtures used across the test suite.

## Configuration Parameters

### test_config.json

#### Test Environment
- `network`: Target test network
- `rpc_url`: RPC endpoint URL
- `chain_id`: Network chain ID
- `block_time`: Average block time in seconds
- `confirmation_blocks`: Required block confirmations

#### Test Parameters
- `max_slippage_bps`: Maximum allowed slippage in basis points (1 bps = 0.01%)
- `min_profit_eth`: Minimum required profit in ETH
- `gas_limit`: Maximum gas limit per transaction
- `priority_fee_gwei`: Priority fee in GWEI
- `max_hops`: Maximum number of hops in arbitrage path
- `timeout_seconds`: Operation timeout in seconds
- `retry_attempts`: Number of retry attempts
- `retry_delay_seconds`: Delay between retries in seconds

#### Test Monitoring
- `log_level`: Logging verbosity level
- `metrics_interval_seconds`: Metrics collection interval in seconds
- `health_check_interval_seconds`: Health check interval in seconds
- `alert_thresholds`:
  - `high_slippage_bps`: High slippage alert threshold in basis points
  - `high_gas_limit`: High gas usage alert threshold
  - `low_profit_eth`: Low profit alert threshold in ETH
  - `high_latency_ms`: High latency alert threshold in milliseconds

#### Test Mocks
- `block_number`: Mock block number
- `gas_price_gwei`: Mock gas price in GWEI
- `timestamp`: Mock timestamp
- `base_fee_gwei`: Mock base fee in GWEI

### monitoring_sample.json

Sample monitoring data that includes:
- System health metrics
- DEX status information
- Arbitrage statistics
- Active trading pairs
- Error and warning logs

## Usage

```python
from tests.data import (
    get_monitoring_data,
    get_test_config,
    get_dex_response,
    get_sample_transactions
)

# Load test configuration
config = get_test_config()

# Get monitoring data
monitoring = get_monitoring_data()

# Get specific timestamp data
data = get_monitoring_data("20250111_042202")

# Get mock DEX response
dex_data = get_dex_response("baseswap")

# Get sample transactions
transactions = get_sample_transactions()
```

## Adding New Test Data

1. Create a new JSON file in this directory
2. Update `__init__.py` with any new loading functions
3. Add documentation in this README
4. Update relevant test files to use the new data

## File Organization

```
tests/data/
├── __init__.py           # Data loading functions
├── README.md            # This documentation
├── test_config.json     # Test configuration
├── monitoring_*.json    # Monitoring data samples
└── dex_response_*.json  # DEX response samples