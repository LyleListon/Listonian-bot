# Base DEX Scanner MCP Integration

This document provides an overview of how to integrate the Base DEX Scanner MCP server with the Listonian Arbitrage Bot.

## Overview

The Base DEX Scanner MCP server is a Model Context Protocol (MCP) server that continuously monitors the Base blockchain for DEXes and pools. It provides tools and resources for discovering and querying DEXes on the Base blockchain, which can be used by the Listonian Arbitrage Bot to find arbitrage opportunities.

## Configuration

The Base DEX Scanner MCP server is configured in the `.roo/mcp.json` file:

```json
{
  "mcpServers": {
    "base-dex-scanner": {
      "command": "python",
      "args": ["C:/Users/lylep/AppData/Roaming/Roo-Code/MCP/base-dex-scanner-mcp-py/run_server.py"],
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

Make sure to replace the environment variables with your actual values:

- `BASE_RPC_URL`: URL of the Base RPC provider
- `BASESCAN_API_KEY`: API key for Basescan
- `DATABASE_URI`: PostgreSQL connection URI
- `SCAN_INTERVAL_MINUTES`: Interval between DEX scans in minutes

## Integration

The integration with the Listonian Arbitrage Bot is implemented in the `arbitrage_bot/integration/base_dex_scanner_mcp.py` file. This file provides two main classes:

1. `BaseDexScannerMCP`: A low-level client for the Base DEX Scanner MCP server
2. `BaseDexScannerSource`: A high-level integration that implements the `DEXSource` interface

### Using the BaseDexScannerMCP Client

The `BaseDexScannerMCP` client provides direct access to the MCP tools:

```python
from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerMCP

async def example():
    # Create the scanner
    scanner = BaseDexScannerMCP()
    
    # Scan for DEXes
    dexes = await scanner.scan_dexes()
    
    # Get DEX info
    dex_info = await scanner.get_dex_info("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
    
    # Get pools for a factory
    pools = await scanner.get_factory_pools("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
    
    # Check if a contract is a DEX component
    contract_info = await scanner.check_contract("0x33128a8fC17869897dcE68Ed026d694621f6FDfD")
    
    # Get recently discovered DEXes
    recent_dexes = await scanner.get_recent_dexes(limit=10, days=7)
```

### Using the BaseDexScannerSource

The `BaseDexScannerSource` class implements the `DEXSource` interface, which allows it to be used with the existing DEX discovery system:

```python
from arbitrage_bot.integration.base_dex_scanner_mcp import BaseDexScannerSource

async def example():
    # Create the source
    source = BaseDexScannerSource()
    
    # Initialize the source
    await source.initialize()
    
    # Fetch DEXes
    dexes = await source.fetch_dexes()
    
    # Get pools for a DEX
    pools = await source.get_pools_for_dex(dexes[0])
    
    # Detect arbitrage opportunities
    opportunities = await source.detect_arbitrage_opportunities()
    
    # Clean up resources
    await source.cleanup()
```

## Example Usage

See the `examples/base_dex_scanner_integration_example.py` file for a complete example of how to use the Base DEX Scanner MCP server with the Listonian Arbitrage Bot.

## Benefits

The Base DEX Scanner MCP server provides several benefits for the Listonian Arbitrage Bot:

1. **Continuous Monitoring**: The server continuously monitors the Base blockchain for new DEXes and pools, ensuring that the bot is always aware of the latest opportunities.

2. **Efficient Scanning**: The server uses efficient scanning techniques to minimize resource usage and maximize performance.

3. **Caching**: The server caches results to reduce the number of RPC calls and improve performance.

4. **Standardized Interface**: The server provides a standardized interface for discovering and querying DEXes, which can be easily integrated with the existing arbitrage bot code.

5. **Extensibility**: The server can be extended to support additional DEX protocols and features as needed.

## Next Steps

1. **Implement Real MCP Integration**: Replace the placeholder MCP tool calls with actual MCP SDK calls.

2. **Add Support for More DEX Protocols**: Extend the server to support additional DEX protocols on the Base blockchain.

3. **Improve Arbitrage Detection**: Enhance the arbitrage detection algorithm to consider price differences and potential profits.

4. **Add Monitoring and Alerting**: Implement monitoring and alerting for the server to ensure it is running correctly.

5. **Optimize Performance**: Optimize the server's performance to reduce resource usage and improve scanning speed.