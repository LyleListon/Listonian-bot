# Base DEX Scanner MCP Integration

This document provides an overview of the Base DEX Scanner MCP integration for the Listonian Arbitrage Bot.

## Overview

The Base DEX Scanner MCP integration allows the Listonian Arbitrage Bot to discover DEXes, pools, and arbitrage opportunities on the Base blockchain. It uses the Model Context Protocol (MCP) to communicate with a Base DEX Scanner server that provides real-time data about DEXes and pools.

## Components

The integration consists of the following components:

1. **BaseDexScannerMCP**: Client for the Base DEX Scanner MCP server
2. **BaseDexScannerSource**: Source for DEX discovery using the Base DEX Scanner MCP server
3. **BaseDexTradingExecutor**: Trading executor for Base DEX arbitrage opportunities

## Features

- **DEX Discovery**: Automatically discover DEXes on the Base blockchain
- **Pool Discovery**: Find pools for each DEX
- **Arbitrage Detection**: Detect arbitrage opportunities across different DEXes
- **Trading Execution**: Execute trades to capture arbitrage profits
- **Flashbots Integration**: Use Flashbots for MEV protection
- **Flash Loan Integration**: Use flash loans for capital efficiency

## Usage

### Setting Up the MCP Server

#### Option 1: Using the MCP Configuration

1. Create a configuration file at `.roo/mcp.json`:

```json
{
  "mcpServers": {
    "base-dex-scanner": {
      "command": "python",
      "args": ["run_base_dex_scanner_mcp.py"],
      "env": {
        "BASE_RPC_URL": "https://mainnet.base.org",
        "BASESCAN_API_KEY": "YOUR_BASESCAN_API_KEY",
        "DATABASE_URI": "postgresql://username:password@localhost:5432/dex_scanner",
        "SCAN_INTERVAL_MINUTES": "60"
      },
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

2. Start the MCP server:

```bash
python run_base_dex_scanner_mcp.py
```

#### Option 2: Using the HTTP API Server

1. Run the server directly:

```bash
python run_base_dex_scanner_mcp_with_api.py
```

2. Access the web interface at http://localhost:9050/

### Mock Data Mode

The Base DEX Scanner MCP server includes a mock data mode for testing purposes. By default, the server uses real data from the Base blockchain. To enable mock data mode, set the `USE_MOCK_DATA` environment variable to `true`:

```bash
USE_MOCK_DATA=true python run_base_dex_scanner_mcp_with_api.py
```

When mock data mode is enabled:

1. A prominent warning banner is displayed in the web interface
2. Warning messages are logged to the console
3. All data returned by the server is fake and not real blockchain data

**Important**: Mock data mode should only be used for testing purposes. Always use real data in production.

### Using the Integration

#### Discovering DEXes

```python
from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerMCP

async def discover_dexes():
    scanner = BaseDexScannerMCP()
    dexes = await scanner.scan_dexes()
    return dexes
```

#### Finding Pools

```python
from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerMCP

async def find_pools(dex_factory_address):
    scanner = BaseDexScannerMCP()
    pools = await scanner.get_factory_pools(dex_factory_address)
    return pools
```

#### Detecting Arbitrage Opportunities

```python
from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerSource

async def find_arbitrage_opportunities():
    source = BaseDexScannerSource()
    await source.initialize()
    opportunities = await source.detect_arbitrage_opportunities()
    return opportunities
```

#### Executing Trades

```python
from arbitrage_bot.integration.base_dex_trading_executor import BaseDexTradingExecutor

async def execute_trades(private_key):
    executor = BaseDexTradingExecutor(private_key=private_key)
    await executor.initialize()
    await executor.start()
    # Run for a while
    await asyncio.sleep(60)
    # Get statistics
    stats = await executor.get_stats()
    # Stop the executor
    await executor.stop()
    return stats
```

## Example

See `examples/base_dex_scanner_integration_example.py` for a complete example of using the Base DEX Scanner MCP integration.

To run the example:

```bash
python run_base_dex_scanner_example.py
```

## Web Interface

The Base DEX Scanner MCP server includes a web interface that provides information about the server and its endpoints. The web interface is available at http://localhost:9050/ when running the server with the HTTP API.

The web interface displays a warning banner when mock data mode is enabled, making it easy to identify when the server is using mock data.

## Architecture

```mermaid
graph TD
    A[Listonian Arbitrage Bot] --> B[BaseDexScannerMCP]
    A --> C[BaseDexScannerSource]
    A --> D[BaseDexTradingExecutor]
    B --> E[Base DEX Scanner MCP Server]
    C --> B
    D --> C
    D --> F[FlashbotsProvider]
    D --> G[Flash Loan Manager]
```

## Implementation Details

### BaseDexScannerMCP

The `BaseDexScannerMCP` class provides methods for interacting with the Base DEX Scanner MCP server:

- `scan_dexes()`: Scan for DEXes on the Base blockchain
- `get_dex_info(dex_address)`: Get information about a DEX
- `get_factory_pools(factory_address)`: Get pools for a DEX factory
- `check_contract(contract_address)`: Check if a contract is a DEX component
- `get_recent_dexes(limit, days)`: Get recently discovered DEXes

### BaseDexScannerSource

The `BaseDexScannerSource` class provides methods for using the Base DEX Scanner MCP server as a source for DEX discovery:

- `initialize()`: Initialize the source
- `fetch_dexes()`: Fetch DEXes from the scanner
- `get_pools_for_dex(dex)`: Get pools for a DEX
- `detect_arbitrage_opportunities()`: Detect arbitrage opportunities
- `cleanup()`: Clean up resources

### BaseDexTradingExecutor

The `BaseDexTradingExecutor` class provides methods for executing trades based on arbitrage opportunities:

- `initialize()`: Initialize the executor
- `start()`: Start the executor
- `stop()`: Stop the executor
- `get_stats()`: Get trading statistics

## Security Considerations

- **Private Keys**: The `BaseDexTradingExecutor` requires a private key for transaction signing. Ensure that private keys are stored securely and not hardcoded in the code.
- **Slippage Protection**: The `BaseDexTradingExecutor` includes slippage protection to prevent losses due to price movements.
- **MEV Protection**: The integration uses Flashbots for MEV protection to prevent front-running and sandwich attacks.
- **Error Handling**: All components include comprehensive error handling to prevent unexpected behavior.

## Performance Considerations

- **Caching**: The `BaseDexScannerMCP` class includes caching to improve performance.
- **Parallel Processing**: The `BaseDexScannerSource` class uses parallel processing to scan DEXes concurrently.
- **Resource Management**: All components follow resource management patterns for initialization and cleanup.
- **Mock Data Mode**: The server includes a mock data mode for testing purposes, which is disabled by default in production.

## Future Improvements

- **Multi-Path Arbitrage**: Implement multi-path arbitrage for better returns.
- **Gas Optimization**: Optimize gas usage for higher net profits.
- **Price Impact Analysis**: Implement price impact analysis for better arbitrage decisions.
- **Liquidity Depth Analysis**: Implement liquidity depth analysis for better arbitrage decisions.