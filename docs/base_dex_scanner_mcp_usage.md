# Base DEX Scanner MCP Server Usage Guide

## Overview

The Base DEX Scanner MCP (Model Context Protocol) server provides tools for scanning DEXes, finding pools, and detecting arbitrage opportunities on the Base blockchain. This server can be used by Cline to enhance its capabilities for blockchain analysis and arbitrage detection.

## Setup

The Base DEX Scanner MCP server has been configured to run automatically when Cline starts. The configuration is stored in `.roo/mcp.json` and uses a wrapper script to ensure proper environment variables are set.

## Available Tools

The Base DEX Scanner MCP server provides the following tools:

### 1. scan_dexes

Scans for DEXes on the Base blockchain.

**Input:** None

**Output:** List of DEXes with their addresses and types

**Example:**
```json
[
  {
    "name": "BaseSwap",
    "factory_address": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
    "router_address": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
    "type": "uniswap_v2",
    "version": "v2"
  },
  {
    "name": "Aerodrome",
    "factory_address": "0x420DD381b31aEf6683db6B902084cB0FFECe40Da",
    "router_address": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
    "type": "uniswap_v2",
    "version": "v2"
  }
]
```

### 2. get_dex_info

Gets information about a specific DEX.

**Input:**
```json
{
  "dex_address": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
}
```

**Output:**
```json
{
  "name": "BaseSwap",
  "factory_address": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD",
  "router_address": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
  "type": "uniswap_v2",
  "version": "v2"
}
```

### 3. get_factory_pools

Gets pools for a specific DEX factory.

**Input:**
```json
{
  "factory_address": "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
}
```

**Output:**
```json
[
  {
    "address": "0x7E9DAB607D95C8336BF22E1Bd5a194B2bA262A2C",
    "token0": {
      "address": "0x4200000000000000000000000000000000000006",
      "symbol": "WETH",
      "decimals": 18
    },
    "token1": {
      "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
      "symbol": "USDC",
      "decimals": 6
    },
    "liquidity_usd": 5000000.0
  }
]
```

### 4. check_contract

Checks if a contract is a DEX component.

**Input:**
```json
{
  "contract_address": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86"
}
```

**Output:**
```json
{
  "is_dex": true,
  "type": "router",
  "dex_name": "BaseSwap",
  "version": "v2"
}
```

### 5. get_pool_price

Gets price information for a pool.

**Input:**
```json
{
  "pool_address": "0x7E9DAB607D95C8336BF22E1Bd5a194B2bA262A2C"
}
```

**Output:**
```json
{
  "price": 3500.0
}
```

## Using the MCP Server in Cline

To use the Base DEX Scanner MCP server in Cline, you can use the `use_mcp_tool` tool:

```
<use_mcp_tool>
<server_name>base-dex-scanner</server_name>
<tool_name>scan_dexes</tool_name>
<arguments>
{}
</arguments>
</use_mcp_tool>
```

This will return a list of DEXes on the Base blockchain.

## Development vs. Production Mode

The MCP server can run in two modes:

1. **Development Mode** (default for MCP): Uses mock data for testing and demonstration purposes
2. **Production Mode**: Uses real blockchain data

The wrapper script (`run_base_dex_scanner_mcp_wrapper.py`) is configured to run the server in development mode with mock data by default. This ensures that the MCP server can be used for demonstration purposes without requiring a connection to the real blockchain.

If you want to use real blockchain data, you would need to modify the wrapper script to set:
```python
env["ENVIRONMENT"] = "production"
env["USE_MOCK_DATA"] = "false"
```

## Troubleshooting

If you encounter issues with the MCP server:

1. Check the logs in `logs/base_dex_scanner_mcp.log` and `logs/base_dex_scanner_mcp_wrapper.log`
2. Ensure the server is running by accessing http://localhost:9050/ in a browser
3. Verify that the MCP configuration in `.roo/mcp.json` is correct
4. Restart Cline to restart the MCP server