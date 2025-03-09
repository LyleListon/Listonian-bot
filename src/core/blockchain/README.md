# Blockchain Layer

## Overview
The blockchain layer handles all interactions with the Base network, providing a robust and reliable interface for Web3 operations.

## Components

### Web3 Manager
The `Web3Manager` class provides high-level blockchain interactions:
```python
from src.core.blockchain import Web3Manager

# Initialize manager
manager = Web3Manager(
    url="https://base-mainnet.g.alchemy.com/v2/YOUR-API-KEY",
    chain_id=8453,
    retry_count=3
)

# Connect to network
await manager.connect()

# Get current block
block_number = await manager.get_block_number()

# Send transaction
tx_hash = await manager.send_transaction({
    'to': '0x...',
    'value': 1000000000000000000,  # 1 ETH
})

# Wait for confirmation
receipt = await manager.wait_for_transaction(tx_hash)
```

### Providers
The provider system implements different connection strategies:

#### Base Provider
Abstract base class defining the provider interface:
```python
from src.core.blockchain.providers import BaseProvider

class CustomProvider(BaseProvider):
    async def connect(self) -> None:
        # Implementation
        pass
```

#### HTTP Provider
Default implementation for HTTP/HTTPS connections:
```python
from src.core.blockchain.providers import HttpProvider

provider = HttpProvider(
    url="https://rpc.example.com",
    chain_id=8453,
    retry_count=3
)
```

## Features

### Retry Logic
- Automatic retry for failed requests
- Exponential backoff
- Configurable retry count
- Detailed error logging

### Transaction Management
- Gas estimation
- Gas price management
- Transaction signing
- Receipt waiting
- Confirmation tracking

### Error Handling
- Detailed error messages
- Connection recovery
- Transaction failure handling
- Chain ID validation

## Configuration

### Environment Variables
```env
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR-API-KEY
CHAIN_ID=8453
```

### Settings
```python
# Default retry count
DEFAULT_RETRY_COUNT = 3

# Default transaction timeout (seconds)
DEFAULT_TX_TIMEOUT = 120

# Gas price buffer (multiplier)
GAS_BUFFER = 1.1
```

## Usage Examples

### Basic Connection
```python
from src.core.blockchain import Web3Manager

async def main():
    manager = Web3Manager(
        url="https://base-mainnet.g.alchemy.com/v2/YOUR-API-KEY",
        chain_id=8453
    )
    await manager.connect()
    
    block = await manager.get_block_number()
    print(f"Current block: {block}")
```

### Transaction Sending
```python
async def send_eth(to: str, amount: int):
    tx = {
        'to': to,
        'value': amount,
        'from': manager.provider.web3.eth.default_account,
    }
    
    # Gas will be estimated automatically
    tx_hash = await manager.send_transaction(tx)
    
    # Wait for confirmation
    receipt = await manager.wait_for_transaction(tx_hash)
    return receipt
```

### Error Handling
```python
try:
    await manager.connect()
except ConnectionError as e:
    logger.error(f"Failed to connect: {e}")
    # Handle connection failure
    
try:
    receipt = await manager.wait_for_transaction(tx_hash)
except TimeoutError:
    logger.error("Transaction timed out")
    # Handle timeout
```

## Best Practices

1. Always use the retry mechanism
2. Handle connection failures gracefully
3. Validate chain ID on connection
4. Use appropriate timeouts
5. Monitor gas prices
6. Log all operations
7. Clean up resources

## Dependencies
- web3.py
- asyncio
- logging

Last Updated: 2025-02-10