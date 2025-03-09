# Memory Module

The memory module provides functionality for storing and managing arbitrage opportunities and trade results. It serves as a short-term memory bank for the arbitrage bot, enabling analysis of historical data and performance tracking.

## Components

### MemoryBank

The main component that handles storage and retrieval of:
- Arbitrage opportunities
- Trade execution results
- Performance statistics

## Features

- **Configurable Storage Limits**: Control the maximum number of opportunities to store
- **Automatic Cleanup**: Background task removes old data based on configurable age limits
- **Thread-Safe Operations**: Supports concurrent access from multiple components
- **Statistical Analysis**: Provides aggregated statistics on trading performance
- **Error Handling**: Robust error handling with detailed logging

## Usage

### Basic Usage

```python
from arbitrage_bot.core.memory.bank import create_memory_bank

# Create and initialize memory bank
config = {
    "max_opportunities": 1000,    # Maximum opportunities to store
    "cleanup_interval": 3600,     # Cleanup interval in seconds
    "max_age": 86400             # Maximum age of data in seconds
}
memory_bank = await create_memory_bank(config)

# Store opportunities
await memory_bank.store_opportunities(opportunities)

# Store trade result
await memory_bank.store_trade_result(
    opportunity=opportunity,
    success=True,
    net_profit=10.0,
    gas_cost=2.0,
    tx_hash="0x123..."
)

# Get recent opportunities
recent_opps = await memory_bank.get_recent_opportunities(
    max_age=3600,  # Get opportunities from last hour
    limit=10       # Get up to 10 opportunities
)

# Get trade history
history = await memory_bank.get_trade_history(
    max_age=86400,    # Get trades from last 24 hours
    success_only=True # Get only successful trades
)

# Get statistics
stats = await memory_bank.get_statistics()
```

### Configuration

The memory bank accepts the following configuration options:

```python
{
    # Maximum number of opportunities to store
    "max_opportunities": 1000,

    # How often to run cleanup (in seconds)
    "cleanup_interval": 3600,  # 1 hour

    # Maximum age of data before cleanup (in seconds)
    "max_age": 86400,  # 24 hours
}
```

### Statistics

The `get_statistics()` method returns a dictionary with the following metrics:

```python
{
    "opportunities_count": int,   # Number of stored opportunities
    "trades_count": int,         # Total number of trades
    "successful_trades": int,    # Number of successful trades
    "total_profit": float,       # Total profit from successful trades
    "total_gas_cost": float,     # Total gas costs
    "success_rate": float,       # Success rate (0-1)
    "average_profit": float      # Average profit per successful trade
}
```

## Integration

The memory bank is integrated with:
- Opportunity Detector: Stores detected arbitrage opportunities
- Arbitrage Executor: Stores trade execution results
- Analytics System: Provides data for analysis
- Dashboard: Displays historical data and statistics

## Error Handling

The memory bank includes comprehensive error handling:
- Initialization failures are logged and handled gracefully
- Storage operations continue even if some operations fail
- Background cleanup task handles errors without interrupting service
- All errors are logged with appropriate context

## Testing

The memory bank includes a comprehensive test suite:
- Unit tests for all major functionality
- Concurrent operation tests
- Error handling tests
- Cleanup functionality tests

Run tests with:
```bash
pytest tests/test_memory_bank.py
```

## Best Practices

1. Always initialize the memory bank before use
2. Handle cleanup properly by calling cleanup() when shutting down
3. Use appropriate timeouts for data retrieval operations
4. Monitor memory usage and adjust configuration if needed
5. Check initialization status before operations
6. Handle potential exceptions in async operations

## Dependencies

- Python 3.8+
- asyncio
- pytest-asyncio (for testing)
