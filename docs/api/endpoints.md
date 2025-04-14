# Listonian Bot API Endpoints

This document provides detailed information about the available API endpoints in the Listonian Bot system.

## Authentication

Most API endpoints require authentication. Include your API key in the request header:

```
X-API-KEY: your_api_key_here
```

For dashboard endpoints, use JWT authentication:

```
Authorization: Bearer your_jwt_token_here
```

## Base URLs

- **Bot API**: `http://your-server:8000/api/v1`
- **Dashboard API**: `http://your-server:8000/dashboard/api/v1`

## Response Format

All API responses are in JSON format with the following structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Or in case of an error:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error message description"
  }
}
```

## Rate Limiting

API requests are rate-limited to protect the system from abuse. The default limits are:

- 100 requests per minute for authenticated users
- 10 requests per minute for unauthenticated users

Rate limit information is included in the response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1619123456
```

## Bot API Endpoints

### System Status

#### GET /status

Returns the current status of the bot system.

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "running",
    "uptime": 3600,
    "version": "1.2.3",
    "components": {
      "arbitrage_engine": "running",
      "market_monitor": "running",
      "transaction_manager": "running"
    },
    "last_trade_timestamp": 1619123456,
    "connected_dexes": ["pancakeswap", "uniswap_v3", "swapbased"]
  },
  "error": null
}
```

### Arbitrage Opportunities

#### GET /opportunities

Returns a list of current arbitrage opportunities.

**Parameters**:
- `min_profit` (optional): Minimum profit percentage (default: 0.5)
- `max_slippage` (optional): Maximum slippage percentage (default: 1.0)
- `limit` (optional): Maximum number of opportunities to return (default: 10)
- `network` (optional): Filter by blockchain network (e.g., "ethereum", "bsc")

**Response**:
```json
{
  "success": true,
  "data": {
    "opportunities": [
      {
        "id": "opp-123456",
        "path": ["TOKEN_A", "TOKEN_B", "TOKEN_C"],
        "addresses": [
          "0x123...",
          "0x456...",
          "0x789..."
        ],
        "expected_profit_percentage": 1.25,
        "expected_profit_usd": 42.15,
        "input_amount": "1.0",
        "input_token": "TOKEN_A",
        "estimated_gas_cost_usd": 12.34,
        "net_profit_usd": 29.81,
        "dexes": ["pancakeswap", "uniswap_v3"],
        "timestamp": 1619123456,
        "risk_score": 2
      }
    ],
    "total_count": 1,
    "timestamp": 1619123456
  },
  "error": null
}
```

### Trade History

#### GET /trades

Returns the history of executed trades.

**Parameters**:
- `limit` (optional): Maximum number of trades to return (default: 10)
- `offset` (optional): Number of trades to skip (default: 0)
- `status` (optional): Filter by status (e.g., "success", "failed", "pending")
- `start_time` (optional): Filter trades after this timestamp
- `end_time` (optional): Filter trades before this timestamp

**Response**:
```json
{
  "success": true,
  "data": {
    "trades": [
      {
        "id": "trade-123456",
        "opportunity_id": "opp-123456",
        "status": "success",
        "path": ["TOKEN_A", "TOKEN_B", "TOKEN_C"],
        "addresses": [
          "0x123...",
          "0x456...",
          "0x789..."
        ],
        "input_amount": "1.0",
        "input_token": "TOKEN_A",
        "output_amount": "1.0125",
        "output_token": "TOKEN_A",
        "profit_percentage": 1.25,
        "profit_usd": 42.15,
        "gas_cost_usd": 12.34,
        "net_profit_usd": 29.81,
        "transaction_hash": "0xabc...",
        "block_number": 12345678,
        "timestamp": 1619123456,
        "dexes": ["pancakeswap", "uniswap_v3"]
      }
    ],
    "total_count": 1
  },
  "error": null
}
```

### Wallet Balance

#### GET /balance

Returns the current balance of the trading wallet.

**Parameters**:
- `address` (optional): Wallet address to check (defaults to bot's wallet)
- `tokens` (optional): Comma-separated list of token addresses to check

**Response**:
```json
{
  "success": true,
  "data": {
    "address": "0xabc...",
    "balances": [
      {
        "token": "ETH",
        "address": "0x0000000000000000000000000000000000000000",
        "balance": "1.234",
        "usd_value": 4321.23
      },
      {
        "token": "USDC",
        "address": "0xa0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "balance": "1000.00",
        "usd_value": 1000.00
      }
    ],
    "total_usd_value": 5321.23,
    "timestamp": 1619123456
  },
  "error": null
}
```

### Execute Trade

#### POST /execute

Manually executes a trade based on an opportunity ID.

**Parameters**:
- `opportunity_id`: ID of the opportunity to execute
- `wallet_address` (optional): Wallet address to use (defaults to bot's wallet)
- `slippage` (optional): Maximum slippage percentage (default: 1.0)

**Request Body**:
```json
{
  "opportunity_id": "opp-123456",
  "slippage": 0.5
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "trade_id": "trade-123456",
    "status": "pending",
    "transaction_hash": "0xabc...",
    "estimated_completion_time": 1619123486
  },
  "error": null
}
```

### Bot Configuration

#### GET /config

Returns the current bot configuration.

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "trading": {
      "enabled": true,
      "min_profit_threshold": 0.5,
      "max_slippage": 1.0,
      "gas_price_multiplier": 1.1,
      "max_trade_amount": 1.0
    },
    "dexes": [
      {
        "name": "pancakeswap",
        "enabled": true
      },
      {
        "name": "uniswap_v3",
        "enabled": true
      }
    ],
    "networks": [
      {
        "name": "ethereum",
        "enabled": true
      },
      {
        "name": "bsc",
        "enabled": true
      }
    ],
    "mev_protection": {
      "enabled": true,
      "provider": "flashbots"
    },
    "flash_loans": {
      "enabled": true,
      "provider": "aave"
    }
  },
  "error": null
}
```

