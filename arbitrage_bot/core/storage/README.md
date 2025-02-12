# Storage System

The Storage system provides persistent data storage with schema validation, backup management, and integration with the memory bank cache. It includes a factory pattern for creating pre-configured storage managers and a central hub for easy access to all storage components.

## Features

- JSON-based persistent storage
- Schema validation with JSON Schema
- Automatic backup management
- Data integrity with checksum validation
- Version tracking with metadata
- Memory bank cache integration
- Error handling and recovery
- Factory pattern for storage creation
- Central storage hub for organization
- Pre-defined schemas for common data types

## Directory Structure

```
storage/
├── data/          # Primary data storage
├── backups/       # Backup files
├── metadata/      # Storage metadata
├── schemas/       # JSON schemas
└── __init__.py    # Core implementation
```

## Quick Start

```python
from arbitrage_bot.core.memory import MemoryBank
from arbitrage_bot.core.storage.factory import create_storage_hub

# Create memory bank for caching
memory = MemoryBank()

# Create storage hub with all managers
storage = create_storage_hub(memory_bank=memory)

# Store trade data (automatically validated against TRADE_SCHEMA)
trade = {
    "id": "trade_1",
    "timestamp": 1675432800,
    "pair": "ETH/USDC",
    "dex": "uniswap",
    "amount": 1.5,
    "price": 1850.75,
    "side": "buy",
    "status": "completed"
}
storage.trades.store("trade_1", trade)

# Store opportunity data
opportunity = {
    "id": "opp_1",
    "timestamp": 1675432800,
    "pair": "ETH/USDC",
    "buy_dex": "uniswap",
    "sell_dex": "sushiswap",
    "buy_price": 1850.75,
    "sell_price": 1852.50,
    "amount": 1.5,
    "profit": 2.625,
    "gas_estimate": 0.5,
    "net_profit": 2.125,
    "executed": False
}
storage.opportunities.store("opp_1", opportunity)

# Store market data
market_data = {
    "timestamp": 1675432800,
    "pair": "ETH/USDC",
    "dex": "uniswap",
    "price": 1850.75,
    "liquidity": 1000000,
    "volume_24h": 5000000
}
storage.market_data.store("eth_usdc_uni", market_data)

# Retrieve data
trade = storage.trades.retrieve("trade_1")
opportunity = storage.opportunities.retrieve("opp_1")
market_data = storage.market_data.retrieve("eth_usdc_uni")

# Define a schema for validation
trade_schema = {
    "type": "object",
    "properties": {
        "timestamp": {"type": "number"},
        "pair": {"type": "string"},
        "amount": {"type": "number"},
        "price": {"type": "number"},
        "side": {"type": "string", "enum": ["buy", "sell"]}
    },
    "required": ["timestamp", "pair", "amount", "price", "side"]
}

# Store data with schema validation
trade_data = {
    "timestamp": 1675432800,
    "pair": "ETH/USDC",
    "amount": 1.5,
    "price": 1850.75,
    "side": "buy"
}

try:
    metadata = storage.store("trade_1", trade_data, schema=trade_schema)
    print(f"Stored at: {metadata.created_at}")
    print(f"Schema version: {metadata.schema_version}")
    print(f"Backup path: {metadata.backup_path}")
except ValidationError as e:
    print(f"Validation failed: {e}")

# Retrieve data with checksum validation
try:
    data = storage.retrieve("trade_1")
    print(f"Retrieved trade: {data}")
except ValidationError as e:
    print(f"Data integrity check failed: {e}")

# List available backups
backups = storage.list_backups("trade_1")
print(f"Available backups: {backups}")

# Restore from backup
if backups:
    try:
        metadata = storage.restore_backup("trade_1", backups[0])
        print(f"Restored from backup at {metadata.updated_at}")
    except StorageError as e:
        print(f"Restore failed: {e}")

# Get metadata
metadata = storage.get_metadata("trade_1")
if metadata:
    print(f"Created: {metadata.created_at}")
    print(f"Last updated: {metadata.updated_at}")
    print(f"Schema version: {metadata.schema_version}")

# List all stored keys
keys = storage.list_keys()
print(f"Stored items: {keys}")

# Delete with backup retention
storage.delete("trade_1", keep_backups=True)
```

