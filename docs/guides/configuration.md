# Listonian Bot Configuration Guide

## Configuration Overview

The Listonian Bot uses a hierarchical configuration system that allows for flexible customization of all aspects of the bot's operation. This guide explains how to configure the bot for optimal performance and to meet your specific trading requirements.

## Configuration Files

The bot uses several configuration files located in the `configs/` directory:

1. **default/config.json**: Base configuration with default values
2. **development/config.json**: Configuration for development environment
3. **production/config.json**: Configuration for production environment

The bot loads these configurations in order, with later files overriding values from earlier ones. You can also provide environment-specific overrides using environment variables.

## Core Configuration Parameters

### Trading Parameters

```json
{
  "trading": {
    "min_profit_threshold": 0.5,
    "max_slippage": 1.0,
    "gas_price_multiplier": 1.1,
    "max_trade_amount": 1.0,
    "min_liquidity": 10000,
    "max_path_length": 3,
    "execution_timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5,
    "trading_enabled": true,
    "trading_pairs": [
      {
        "base_token": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "quote_token": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
      }
    ]
  }
}
```

| Parameter | Description | Default | Recommended Range |
|-----------|-------------|---------|-------------------|
| min_profit_threshold | Minimum profit percentage to execute a trade | 0.5 | 0.1 - 2.0 |
| max_slippage | Maximum allowed slippage percentage | 1.0 | 0.1 - 3.0 |
| gas_price_multiplier | Multiplier for gas price estimation | 1.1 | 1.0 - 1.5 |
| max_trade_amount | Maximum trade amount in base currency | 1.0 | 0.1 - 10.0 |
| min_liquidity | Minimum liquidity required in the pool | 10000 | 1000 - 100000 |
| max_path_length | Maximum number of hops in a trading path | 3 | 2 - 4 |
| execution_timeout | Timeout for trade execution in seconds | 30 | 10 - 60 |
| retry_attempts | Number of retry attempts for failed trades | 3 | 1 - 5 |
| retry_delay | Delay between retry attempts in seconds | 5 | 1 - 10 |
| trading_enabled | Enable/disable trading | true | true/false |
| trading_pairs | List of trading pairs to monitor | [] | Array of token pairs |

### Blockchain Configuration

```json
{
  "blockchain": {
    "networks": [
      {
        "name": "ethereum",
        "chain_id": 1,
        "rpc_url": "https://mainnet.infura.io/v3/YOUR_API_KEY",
        "ws_url": "wss://mainnet.infura.io/ws/v3/YOUR_API_KEY",
        "explorer_url": "https://etherscan.io",
        "enabled": true,
        "gas_limit": 500000,
        "priority_fee": 1.5
      },
      {
        "name": "bsc",
        "chain_id": 56,
        "rpc_url": "https://bsc-dataseed.binance.org/",
        "ws_url": "wss://bsc-ws-node.nariox.org:443",
        "explorer_url": "https://bscscan.com",
        "enabled": true,
        "gas_limit": 500000,
        "priority_fee": 1.0
      }
    ],
    "default_network": "ethereum",
    "block_confirmation": 1,
    "transaction_timeout": 120
  }
}
```

### DEX Configuration

```json
{
  "dexes": [
    {
      "name": "pancakeswap",
      "network": "bsc",
      "factory_address": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
      "router_address": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
      "enabled": true,
      "fee_tiers": [0.25]
    },
    {
      "name": "uniswap_v3",
      "network": "ethereum",
      "factory_address": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
      "router_address": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
      "enabled": true,
      "fee_tiers": [0.05, 0.3, 1.0]
    }
  ]
}
```

### MEV Protection Configuration

```json
{
  "mev_protection": {
    "enabled": true,
    "provider": "flashbots",
    "flashbots": {
      "relay_url": "https://relay.flashbots.net/",
      "min_block_confirmations": 1,
      "max_block_confirmations": 3,
      "priority_fee_percentage": 90
    },
    "mev_blocker": {
      "rpc_url": "https://rpc.mevblocker.io",
      "enabled": false
    }
  }
}
```

### Flash Loan Configuration

```json
{
  "flash_loans": {
    "enabled": true,
    "providers": [
      {
        "name": "aave",
        "network": "ethereum",
        "lending_pool_address": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
        "enabled": true,
        "max_loan_amount": 100,
        "fee_percentage": 0.09
      },
      {
        "name": "dydx",
        "network": "ethereum",
        "solo_address": "0x1E0447b19BB6EcFdAe1e4AE1694b0C3659614e4e",
        "enabled": true,
        "max_loan_amount": 50,
        "fee_percentage": 0
      }
    ],
    "default_provider": "aave"
  }
}
```

### Dashboard Configuration

```json
{
  "dashboard": {
    "port": 8080,
    "host": "0.0.0.0",
    "enable_authentication": true,
    "session_timeout": 3600,
    "refresh_interval": 5,
    "theme": "dark",
    "max_trades_display": 100,
    "enable_notifications": true
  }
}
```

### API Configuration

```json
{
  "api": {
    "port": 8000,
    "host": "0.0.0.0",
    "enable_authentication": true,
    "rate_limit": 100,
    "rate_limit_period": 60,
    "cors_origins": ["*"],
    "api_keys": []
  }
}
```

### Logging Configuration

```json
{
  "logging": {
    "level": "INFO",
    "file": "logs/bot.log",
    "max_file_size": 10485760,
    "backup_count": 5,
    "console_output": true,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  }
}
```

### MCP Server Configuration

```json
{
  "mcp_servers": [
    {
      "id": "mcp1",
      "host": "localhost",
      "port": 9001,
      "api_key": "your_api_key_here",
      "enabled": true,
      "services": ["market_data", "arbitrage_engine"]
    },
    {
      "id": "mcp2",
      "host": "localhost",
      "port": 9002,
      "api_key": "your_api_key_here",
      "enabled": true,
      "services": ["transaction_manager", "flash_loans"]
    }
  ]
}
```

## Environment Variable Overrides

You can override any configuration value using environment variables. The format is:

```
LISTONIAN_<SECTION>_<PARAMETER>=value
```

For example:

```
LISTONIAN_TRADING_MIN_PROFIT_THRESHOLD=0.8
LISTONIAN_BLOCKCHAIN_DEFAULT_NETWORK=bsc
LISTONIAN_DASHBOARD_PORT=8081
```

For nested configurations, use underscores:

```
LISTONIAN_BLOCKCHAIN_NETWORKS_0_RPC_URL=https://custom-rpc.example.com
```

## Configuration Validation

The bot validates all configuration parameters on startup. If any required parameters are missing or invalid, the bot will log an error and exit.

To validate your configuration without starting the bot:

```bash
python scripts/validate_config.py --env production
```

## Dynamic Configuration

Some configuration parameters can be changed at runtime through the dashboard or API:

1. Trading parameters (min_profit_threshold, max_slippage, etc.)
2. Trading enabled/disabled status
3. Logging level
4. Dashboard refresh interval

Changes made through the dashboard or API are temporary and will be reset when the bot restarts. To make permanent changes, update the configuration files.

## Configuration Best Practices

1. **Start Conservative**: Begin with higher profit thresholds and lower trade amounts
2. **Test Thoroughly**: Test any configuration changes in a development environment first
3. **Monitor Closely**: After configuration changes, monitor the bot closely for unexpected behavior
4. **Regular Backups**: Back up your configuration files before making significant changes
5. **Environment Separation**: Use different configurations for development, testing, and production
6. **Secure Sensitive Data**: Store API keys and private keys as environment variables, not in configuration files
7. **Document Changes**: Keep a log of configuration changes and their effects on performance
