# Project Structure

This document outlines the ideal structure for the Listonian Arbitrage Bot project.

## Overview

The project is organized into the following main components:

```
Listonian-bot/
├── arbitrage_bot/         # Core arbitrage bot package
├── new_dashboard/         # Dashboard implementation
├── configs/               # Configuration files
├── scripts/               # Helper scripts
├── memory-bank/           # Shared data storage
├── secure/                # Secure storage for sensitive data
├── .augment/              # Augment extension configuration
├── docs/                  # Documentation
├── tests/                 # Tests
├── logs/                  # Log files
└── mcp_servers/           # MCP server implementations
```

## Core Components

### 1. Arbitrage Bot (`arbitrage_bot/`)

The core arbitrage bot package contains the main functionality for finding and executing arbitrage opportunities.

```
arbitrage_bot/
├── core/                  # Core bot functionality
│   ├── arbitrage/         # Arbitrage system implementation
│   ├── dex/               # DEX implementations and interfaces
│   └── web3/              # Web3 connectivity and blockchain interaction
├── dashboard/             # Old dashboard implementation
├── utils/                 # Utility functions and helpers
└── __init__.py
```

### 2. Dashboard (`new_dashboard/`)

The dashboard provides a web interface for monitoring and controlling the bot.

```
new_dashboard/
├── dashboard/             # Dashboard application
│   ├── routes/            # API routes
│   ├── services/          # Services for data processing
│   └── websocket/         # WebSocket implementation
├── static/                # Static assets
├── templates/             # UI templates
└── __init__.py
```

### 3. Configuration (`configs/`)

Configuration files for the bot and dashboard.

```
configs/
├── default.json           # Default configuration
├── production.json        # Production configuration
└── test.json              # Test configuration
```

### 4. Scripts (`scripts/`)

Helper scripts for various tasks.

```
scripts/
├── start_bot_with_dashboard.ps1  # Start both bot and dashboard
├── initialize_memory_bank.py     # Initialize memory bank
├── manage_mcp_servers.py         # Manage MCP servers
└── cleanup_project.py            # Clean up project
```

### 5. MCP Servers (`mcp_servers/`)

MCP server implementations for various data providers.

```
mcp_servers/
├── base_dex_scanner/      # Base DEX scanner MCP server
├── crypto_price/          # Crypto price MCP server
├── market_analysis/       # Market analysis MCP server
└── __init__.py
```

## Entry Points

The main entry points for the project are:

- `run_bot.py` - Start the arbitrage bot
- `run_dashboard.py` - Start the dashboard
- `run_base_dex_scanner_mcp.py` - Start the Base DEX scanner MCP server
- `run_base_dex_scanner_mcp_with_api.py` - Start the Base DEX scanner MCP server with API

## Data Flow

The data flow between components is as follows:

1. **Arbitrage Bot → Memory Bank**: The bot writes trade data, metrics, and system state to the memory bank.
2. **Memory Bank → Dashboard**: The dashboard reads data from the memory bank to display information.
3. **Dashboard → Arbitrage Bot**: The dashboard sends commands to the bot via API endpoints.
4. **MCP Servers → Arbitrage Bot**: MCP servers provide data to the bot for decision making.

## Recommended Cleanup Actions

1. **Move DEX-specific files to `arbitrage_bot/core/dex/`**:
   - `pancakeswap.py`
   - `rocketswap.py`
   - `swapbased.py`
   - `uniswap_v3.py`

2. **Move MCP server files to `mcp_servers/`**:
   - `run_base_dex_scanner_mcp.py`
   - `run_base_dex_scanner_mcp_with_api.py`
   - `run_base_dex_scanner_mcp_wrapper.py`
   - `run_base_dex_scanner_example.py`

3. **Organize configuration files**:
   - Move all configuration files to `configs/`
   - Ensure `.env` and `.env.production` are in the root directory

4. **Clean up temporary and backup files**:
   - Use `scripts/cleanup_project.py` to identify and move junk files

5. **Update documentation**:
   - Update `README.md` with project structure and setup instructions
   - Create additional documentation in `docs/`
