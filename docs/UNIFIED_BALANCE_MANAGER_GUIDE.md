# Unified Balance Manager Guide

## Overview

The `UnifiedBalanceManager` provides a consolidated solution for token balance management and allocation in the arbitrage bot. It combines functionality from both the `BalanceManager` (for tracking balances) and `BalanceAllocator` (for determining trade sizes) into a single, robust implementation that reduces duplication and improves consistency.

Key improvements:
- Single source of truth for token balances
- Consistent decision-making for trade sizes
- Combined functionality eliminates potential conflicts
- Support for both synchronous and asynchronous operations
- Improved thread safety through proper lock management
- Better error handling and resource management

## Architecture

The Unified Balance Manager consolidates two previously separate components:

```
┌───────────────────────────────────────┐
│       UnifiedBalanceManager           │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │       Balance Tracking          │  │
│  │ (previously BalanceManager)     │  │
│  └─────────────────────────────────┘  │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │       Allocation Logic          │  │
│  │ (previously BalanceAllocator)   │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
           │                  │
           ▼                  ▼
┌────────────────┐  ┌────────────────────┐
│ Legacy Wrapper │  │ Direct Usage       │
│                │  │ (Recommended)      │
└────────────────┘  └────────────────────┘
```

## Migration Guide

### Async Usage (Recommended)

```python
from arbitrage_bot.core.unified_balance_manager import create_unified_balance_manager

async def example_async_usage():
    # Create the web3 manager
    web3_manager = await create_web3_manager()
    
    # Create dex manager (optional)
    dex_manager = await create_dex_manager(web3_manager, config)
    
    # Create and initialize the balance manager
    balance_manager = await create_unified_balance_manager(
        web3_manager, 
        dex_manager, 
        config
    )
    
    # Start balance tracking
    await balance_manager.start()
    
    try:
        # Check a token balance
        eth_balance = await balance_manager.get_balance('ETH')
        
        # Get formatted balance
        formatted_balance = await balance_manager.get_formatted_balance('ETH')
        
        # Get all balances
        all_balances = await balance_manager.get_all_balances()
        
        # Check if balance is sufficient
        is_sufficient = await balance_manager.check_balance('ETH', amount_wei)
        
        # Get allocation range for a token
        min_amount, max_amount = await balance_manager.get_allocation_range(token_address)
        
        # Adjust an amount to be within allocation limits
        adjusted_amount = await balance_manager.adjust_amount_to_limits(token_address, amount)
        
    finally:
        # Clean up resources
        await balance_manager.stop()
```

### Synchronous Usage

```python
from arbitrage_bot.core.unified_balance_manager import create_unified_balance_manager_sync

def example_sync_usage():
    # Create the web3 manager
    web3_manager = create_web3_manager_sync()
    
    # Create the balance manager
    balance_manager = create_unified_balance_manager_sync(web3_manager, None, config)
    
    # Start balance tracking
    balance_manager.start_sync()
    
    try:
        # Check a token balance
        eth_balance = balance_manager.get_balance_sync('ETH')
        
        # Get formatted balance
        formatted_balance = balance_manager.get_formatted_balance_sync('ETH')
        
        # Get all balances
        all_balances = balance_manager.get_all_balances_sync()
        
        # Check if balance is sufficient
        is_sufficient = balance_manager.check_balance_sync('ETH', amount_wei)
        
        # Get allocation range for a token
        min_amount, max_amount = balance_manager.get_allocation_range_sync(token_address)
        
        # Adjust an amount to be within allocation limits
        adjusted_amount = balance_manager.adjust_amount_to_limits_sync(token_address, amount)
        
    finally:
        # Clean up resources
        balance_manager.stop_sync()
```

### Using Legacy Compatibility Wrappers (Not Recommended)

The system provides backward compatibility through wrapper classes that implement the original interfaces:

```python
# Original BalanceManager
from arbitrage_bot.core.balance_manager import create_balance_manager

# Original BalanceAllocator
from arbitrage_bot.core.balance_allocator import create_balance_allocator
```

These modules will emit deprecation warnings to encourage migration to the unified implementation.

## Key Functionality

### Balance Tracking

The balance tracking component periodically updates token balances and provides methods to:

- Retrieve current token balances (raw and formatted)
- Check if balances are sufficient for transactions
- Get all balances at once

### Allocation Logic

The allocation component determines appropriate trade sizes based on:

- Available wallet balance
- Configured minimum and maximum percentages
- Absolute minimum and maximum limits
- Reserve requirements
- Concurrent trade considerations

### Thread Safety

The unified implementation includes thread safety features:

1. Async locks to protect shared resources
2. Atomic operations for state changes
3. Proper handling of concurrent operations

## Configuration

The balance manager uses the following configuration structure:

```json
{
  "dynamic_allocation": {
    "enabled": true,
    "min_percentage": 5,
    "max_percentage": 50,
    "absolute_min_eth": 0.05,
    "absolute_max_eth": 10.0,
    "concurrent_trades": 2,
    "reserve_percentage": 10
  },
  "balance_update_interval": 60,
  "tokens": {
    "ETH": {},
    "WETH": {
      "address": "0x4200000000000000000000000000000000000006",
      "decimals": 18
    },
    "USDC": {
      "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "decimals": 6
    }
  }
}
```

## Resource Management

The UnifiedBalanceManager implements proper resource management:

1. Background tasks are properly tracked and cleaned up
2. Startup and shutdown procedures ensure proper initialization and cleanup
3. Locks prevent concurrent access issues

## Benefits Over Previous Implementation

1. **Eliminates Duplication**: Combined balance tracking and allocation logic eliminates duplicate code.
2. **Consistent State**: Single source of truth for balances prevents inconsistent views.
3. **Thread Safety**: Proper lock management prevents race conditions.
4. **Better Resource Management**: Improved cleanup of background tasks.
5. **Unified Interface**: Single API for all balance operations simplifies usage.

## System Requirements

- Python 3.8+
- Web3.py 5.0+
- Asyncio support