# Listonian Bot API Data Models

This document describes the data models used in the Listonian Bot API. Understanding these models is essential for effectively working with the API.

## Common Models

### Timestamp

All timestamps in the API are represented as Unix timestamps (seconds since the Unix epoch).

Example: `1619123456`

### Price

Prices are represented as strings to preserve precision.

Example: `"1234.56789"`

### Address

Blockchain addresses are represented as hexadecimal strings.

Example: `"0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"`

### Transaction Hash

Transaction hashes are represented as hexadecimal strings.

Example: `"0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"`

## Core Models

### Token

Represents a cryptocurrency token.

```json
{
  "symbol": "ETH",
  "name": "Ethereum",
  "address": "0x0000000000000000000000000000000000000000",
  "decimals": 18,
  "price_usd": "3500.12",
  "volume_24h_usd": "1234567.89",
  "market_cap_usd": "412345678901.23",
  "change_24h_percentage": "2.5",
  "networks": ["ethereum", "bsc"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Token symbol (e.g., "ETH", "BTC") |
| `name` | string | Token name (e.g., "Ethereum", "Bitcoin") |
| `address` | string | Token contract address (zero address for native tokens) |
| `decimals` | integer | Number of decimal places for the token |
| `price_usd` | string | Current price in USD |
| `volume_24h_usd` | string | 24-hour trading volume in USD |
| `market_cap_usd` | string | Market capitalization in USD |
| `change_24h_percentage` | string | 24-hour price change percentage |
| `networks` | array of strings | Blockchain networks where the token is available |

### TokenPair

Represents a trading pair between two tokens.

```json
{
  "base_token": {
    "symbol": "ETH",
    "address": "0x0000000000000000000000000000000000000000"
  },
  "quote_token": {
    "symbol": "USDC",
    "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
  },
  "price": "3500.12",
  "inverse_price": "0.00028570",
  "liquidity_usd": "1234567.89",
  "volume_24h_usd": "9876543.21",
  "dex": "uniswap_v3",
  "network": "ethereum",
  "fee_tier": "0.3",
  "pair_address": "0x1234567890abcdef1234567890abcdef12345678"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `base_token` | object | Base token information |
| `quote_token` | object | Quote token information |
| `price` | string | Current price of base token in terms of quote token |
| `inverse_price` | string | Current price of quote token in terms of base token |
| `liquidity_usd` | string | Total liquidity in USD |
| `volume_24h_usd` | string | 24-hour trading volume in USD |
| `dex` | string | DEX where the pair is traded |
| `network` | string | Blockchain network |
| `fee_tier` | string | Fee tier (for DEXs with multiple fee tiers) |
| `pair_address` | string | Address of the pair contract or pool |

### ArbitrageOpportunity

Represents an arbitrage opportunity.

```json
{
  "id": "opp-123456",
  "path": ["ETH", "USDC", "WBTC", "ETH"],
  "addresses": [
    "0x0000000000000000000000000000000000000000",
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "0x0000000000000000000000000000000000000000"
  ],
  "expected_profit_percentage": "1.25",
  "expected_profit_usd": "42.15",
  "input_amount": "1.0",
  "input_token": "ETH",
  "estimated_gas_cost_usd": "12.34",
  "net_profit_usd": "29.81",
  "dexes": ["uniswap_v3", "sushiswap", "uniswap_v3"],
  "networks": ["ethereum"],
  "timestamp": 1619123456,
  "risk_score": 2,
  "expiration": 1619123486,
  "execution_plan": {
    "steps": [
      {
        "dex": "uniswap_v3",
        "action": "swap",
        "input_token": "ETH",
        "output_token": "USDC",
        "input_amount": "1.0",
        "expected_output_amount": "3500.12",
        "fee_tier": "0.3"
      },
      {
        "dex": "sushiswap",
        "action": "swap",
        "input_token": "USDC",
        "output_token": "WBTC",
        "input_amount": "3500.12",
        "expected_output_amount": "0.0625"
      },
      {
        "dex": "uniswap_v3",
        "action": "swap",
        "input_token": "WBTC",
        "output_token": "ETH",
        "input_amount": "0.0625",
        "expected_output_amount": "1.0125",
        "fee_tier": "0.3"
      }
    ],
    "flash_loan": {
      "provider": "aave",
      "token": "ETH",
      "amount": "1.0",
      "fee": "0.0009"
    },
    "mev_protection": {
      "provider": "flashbots",
      "bundle_type": "standard"
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the opportunity |
| `path` | array of strings | Token symbols in the arbitrage path |
| `addresses` | array of strings | Token addresses in the arbitrage path |
| `expected_profit_percentage` | string | Expected profit as a percentage |
| `expected_profit_usd` | string | Expected profit in USD |
| `input_amount` | string | Input amount for the arbitrage |
| `input_token` | string | Input token symbol |
| `estimated_gas_cost_usd` | string | Estimated gas cost in USD |
| `net_profit_usd` | string | Net profit after gas costs in USD |
| `dexes` | array of strings | DEXs used in the arbitrage path |
| `networks` | array of strings | Blockchain networks involved |
| `timestamp` | integer | Timestamp when the opportunity was found |
| `risk_score` | integer | Risk score (1-5, where 1 is lowest risk) |
| `expiration` | integer | Timestamp when the opportunity expires |
| `execution_plan` | object | Detailed execution plan |

### Trade

Represents an executed trade.

```json
{
  "id": "trade-123456",
  "opportunity_id": "opp-123456",
  "status": "success",
  "path": ["ETH", "USDC", "WBTC", "ETH"],
  "addresses": [
    "0x0000000000000000000000000000000000000000",
    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    "0x0000000000000000000000000000000000000000"
  ],
  "input_amount": "1.0",
  "input_token": "ETH",
  "output_amount": "1.0125",
  "output_token": "ETH",
  "profit_percentage": "1.25",
  "profit_usd": "42.15",
  "gas_cost_usd": "12.34",
  "net_profit_usd": "29.81",
  "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
  "block_number": 12345678,
  "timestamp": 1619123456,
  "dexes": ["uniswap_v3", "sushiswap", "uniswap_v3"],
  "networks": ["ethereum"],
  "execution_time_ms": 234,
  "steps": [
    {
      "dex": "uniswap_v3",
      "action": "swap",
      "input_token": "ETH",
      "output_token": "USDC",
      "input_amount": "1.0",
      "output_amount": "3500.12",
      "fee_tier": "0.3",
      "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    },
    {
      "dex": "sushiswap",
      "action": "swap",
      "input_token": "USDC",
      "output_token": "WBTC",
      "input_amount": "3500.12",
      "output_amount": "0.0625",
      "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    },
    {
      "dex": "uniswap_v3",
      "action": "swap",
      "input_token": "WBTC",
      "output_token": "ETH",
      "input_amount": "0.0625",
      "output_amount": "1.0125",
      "fee_tier": "0.3",
      "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    }
  ],
  "flash_loan": {
    "provider": "aave",
    "token": "ETH",
    "amount": "1.0",
    "fee": "0.0009",
    "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  },
  "mev_protection": {
    "provider": "flashbots",
    "bundle_type": "standard",
    "bundle_id": "0x9876543210abcdef9876543210abcdef9876543210abcdef9876543210abcdef"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the trade |
| `opportunity_id` | string | ID of the opportunity that led to this trade |
| `status` | string | Trade status (success, failed, pending) |
| `path` | array of strings | Token symbols in the arbitrage path |
| `addresses` | array of strings | Token addresses in the arbitrage path |
| `input_amount` | string | Input amount for the trade |
| `input_token` | string | Input token symbol |
| `output_amount` | string | Output amount from the trade |
| `output_token` | string | Output token symbol |
| `profit_percentage` | string | Actual profit as a percentage |
| `profit_usd` | string | Actual profit in USD |
| `gas_cost_usd` | string | Actual gas cost in USD |
| `net_profit_usd` | string | Net profit after gas costs in USD |
| `transaction_hash` | string | Hash of the transaction |
| `block_number` | integer | Block number where the transaction was included |
| `timestamp` | integer | Timestamp when the trade was executed |
| `dexes` | array of strings | DEXs used in the trade |
| `networks` | array of strings | Blockchain networks involved |
| `execution_time_ms` | integer | Time taken to execute the trade in milliseconds |
| `steps` | array of objects | Detailed steps of the trade execution |
| `flash_loan` | object | Flash loan details (if used) |
| `mev_protection` | object | MEV protection details (if used) |

### WalletBalance

Represents the balance of a wallet.

```json
{
  "address": "0x1234567890abcdef1234567890abcdef12345678",
  "balances": [
    {
      "token": "ETH",
      "address": "0x0000000000000000000000000000000000000000",
      "balance": "1.234",
      "usd_value": "4321.23"
    },
    {
      "token": "USDC",
      "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "balance": "1000.00",
      "usd_value": "1000.00"
    }
  ],
  "total_usd_value": "5321.23",
  "timestamp": 1619123456
}
```

| Field | Type | Description |
|-------|------|-------------|
| `address` | string | Wallet address |
| `balances` | array of objects | Token balances |
| `total_usd_value` | string | Total value in USD |
| `timestamp` | integer | Timestamp when the balance was checked |

### SystemStatus

Represents the current status of the bot system.

```json
{
  "status": "running",
  "uptime": 3600,
  "version": "1.2.3",
  "components": {
    "arbitrage_engine": "running",
    "market_monitor": "running",
    "transaction_manager": "running",
    "api_server": "running",
    "dashboard": "running"
  },
  "last_trade_timestamp": 1619123456,
  "connected_dexes": ["pancakeswap", "uniswap_v3", "swapbased"],
  "active_networks": ["ethereum", "bsc"],
  "system_metrics": {
    "cpu_usage": "45.2",
    "memory_usage": "1.2",
    "disk_usage": "23.4",
    "network_in": "1.5",
    "network_out": "0.8"
  },
  "trading_metrics": {
    "opportunities_found_24h": 450,
    "trades_executed_24h": 120,
    "success_rate_24h": "95.83",
    "profit_24h_usd": "1234.56"
  },
  "alerts": [
    {
      "level": "warning",
      "message": "High gas prices on Ethereum network",
      "timestamp": 1619123456
    }
  ],
  "timestamp": 1619123456
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Overall system status |
| `uptime` | integer | System uptime in seconds |
| `version` | string | Bot version |
| `components` | object | Status of individual components |
| `last_trade_timestamp` | integer | Timestamp of the last trade |
| `connected_dexes` | array of strings | Connected DEXs |
| `active_networks` | array of strings | Active blockchain networks |
| `system_metrics` | object | System resource metrics |
| `trading_metrics` | object | Trading performance metrics |
| `alerts` | array of objects | Active system alerts |
| `timestamp` | integer | Timestamp when the status was checked |

### Configuration

Represents the bot configuration.

```json
{
  "trading": {
    "enabled": true,
    "min_profit_threshold": "0.5",
    "max_slippage": "1.0",
    "gas_price_multiplier": "1.1",
    "max_trade_amount": "1.0",
    "min_liquidity": "10000",
    "max_path_length": 3,
    "execution_timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 5
  },
  "dexes": [
    {
      "name": "pancakeswap",
      "network": "bsc",
      "enabled": true,
      "fee_tiers": ["0.25"]
    },
    {
      "name": "uniswap_v3",
      "network": "ethereum",
      "enabled": true,
      "fee_tiers": ["0.05", "0.3", "1.0"]
    }
  ],
  "networks": [
    {
      "name": "ethereum",
      "enabled": true,
      "gas_limit": 500000,
      "priority_fee": "1.5"
    },
    {
      "name": "bsc",
      "enabled": true,
      "gas_limit": 500000,
      "priority_fee": "1.0"
    }
  ],
  "mev_protection": {
    "enabled": true,
    "provider": "flashbots",
    "min_block_confirmations": 1,
    "max_block_confirmations": 3,
    "priority_fee_percentage": 90
  },
  "flash_loans": {
    "enabled": true,
    "provider": "aave",
    "max_loan_amount": "100",
    "fee_percentage": "0.09"
  },
  "last_updated": 1619123456,
  "updated_by": "admin"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `trading` | object | Trading configuration |
| `dexes` | array of objects | DEX configurations |
| `networks` | array of objects | Network configurations |
| `mev_protection` | object | MEV protection configuration |
| `flash_loans` | object | Flash loan configuration |
| `last_updated` | integer | Timestamp of the last update |
| `updated_by` | string | User who last updated the configuration |

### User

Represents a user of the system.

```json
{
  "id": "user-123",
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin",
  "permissions": ["read", "write", "execute", "configure"],
  "last_login": 1619123456,
  "created_at": 1609459256,
  "api_keys": [
    {
      "id": "key-456",
      "name": "Dashboard API",
      "last_used": 1619123456,
      "created_at": 1609459256,
      "expires_at": 1640995256
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the user |
| `username` | string | Username |
| `email` | string | Email address |
| `role` | string | User role (admin, operator, viewer) |
| `permissions` | array of strings | User permissions |
| `last_login` | integer | Timestamp of the last login |
| `created_at` | integer | Timestamp when the user was created |
| `api_keys` | array of objects | API keys associated with the user |

## Dashboard Models

### DashboardMetrics

Represents metrics for the dashboard.

```json
{
  "trading": {
    "total_trades": 120,
    "successful_trades": 115,
    "failed_trades": 5,
    "total_profit_usd": "1234.56",
    "total_gas_cost_usd": "345.67",
    "net_profit_usd": "888.89",
    "average_profit_per_trade_usd": "7.73",
    "success_rate": "95.83",
    "roi_percentage": "12.34"
  },
  "performance": {
    "average_execution_time_ms": 234,
    "average_block_time_s": 12.5,
    "average_confirmation_time_s": 38.2,
    "opportunities_found": 450,
    "opportunities_executed": 120,
    "execution_rate": "26.67",
    "average_gas_price_gwei": "25.4"
  },
  "system": {
    "uptime": 86400,
    "cpu_usage": "45.2",
    "memory_usage": "1.2",
    "disk_usage": "23.4",
    "api_requests": 1234,
    "active_connections": 5
  },
  "tokens": {
    "most_profitable": "ETH",
    "most_traded": "USDC",
    "highest_volume": "WBTC",
    "total_tokens": 45
  },
  "dexes": {
    "most_profitable": "uniswap_v3",
    "most_used": "pancakeswap",
    "highest_volume": "uniswap_v3",
    "total_dexes": 5
  },
  "networks": {
    "most_profitable": "ethereum",
    "most_active": "bsc",
    "highest_gas_cost": "ethereum",
    "total_networks": 2
  },
  "timeframe": "24h",
  "timestamp": 1619123456
}
```

| Field | Type | Description |
|-------|------|-------------|
| `trading` | object | Trading metrics |
| `performance` | object | Performance metrics |
| `system` | object | System metrics |
| `tokens` | object | Token metrics |
| `dexes` | object | DEX metrics |
| `networks` | object | Network metrics |
| `timeframe` | string | Timeframe for the metrics |
| `timestamp` | integer | Timestamp when the metrics were collected |

### ChartData

Represents data for a dashboard chart.

```json
{
  "chart": "profit_history",
  "timeframe": "24h",
  "resolution": "1h",
  "series": [
    {
      "name": "Gross Profit",
      "data": [
        [1619037056, "12.34"],
        [1619040656, "23.45"],
        [1619044256, "34.56"]
      ]
    },
    {
      "name": "Gas Cost",
      "data": [
        [1619037056, "3.45"],
        [1619040656, "4.56"],
        [1619044256, "5.67"]
      ]
    },
    {
      "name": "Net Profit",
      "data": [
        [1619037056, "8.89"],
        [1619040656, "18.89"],
        [1619044256, "28.89"]
      ]
    }
  ],
  "timestamp": 1619123456
}
```

| Field | Type | Description |
|-------|------|-------------|
| `chart` | string | Chart type |
| `timeframe` | string | Timeframe for the chart data |
| `resolution` | string | Data point resolution |
| `series` | array of objects | Chart series data |
| `timestamp` | integer | Timestamp when the data was collected |

### Alert

Represents a system alert.

```json
{
  "id": "alert-123",
  "level": "warning",
  "category": "system",
  "message": "High gas prices on Ethereum network",
  "details": {
    "current_gas_price": "150",
    "threshold": "100",
    "network": "ethereum"
  },
  "timestamp": 1619123456,
  "acknowledged": false,
  "acknowledged_by": null,
  "acknowledged_at": null,
  "resolved": false,
  "resolved_at": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the alert |
| `level` | string | Alert level (info, warning, error, critical) |
| `category` | string | Alert category (system, trading, security) |
| `message` | string | Alert message |
| `details` | object | Additional alert details |
| `timestamp` | integer | Timestamp when the alert was generated |
| `acknowledged` | boolean | Whether the alert has been acknowledged |
| `acknowledged_by` | string | User who acknowledged the alert |
| `acknowledged_at` | integer | Timestamp when the alert was acknowledged |
| `resolved` | boolean | Whether the alert has been resolved |
| `resolved_at` | integer | Timestamp when the alert was resolved |

## Error Models

### Error

Represents an API error.

```json
{
  "code": "AUTHENTICATION_REQUIRED",
  "message": "Authentication is required for this endpoint",
  "details": {
    "required_permissions": ["read", "write"]
  },
  "timestamp": 1619123456,
  "request_id": "req-123456"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `code` | string | Error code |
| `message` | string | Error message |
| `details` | object | Additional error details |
| `timestamp` | integer | Timestamp when the error occurred |
| `request_id` | string | Unique identifier for the request |

## Webhook Models

### WebhookPayload

Represents a webhook notification payload.

```json
{
  "event": "trade_executed",
  "timestamp": 1619123456,
  "data": {
    "trade_id": "trade-123456",
    "status": "success",
    "profit_usd": "42.15",
    "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | Event type |
| `timestamp` | integer | Timestamp when the event occurred |
| `data` | object | Event-specific data |

### WebhookConfiguration

Represents a webhook configuration.

```json
{
  "id": "webhook-123",
  "url": "https://example.com/webhook",
  "events": ["trade_executed", "trade_failed", "opportunity_found"],
  "secret": "your_webhook_secret",
  "active": true,
  "created_at": 1609459256,
  "created_by": "admin",
  "last_triggered": 1619123456,
  "success_count": 120,
  "failure_count": 5
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier for the webhook |
| `url` | string | Webhook URL |
| `events` | array of strings | Events to trigger the webhook |
| `secret` | string | Webhook secret for signature verification |
| `active` | boolean | Whether the webhook is active |
| `created_at` | integer | Timestamp when the webhook was created |
| `created_by` | string | User who created the webhook |
| `last_triggered` | integer | Timestamp when the webhook was last triggered |
| `success_count` | integer | Number of successful webhook deliveries |
| `failure_count` | integer | Number of failed webhook deliveries |
