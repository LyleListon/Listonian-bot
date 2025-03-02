# Unified Flash Loan Manager Guide

## Overview

The `UnifiedFlashLoanManager` provides a consolidated implementation for flash loan operations in the arbitrage bot. It combines functionality from both the synchronous `FlashLoanManager` and asynchronous `AsyncFlashLoanManager` into a single, robust solution that supports both programming paradigms.

Key improvements:
- Unified codebase that reduces duplication and maintenance overhead
- Full support for both synchronous and asynchronous operations
- Improved error handling and resource management
- Enhanced thread safety with proper lock management
- Support for Flashbots MEV protection
- Context manager support for resource cleanup

## Architecture

The Unified Flash Loan Manager uses async/await as its primary pattern internally but provides synchronous wrapper methods for backward compatibility. This design allows for easier maintenance while ensuring existing code continues to work.

```
┌───────────────────────────────────────┐
│        UnifiedFlashLoanManager        │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │    Async Core Implementation    │  │
│  └─────────────────────────────────┘  │
│                                       │
│  ┌─────────────────────────────────┐  │
│  │  Synchronous Wrapper Methods    │  │
│  └─────────────────────────────────┘  │
└───────────────────────────────────────┘
           │                  │
           ▼                  ▼
┌────────────────┐  ┌────────────────────┐
│ Legacy Wrapper │  │ Direct Usage       │
│ FlashLoanMgr   │  │ (Recommended)      │
└────────────────┘  └────────────────────┘
```

## Migration Guide

### Async Usage (Recommended)

```python
from arbitrage_bot.core.unified_flash_loan_manager import create_flash_loan_manager

async def example_async_usage():
    # Create the web3 manager
    web3_manager = await create_web3_manager()
    
    # Create and initialize the flash loan manager
    async with await create_flash_loan_manager(web3_manager, config) as flash_loan_manager:
        # Check if a token is supported
        is_supported = await flash_loan_manager.is_token_supported(token_address)
        
        # Get maximum flash loan amount
        max_amount = await flash_loan_manager.get_max_flash_loan_amount(token_address)
        
        # Validate an arbitrage opportunity
        validation = await flash_loan_manager.validate_arbitrage_opportunity(
            input_token=token_address,
            output_token=token_address,
            input_amount=amount,
            expected_output=expected_profit,
            route=route
        )
        
        # Only proceed if profitable
        if validation['is_profitable']:
            # Prepare transaction
            tx_prep = await flash_loan_manager.prepare_flash_loan_transaction(
                token_address=token_address,
                amount=amount,
                route=route,
                min_profit=validation['min_profit_required']
            )
            
            # Execute if preparation succeeded
            if tx_prep['success']:
                result = await flash_loan_manager.execute_flash_loan_arbitrage(
                    token_address=token_address,
                    amount=amount,
                    route=route,
                    min_profit=validation['min_profit_required'],
                    use_flashbots=True  # Optional
                )
```

### Synchronous Usage

```python
from arbitrage_bot.core.unified_flash_loan_manager import create_flash_loan_manager_sync

def example_sync_usage():
    # Create the web3 manager
    web3_manager = create_web3_manager()
    
    # Create and initialize the flash loan manager
    flash_loan_manager = create_flash_loan_manager_sync(web3_manager, config)
    
    try:
        # Check if a token is supported
        is_supported = flash_loan_manager.is_token_supported_sync(token_address)
        
        # Get maximum flash loan amount
        max_amount = flash_loan_manager.get_max_flash_loan_amount_sync(token_address)
        
        # Validate an arbitrage opportunity
        validation = flash_loan_manager.validate_arbitrage_opportunity_sync(
            input_token=token_address,
            output_token=token_address,
            input_amount=amount,
            expected_output=expected_profit,
            route=route
        )
        
        # Only proceed if profitable
        if validation['is_profitable']:
            # Prepare transaction
            tx_prep = flash_loan_manager.prepare_flash_loan_transaction_sync(
                token_address=token_address,
                amount=amount,
                route=route,
                min_profit=validation['min_profit_required']
            )
            
            # Execute if preparation succeeded
            if tx_prep['success']:
                result = flash_loan_manager.execute_flash_loan_arbitrage_sync(
                    token_address=token_address,
                    amount=amount,
                    route=route,
                    min_profit=validation['min_profit_required'],
                    use_flashbots=True  # Optional
                )
    finally:
        # Clean up resources
        flash_loan_manager.close_sync()
```

### Using Legacy Compatibility Wrappers (Not Recommended)

The system provides backward compatibility through wrapper classes that implement the original interfaces:

```python
# Original FlashLoanManager (synchronous)
from arbitrage_bot.core.flash_loan_manager import create_flash_loan_manager

# Original AsyncFlashLoanManager (asynchronous)
from arbitrage_bot.core.flash_loan_manager_async import create_flash_loan_manager as create_async_flash_loan_manager
```

These modules will emit deprecation warnings to encourage migration to the unified implementation.

## Route Format

The flash loan arbitrage route format follows a standard structure:

```python
route = [
    {
        "dex_id": 1,  # Numeric identifier for the DEX (e.g., 1 for Uniswap)
        "token_in": "0x4200000000000000000000000000000000000006",  # Input token address
        "token_out": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Output token address
    },
    {
        "dex_id": 2,  # Second DEX in the arbitrage path
        "token_in": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "token_out": "0x4200000000000000000000000000000000000006"
    }
]
```

## Validation Result Format

The validation result provides detailed information about the profitability assessment:

```python
{
    "is_profitable": True/False,       # Overall profitability assessment
    "raw_profit": 1000000000000000,    # Raw profit in wei
    "flash_loan_fee": 90000000000000,  # Flash loan protocol fee in wei
    "gas_cost": 2236235500000,         # Estimated gas cost in wei
    "net_profit": 907781731500000,     # Net profit after costs in wei
    "profit_margin": 0.009077817315,   # Profit margin as a decimal
    "min_profit_required": 2000000000000000  # Min profit threshold in wei
}
```

## Transaction Execution Result Format

The execution result provides information about the transaction:

```python
{
    "success": True/False,             # Whether execution succeeded
    "transaction_hash": "0x123...",    # Transaction hash (if standard tx)
    "bundle_id": "0x456...",           # Bundle ID (if Flashbots)
    "target_block": 12345,             # Target block (if Flashbots)
    "gas_used": 250000,                # Gas used (if standard tx)
    "profit_realized": 5000000000000,  # Estimated profit realized
    "using_flashbots": True/False      # Whether Flashbots was used
}
```

## Error Handling

The unified manager includes comprehensive error handling:

1. All methods return structured response objects with success/error information
2. Failed operations include detailed error messages
3. Resource management is handled through context managers
4. Proper cleanup on errors

## Thread Safety

The unified implementation includes thread safety features:

1. Async locks to protect shared resources
2. Atomic operations for state changes
3. Proper handling of concurrent operations

## Configuration

The flash loan manager uses the following configuration structure:

```json
{
  "flash_loans": {
    "enabled": true,
    "use_flashbots": true,
    "min_profit_basis_points": 200,
    "slippage_tolerance": 50,
    "transaction_timeout": 180,
    "max_trade_size": "1",
    "balancer_vault": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
    "contract_address": {
      "mainnet": "0x...",
      "testnet": "0x..."
    }
  },
  "tokens": {
    "weth": "0x4200000000000000000000000000000000000006",
    "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
  }
}
```

## System Requirements

- Python 3.8+
- Web3.py 5.0+
- Asyncio support