#### PATCH /config

Updates the bot configuration.

**Request Body**:
```json
{
  "trading": {
    "enabled": false,
    "min_profit_threshold": 0.8
  },
  "dexes": [
    {
      "name": "pancakeswap",
      "enabled": false
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "updated": ["trading.enabled", "trading.min_profit_threshold", "dexes[0].enabled"],
    "timestamp": 1619123456
  },
  "error": null
}
```

## Dashboard API Endpoints

### Dashboard Metrics

#### GET /dashboard/metrics

Returns metrics for the dashboard.

**Parameters**:
- `timeframe` (optional): Timeframe for metrics (e.g., "1h", "24h", "7d", "30d", default: "24h")

**Response**:
```json
{
  "success": true,
  "data": {
    "trading": {
      "total_trades": 120,
      "successful_trades": 115,
      "failed_trades": 5,
      "total_profit_usd": 1234.56,
      "total_gas_cost_usd": 345.67,
      "net_profit_usd": 888.89,
      "average_profit_per_trade_usd": 7.73,
      "success_rate": 95.83
    },
    "performance": {
      "average_execution_time_ms": 234,
      "average_block_time_s": 12.5,
      "average_confirmation_time_s": 38.2,
      "opportunities_found": 450,
      "opportunities_executed": 120,
      "execution_rate": 26.67
    },
    "system": {
      "uptime": 86400,
      "cpu_usage": 45.2,
      "memory_usage": 1.2,
      "disk_usage": 23.4,
      "api_requests": 1234
    },
    "timestamp": 1619123456
  },
  "error": null
}
```

### Dashboard Charts Data

#### GET /dashboard/charts

Returns data for dashboard charts.

**Parameters**:
- `chart` (required): Chart type (e.g., "profit_history", "gas_cost", "trade_volume")
- `timeframe` (optional): Timeframe for chart data (e.g., "1h", "24h", "7d", "30d", default: "24h")
- `resolution` (optional): Data point resolution (e.g., "1m", "5m", "1h", "1d", default depends on timeframe)

