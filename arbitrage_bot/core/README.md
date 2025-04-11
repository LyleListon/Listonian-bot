# Core Module

The core module contains the fundamental components of the Listonian Arbitrage Bot. These components handle the critical operations of the bot, including blockchain interaction, flash loan management, and arbitrage execution.

## Components

### WebSocket Management

The WebSocket functionality has been refactored for improved stability:

- **Automatic reconnection**: The system now automatically reconnects when a WebSocket connection is lost
- **Connection pooling**: Multiple WebSocket connections are managed efficiently
- **Error handling**: Robust error handling for WebSocket-related issues

### Flash Loan Management

Flash loan functionality has been consolidated into a unified system:

- **UnifiedFlashLoanManager**: Centralized manager for all flash loan operations
- **EnhancedFlashLoanManager**: Extended functionality with improved error handling and profitability checks
- **Balancer Integration**: Primary flash loan provider through Balancer protocol

### Execution Engine

The execution engine handles the actual execution of arbitrage opportunities:

- **ArbitrageExecutor**: Manages the execution of arbitrage opportunities
- **Transaction Builder**: Builds and optimizes transaction bundles
- **Flashbots Integration**: Protects against MEV attacks

### Path Finding

The path finding system identifies potential arbitrage opportunities:

- **PathFinder**: Finds optimal paths across multiple DEXes
- **RouteOptimizer**: Optimizes routes for maximum profitability
- **PriceAnalyzer**: Analyzes price differences across DEXes

## Usage

### Flash Loan Management

```python
from arbitrage_bot.core.unified_flash_loan_manager import UnifiedFlashLoanManager

# Initialize the manager
flash_loan_manager = UnifiedFlashLoanManager(
    web3=web3_instance,
    flashbots_provider=flashbots_provider,
    memory_bank=memory_bank,
    min_profit_threshold=Web3.to_wei(0.01, "ether"),
    max_slippage=Decimal("0.005"),
    max_paths=3,
)

# Prepare a flash loan bundle
bundle = await flash_loan_manager.prepare_flash_loan_bundle(
    token_pair=token_pair,
    amount=amount,
    prices=prices
)

# Execute the bundle
result = await flash_loan_manager.execute_bundle(bundle)
```

### Path Finding

```python
from arbitrage_bot.core.path_finder import PathFinder

# Initialize the path finder
path_finder = PathFinder(
    dex_manager=dex_manager,
    config=config,
    web3_manager=web3_manager
)

# Find arbitrage paths
paths = await path_finder.find_arbitrage_paths(
    start_token_address=weth_address,
    amount_in=amount,
    max_paths=3
)

# Evaluate a path
evaluation = await path_finder.evaluate_path(paths[0])
```

## Error Handling

The core module includes robust error handling with:

- Automatic retries for transient errors
- Detailed logging for debugging
- Graceful degradation when services are unavailable

## Testing

Each component in the core module has comprehensive unit and integration tests:

```bash
python -m pytest arbitrage_bot/tests/core/