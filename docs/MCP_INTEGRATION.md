# MCP Server Integration with Augment

This document explains how to integrate the MCP (Master Control Program) servers with the Augment extension.

## Overview

The Listonian Arbitrage Bot uses several MCP servers to provide data and analysis:

1. **Base DEX Scanner MCP Server** - Monitors the Base blockchain for DEXes and pools
2. **Crypto Price MCP Server** - Provides cryptocurrency price data
3. **Market Analysis MCP Server** - Analyzes market conditions and trends

These servers follow the Model Context Protocol, which allows the arbitrage bot to call tools and access resources on these servers.

## Configuration

The MCP servers are configured in the `.augment/mcp_config.json` file. This file defines the servers, their commands, arguments, and environment variables.

```json
{
  "mcpServers": {
    "base-dex-scanner": {
      "command": "python",
      "args": ["run_base_dex_scanner_mcp_with_api.py"],
      "env": {
        "BASE_RPC_URL": "${BASE_RPC_URL}",
        "BASESCAN_API_KEY": "${BASESCAN_API_KEY}",
        "DATABASE_URI": "${DATABASE_URI}",
        "SCAN_INTERVAL_MINUTES": "60",
        "BASE_DEX_SCANNER_API_KEY": "${BASE_DEX_SCANNER_API_KEY}"
      },
      "description": "Monitors the Base blockchain for DEXes and pools"
    },
    // Other servers...
  }
}
```

## Managing MCP Servers

You can manage the MCP servers using the `scripts/manage_mcp_servers.py` script:

```bash
# List all MCP servers
python scripts/manage_mcp_servers.py list

# Start a specific MCP server
python scripts/manage_mcp_servers.py start base-dex-scanner

# Stop a specific MCP server
python scripts/manage_mcp_servers.py stop base-dex-scanner

# Start all MCP servers
python scripts/manage_mcp_servers.py start-all

# Stop all MCP servers
python scripts/manage_mcp_servers.py stop-all
```

## Integration with Augment

The Augment extension can interact with the MCP servers through the `.augment/mcp_helper.py` script. This script provides functions to start, stop, and list MCP servers.

### Using MCP Servers in Your Code

Here's how to use the MCP servers in your code:

```python
# Import the MCP helper functions
from arbitrage_bot.utils.mcp_helper import call_mcp_tool, access_mcp_resource

# Call an MCP tool
result = await call_mcp_tool(
    server_name="base-dex-scanner",
    tool_name="scan_dexes",
    arguments={"use_cache": True}
)

# Access an MCP resource
resource = await access_mcp_resource(
    server_name="base-dex-scanner",
    uri="dex://0x33128a8fC17869897dcE68Ed026d694621f6FDfD/info"
)
```

## MCP Server Tools

### Base DEX Scanner MCP Server

The Base DEX Scanner MCP server provides the following tools:

- `scan_dexes` - Scan for DEXes on the Base blockchain
- `get_dex_info` - Get information about a specific DEX
- `get_factory_pools` - Get pools for a specific factory
- `get_pool_info` - Get information about a specific pool
- `get_pool_price` - Get the current price for a specific pool

### Crypto Price MCP Server

The Crypto Price MCP server provides the following tools:

- `get_prices` - Get current prices for cryptocurrencies
- `get_historical_prices` - Get historical prices for cryptocurrencies
- `get_price_change` - Get price change information for cryptocurrencies

### Market Analysis MCP Server

The Market Analysis MCP server provides the following tools:

- `assess_market_conditions` - Assess current market conditions
- `analyze_mev_risks` - Analyze MEV risks for a specific token
- `predict_price_movement` - Predict price movement for a specific token
- `evaluate_arbitrage_opportunity` - Evaluate an arbitrage opportunity

## Troubleshooting

If you encounter issues with the MCP servers:

1. Check that the servers are running using `python scripts/manage_mcp_servers.py list`
2. Verify that the environment variables are set correctly
3. Check the server logs for error messages
4. Restart the servers using `python scripts/manage_mcp_servers.py stop-all` followed by `python scripts/manage_mcp_servers.py start-all`

## Next Steps

1. **Implement Authentication** - Add authentication to secure the MCP servers
2. **Add Monitoring** - Implement monitoring for the MCP servers
3. **Improve Error Handling** - Enhance error handling and recovery
4. **Optimize Performance** - Optimize the performance of the MCP servers