**Response**:
```json
{
  "success": true,
  "data": {
    "chart": "profit_history",
    "timeframe": "24h",
    "resolution": "1h",
    "series": [
      {
        "name": "Gross Profit",
        "data": [
          [1619037056, 12.34],
          [1619040656, 23.45],
          [1619044256, 34.56],
          // ... more data points
        ]
      },
      {
        "name": "Gas Cost",
        "data": [
          [1619037056, 3.45],
          [1619040656, 4.56],
          [1619044256, 5.67],
          // ... more data points
        ]
      },
      {
        "name": "Net Profit",
        "data": [
          [1619037056, 8.89],
          [1619040656, 18.89],
          [1619044256, 28.89],
          // ... more data points
        ]
      }
    ],
    "timestamp": 1619123456
  },
  "error": null
}
```

### Token Information

#### GET /dashboard/tokens

Returns information about tokens used by the bot.

**Parameters**:
- `limit` (optional): Maximum number of tokens to return (default: 10)
- `offset` (optional): Number of tokens to skip (default: 0)
- `sort_by` (optional): Field to sort by (e.g., "volume", "profit", "trades", default: "volume")
- `order` (optional): Sort order (e.g., "asc", "desc", default: "desc")

**Response**:
```json
{
  "success": true,
  "data": {
    "tokens": [
      {
        "symbol": "ETH",
        "name": "Ethereum",
        "address": "0x0000000000000000000000000000000000000000",
        "decimals": 18,
        "price_usd": 3500.12,
        "volume_24h_usd": 1234567.89,
        "trades_count": 45,
        "profit_usd": 123.45,
        "networks": ["ethereum"]
      },
      {
        "symbol": "USDC",
        "name": "USD Coin",
        "address": "0xa0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "decimals": 6,
        "price_usd": 1.00,
        "volume_24h_usd": 987654.32,
        "trades_count": 38,
        "profit_usd": 98.76,
        "networks": ["ethereum", "bsc"]
      }
    ],
    "total_count": 2,
    "timestamp": 1619123456
  },
  "error": null
}
```

### User Management

#### POST /dashboard/users/login

Authenticates a user and returns a JWT token.

**Request Body**:
```json
{
  "username": "admin",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": 1619209856,
    "user": {
      "id": "user-123",
      "username": "admin",
      "role": "admin",
      "last_login": 1619123456
    }
  },
  "error": null
}
```

#### GET /dashboard/users/me

Returns information about the currently authenticated user.

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "id": "user-123",
    "username": "admin",
    "role": "admin",
    "email": "admin@example.com",
    "last_login": 1619123456,
    "created_at": 1609459256
  },
  "error": null
}
```

#### POST /dashboard/users/logout

Logs out the current user by invalidating their token.

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": {
    "message": "Successfully logged out"
  },
  "error": null
}
```

## Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_REQUIRED` | Authentication is required for this endpoint |
| `INVALID_API_KEY` | The provided API key is invalid |
| `INVALID_TOKEN` | The provided JWT token is invalid or expired |
| `RATE_LIMIT_EXCEEDED` | You have exceeded the rate limit for this endpoint |
| `INVALID_PARAMETERS` | One or more parameters are invalid |
| `RESOURCE_NOT_FOUND` | The requested resource was not found |
| `INSUFFICIENT_PERMISSIONS` | You do not have permission to access this resource |
| `INTERNAL_SERVER_ERROR` | An internal server error occurred |
| `SERVICE_UNAVAILABLE` | The service is temporarily unavailable |
| `OPPORTUNITY_EXPIRED` | The arbitrage opportunity has expired |
| `INSUFFICIENT_FUNDS` | Insufficient funds to execute the trade |
| `EXECUTION_FAILED` | Trade execution failed |

## Webhook Notifications

The API can send webhook notifications for various events. Configure webhooks in the dashboard settings.

### Webhook Payload Format

```json
{
  "event": "trade_executed",
  "timestamp": 1619123456,
  "data": {
    // Event-specific data
  }
}
```

### Webhook Events

| Event | Description |
|-------|-------------|
| `trade_executed` | A trade has been executed |
| `trade_failed` | A trade has failed |
| `opportunity_found` | A new arbitrage opportunity has been found |
| `balance_low` | Wallet balance is below the configured threshold |
| `system_status_changed` | System status has changed |
| `error_occurred` | An error has occurred |