## Storage Components

### StorageManager

Base storage class with core functionality:

```python
from arbitrage_bot.core.storage import StorageManager

# Create standalone storage manager
storage = StorageManager(base_path="data/custom", schema_version="1.0.0")

# Store with schema validation
storage.store("key", data, schema=my_schema)

# Retrieve with validation
data = storage.retrieve("key", validate=True)

# List and restore backups
backups = storage.list_backups("key")
storage.restore_backup("key", backups[0])
```

### StorageFactory

Creates pre-configured storage managers:

```python
from arbitrage_bot.core.storage.factory import StorageFactory

factory = StorageFactory(base_path="data", memory_bank=memory)

# Create specialized storage managers
trade_storage = factory.create_trade_storage()
market_storage = factory.create_market_data_storage()
config_storage = factory.create_config_storage()
```

### StorageHub

Central access point for all storage managers:

```python
from arbitrage_bot.core.storage.factory import StorageHub

hub = StorageHub(base_path="data", memory_bank=memory)

# Access different storage types
hub.trades.store("trade_1", trade_data)
hub.opportunities.store("opp_1", opportunity_data)
hub.market_data.store("market_1", market_data)
hub.config.store("settings", config_data)
hub.performance.store("metrics", performance_data)
hub.errors.store("error_1", error_data)
hub.health.store("status", health_data)
```

## Error Handling

The system provides several error types for specific scenarios:

- `StorageError`: Base class for storage-related errors
- `ValidationError`: Raised when schema validation fails
- `SchemaError`: Raised when schema parsing/loading fails
- `BackupError`: Raised when backup operations fail

Example error handling:

```python
try:
    storage.trades.store("trade_1", invalid_trade)
except ValidationError as e:
    logger.error(f"Trade validation failed: {e}")
    # Handle invalid trade data
except BackupError as e:
    logger.error(f"Backup creation failed: {e}")
    # Handle backup failure
except StorageError as e:
    logger.error(f"Storage operation failed: {e}")
    # Handle general storage errors
```

Example error handling:

```python
try:
    storage.store("trade_1", invalid_data, schema=trade_schema)
except ValidationError as e:
    print(f"Data validation failed: {e}")
except BackupError as e:
    print(f"Backup creation failed: {e}")
except StorageError as e:
    print(f"Storage operation failed: {e}")
```

## Memory Bank Integration

When initialized with a MemoryBank instance, the storage system will:

1. Use the memory bank as a fast cache layer
2. Automatically update the cache on writes
3. Check the cache first on reads
4. Maintain version history in the memory bank
5. Clear cache entries when data is deleted

This integration provides:
- Faster access to frequently used data
- Reduced disk I/O
- Automatic cache invalidation
- Version tracking with comments

## Backup Management

The system maintains backups with these features:

- Automatic backup creation on updates
- Configurable backup retention
- Timestamp-based backup identification
- Backup restoration with validation
- Backup listing and management

## Schema Validation

JSON Schema validation ensures data integrity:

- Schema storage alongside data
- Validation on write operations
- Schema version tracking
- Support for complex schemas
- Custom error messages

## Best Practices

1. Use the StorageHub for organized access to all storage types
2. Always provide schemas for critical data
3. Use meaningful keys for better organization
4. Handle errors appropriately
5. Keep backups for important data
6. Monitor storage space usage
7. Use memory bank integration for performance
8. Validate data integrity on retrieval
9. Clean up old backups periodically
10. Use type hints and docstrings for better code clarity

## Schema Management

Pre-defined schemas are available in `schemas.py`:

- `TRADE_SCHEMA`: For trade execution data
- `OPPORTUNITY_SCHEMA`: For arbitrage opportunities
- `MARKET_DATA_SCHEMA`: For price and liquidity data
- `CONFIG_SCHEMA`: For bot configuration
- `PERFORMANCE_SCHEMA`: For performance metrics
- `ERROR_SCHEMA`: For error logging
- `HEALTH_SCHEMA`: For system health monitoring

Custom schemas can be created following the JSON Schema specification.
