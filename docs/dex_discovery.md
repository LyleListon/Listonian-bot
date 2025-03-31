# DEX Discovery System

This document describes the DEX discovery system implemented in the Listonian Arbitrage Bot.

## Overview

The DEX discovery system is designed to automatically discover and validate DEXes (Decentralized Exchanges) on various blockchain networks. It uses multiple sources to gather information about DEXes, validates their contracts, and stores the information in a repository for use by the arbitrage system.

## Components

The DEX discovery system consists of the following components:

### 1. DEX Sources

Sources are responsible for fetching DEX information from various external sources:

- **DefiLlamaSource**: Fetches DEX information from DeFiLlama's API
- **DexScreenerSource**: Fetches DEX information from DexScreener's API
- **DefiPulseSource**: Fetches DEX information from DefiPulse's API

Each source implements the `DEXSource` interface, which defines methods for fetching DEX information.

### 2. DEX Repository

The repository is responsible for storing and managing DEX information. It provides methods for adding, retrieving, and validating DEXes, as well as persisting them to disk.

### 3. DEX Validator

The validator is responsible for validating DEX contracts. It checks that the contract addresses are valid, that the contracts exist on the blockchain, and that they implement the expected interfaces.

### 4. DEX Discovery Manager

The manager coordinates the sources, repository, and validator to discover, validate, and store DEX information. It provides a high-level interface for the arbitrage system to interact with the DEX discovery system.

## Data Model

The DEX discovery system uses the following data model:

### DEXInfo

The `DEXInfo` class represents information about a DEX, including:

- **name**: The name of the DEX
- **protocol_type**: The protocol type (e.g., Uniswap V2, Uniswap V3, Balancer, Curve)
- **version**: The version of the DEX
- **chain_id**: The chain ID of the blockchain network
- **factory_address**: The address of the factory contract
- **router_address**: The address of the router contract
- **quoter_address**: The address of the quoter contract (optional)
- **fee_tiers**: The fee tiers supported by the DEX
- **tvl_usd**: The total value locked in USD
- **volume_24h_usd**: The 24-hour trading volume in USD
- **source**: The source of the DEX information
- **validated**: Whether the DEX has been validated
- **validation_errors**: Any validation errors

### DEXProtocolType

The `DEXProtocolType` enum represents the protocol type of a DEX:

- **UNISWAP_V2**: Uniswap V2 and compatible protocols
- **UNISWAP_V3**: Uniswap V3 and compatible protocols
- **BALANCER**: Balancer and compatible protocols
- **CURVE**: Curve and compatible protocols
- **CUSTOM**: Custom protocols
- **UNKNOWN**: Unknown protocols

## Configuration

The DEX discovery system is configured through the `dex_discovery` section of the configuration file:

```json
"dex_discovery": {
    "discovery_interval_seconds": 3600,
    "auto_validate": true,
    "chain_id": 8453,
    "storage_dir": "data/dexes",
    "storage_file": "dexes.json",
    "defillama": {
        "base_url": "https://api.llama.fi",
        "cache_ttl": 3600
    },
    "dexscreener": {
        "base_url": "https://api.dexscreener.com/latest",
        "cache_ttl": 3600
    },
    "defipulse": {
        "base_url": "https://data-api.defipulse.com/api/v1",
        "cache_ttl": 3600
    }
}
```

## Usage

### Basic Usage

```python
from arbitrage_bot.core.arbitrage.discovery import (
    create_dex_discovery_manager,
    setup_dex_discovery
)
from arbitrage_bot.core.web3.web3_manager import create_web3_manager
from arbitrage_bot.utils.config_loader import load_config

# Load configuration
config = load_config()

# Create Web3 manager
web3_manager = await create_web3_manager(config["web3"])

# Create DEX discovery manager
discovery_manager = await create_dex_discovery_manager(
    web3_manager=web3_manager,
    config=config["dex_discovery"]
)

# Discover DEXes
dexes = await discovery_manager.discover_dexes()

# Get DEXes from repository
repo_dexes = await discovery_manager.get_dexes()

# Get a specific DEX by name
dex = await discovery_manager.get_dex("baseswap_v3")

# Get a specific DEX by factory address
dex = await discovery_manager.get_dex_by_address("0x38015D05f4fEC8AFe15D7cc0386a126574e8077B")

# Validate a DEX
is_valid, errors = await discovery_manager.validate_dex(dex)

# Clean up resources
await discovery_manager.cleanup()
await web3_manager.close()
```

### Integration with Arbitrage System

```python
from arbitrage_bot.core.arbitrage.discovery.integration import (
    integrate_dex_discovery,
    setup_dex_discovery
)

# Integrate DEX discovery with arbitrage system
await integrate_dex_discovery(
    discovery_manager=discovery_manager,
    dex_manager=dex_manager,
    web3_manager=web3_manager,
    config=config
)

# Set up DEX discovery with periodic discovery
dex_discovery_manager = await setup_dex_discovery(
    dex_manager=dex_manager,
    web3_manager=web3_manager,
    config=config
)
```

## Example

See the `examples/dex_discovery_example.py` file for a complete example of how to use the DEX discovery system.

## Testing

The DEX discovery system includes unit tests in the `tests/test_dex_discovery.py` file. To run the tests, use the following command:

```bash
pytest tests/test_dex_discovery.py