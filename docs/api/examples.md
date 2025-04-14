# Listonian Bot API Examples

This document provides practical examples of using the Listonian Bot API for common tasks.

## Authentication

### Obtaining an API Key

API keys can be generated in the dashboard under Settings > API Keys.

### Using API Keys

Include your API key in the request header:

```bash
curl -X GET "http://your-server:8000/api/v1/status" \
  -H "X-API-KEY: your_api_key_here"
```

### JWT Authentication (Dashboard API)

First, obtain a JWT token:

```bash
curl -X POST "http://your-server:8000/dashboard/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your_password_here"
  }'
```

Response:
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

Then use the token in subsequent requests:

```bash
curl -X GET "http://your-server:8000/dashboard/api/v1/metrics" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## System Status

### Get System Status

```bash
curl -X GET "http://your-server:8000/api/v1/status" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
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

## Arbitrage Opportunities

### Get Current Opportunities

```bash
curl -X GET "http://your-server:8000/api/v1/opportunities?min_profit=0.8&max_slippage=0.5&limit=2" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
```json
{
  "success": true,
  "data": {
    "opportunities": [
      {
        "id": "opp-123456",
        "path": ["ETH", "USDC", "WBTC", "ETH"],
        "addresses": [
          "0x0000000000000000000000000000000000000000",
          "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
          "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
          "0x0000000000000000000000000000000000000000"
        ],
        "expected_profit_percentage": 1.25,
        "expected_profit_usd": 42.15,
        "input_amount": "1.0",
        "input_token": "ETH",
        "estimated_gas_cost_usd": 12.34,
        "net_profit_usd": 29.81,
        "dexes": ["uniswap_v3", "sushiswap", "uniswap_v3"],
        "timestamp": 1619123456,
        "risk_score": 2
      },
      {
        "id": "opp-123457",
        "path": ["USDC", "WETH", "DAI", "USDC"],
        "addresses": [
          "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
          "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
          "0x6B175474E89094C44Da98b954EedeAC495271d0F",
          "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        ],
        "expected_profit_percentage": 0.95,
        "expected_profit_usd": 38.25,
        "input_amount": "4000.0",
        "input_token": "USDC",
        "estimated_gas_cost_usd": 10.45,
        "net_profit_usd": 27.80,
        "dexes": ["uniswap_v3", "curve", "uniswap_v3"],
        "timestamp": 1619123486,
        "risk_score": 1
      }
    ],
    "total_count": 2,
    "timestamp": 1619123456
  },
  "error": null
}
```

## Trade History

### Get Recent Trades

```bash
curl -X GET "http://your-server:8000/api/v1/trades?limit=2&status=success" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
```json
{
  "success": true,
  "data": {
    "trades": [
      {
        "id": "trade-123456",
        "opportunity_id": "opp-123456",
        "status": "success",
        "path": ["ETH", "USDC", "WBTC", "ETH"],
        "input_amount": "1.0",
        "input_token": "ETH",
        "output_amount": "1.0125",
        "output_token": "ETH",
        "profit_percentage": 1.25,
        "profit_usd": 42.15,
        "gas_cost_usd": 12.34,
        "net_profit_usd": 29.81,
        "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "block_number": 12345678,
        "timestamp": 1619123456,
        "dexes": ["uniswap_v3", "sushiswap", "uniswap_v3"]
      },
      {
        "id": "trade-123457",
        "opportunity_id": "opp-123457",
        "status": "success",
        "path": ["USDC", "WETH", "DAI", "USDC"],
        "input_amount": "4000.0",
        "input_token": "USDC",
        "output_amount": "4038.0",
        "output_token": "USDC",
        "profit_percentage": 0.95,
        "profit_usd": 38.25,
        "gas_cost_usd": 10.45,
        "net_profit_usd": 27.80,
        "transaction_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "block_number": 12345679,
        "timestamp": 1619123486,
        "dexes": ["uniswap_v3", "curve", "uniswap_v3"]
      }
    ],
    "total_count": 2
  },
  "error": null
}
```

### Get Trade Details

```bash
curl -X GET "http://your-server:8000/api/v1/trades/trade-123456" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
```json
{
  "success": true,
  "data": {
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
    "profit_percentage": 1.25,
    "profit_usd": 42.15,
    "gas_cost_usd": 12.34,
    "net_profit_usd": 29.81,
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
  },
  "error": null
}
```

## Wallet Balance

### Get Wallet Balance

```bash
curl -X GET "http://your-server:8000/api/v1/balance" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
```json
{
  "success": true,
  "data": {
    "address": "0x1234567890abcdef1234567890abcdef12345678",
    "balances": [
      {
        "token": "ETH",
        "address": "0x0000000000000000000000000000000000000000",
        "balance": "1.234",
        "usd_value": 4321.23
      },
      {
        "token": "USDC",
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
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

## Execute Trade

### Execute a Trade

```bash
curl -X POST "http://your-server:8000/api/v1/execute" \
  -H "X-API-KEY: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "opportunity_id": "opp-123456",
    "slippage": 0.5
  }'
```

Response:
```json
{
  "success": true,
  "data": {
    "trade_id": "trade-123456",
    "status": "pending",
    "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
    "estimated_completion_time": 1619123486
  },
  "error": null
}
```

## Bot Configuration

### Get Configuration

```bash
curl -X GET "http://your-server:8000/api/v1/config" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
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

### Update Configuration

```bash
curl -X PATCH "http://your-server:8000/api/v1/config" \
  -H "X-API-KEY: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

Response:
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

## Dashboard API Examples

### Get Dashboard Metrics

```bash
curl -X GET "http://your-server:8000/dashboard/api/v1/metrics?timeframe=24h" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Response:
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

### Get Chart Data

```bash
curl -X GET "http://your-server:8000/dashboard/api/v1/charts?chart=profit_history&timeframe=24h&resolution=1h" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Response:
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
          [1619044256, 34.56]
        ]
      },
      {
        "name": "Gas Cost",
        "data": [
          [1619037056, 3.45],
          [1619040656, 4.56],
          [1619044256, 5.67]
        ]
      },
      {
        "name": "Net Profit",
        "data": [
          [1619037056, 8.89],
          [1619040656, 18.89],
          [1619044256, 28.89]
        ]
      }
    ],
    "timestamp": 1619123456
  },
  "error": null
}
```

### Get Token Information

```bash
curl -X GET "http://your-server:8000/dashboard/api/v1/tokens?limit=2&sort_by=profit&order=desc" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Response:
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
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
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

## Error Handling

### Authentication Error

```bash
curl -X GET "http://your-server:8000/api/v1/status"
```

Response:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "AUTHENTICATION_REQUIRED",
    "message": "Authentication is required for this endpoint"
  }
}
```

### Invalid Parameters

```bash
curl -X GET "http://your-server:8000/api/v1/opportunities?min_profit=invalid" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_PARAMETERS",
    "message": "Invalid value for parameter 'min_profit': must be a number"
  }
}
```

### Resource Not Found

```bash
curl -X GET "http://your-server:8000/api/v1/trades/non-existent-trade" \
  -H "X-API-KEY: your_api_key_here"
```

Response:
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Trade with ID 'non-existent-trade' not found"
  }
}
```

## Using the API with Programming Languages

### Python Example

```python
import requests
import json

API_URL = "http://your-server:8000/api/v1"
API_KEY = "your_api_key_here"

headers = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# Get system status
response = requests.get(f"{API_URL}/status", headers=headers)
status_data = response.json()
print(f"System status: {status_data['data']['status']}")

# Get current opportunities
params = {
    "min_profit": 0.5,
    "max_slippage": 1.0,
    "limit": 5
}
response = requests.get(f"{API_URL}/opportunities", headers=headers, params=params)
opportunities = response.json()
print(f"Found {len(opportunities['data']['opportunities'])} opportunities")

# Execute a trade
if len(opportunities['data']['opportunities']) > 0:
    opportunity_id = opportunities['data']['opportunities'][0]['id']
    trade_data = {
        "opportunity_id": opportunity_id,
        "slippage": 0.5
    }
    response = requests.post(f"{API_URL}/execute", headers=headers, json=trade_data)
    trade_result = response.json()
    print(f"Trade execution: {trade_result['data']['status']}")
```

### JavaScript Example

```javascript
const axios = require('axios');

const API_URL = 'http://your-server:8000/api/v1';
const API_KEY = 'your_api_key_here';

const headers = {
  'X-API-KEY': API_KEY,
  'Content-Type': 'application/json'
};

// Get system status
axios.get(`${API_URL}/status`, { headers })
  .then(response => {
    console.log(`System status: ${response.data.data.status}`);
  })
  .catch(error => {
    console.error('Error fetching system status:', error.response?.data || error.message);
  });

// Get current opportunities
const params = {
  min_profit: 0.5,
  max_slippage: 1.0,
  limit: 5
};

axios.get(`${API_URL}/opportunities`, { headers, params })
  .then(response => {
    const opportunities = response.data.data.opportunities;
    console.log(`Found ${opportunities.length} opportunities`);
    
    // Execute a trade
    if (opportunities.length > 0) {
      const opportunityId = opportunities[0].id;
      const tradeData = {
        opportunity_id: opportunityId,
        slippage: 0.5
      };
      
      return axios.post(`${API_URL}/execute`, tradeData, { headers });
    }
  })
  .then(response => {
    if (response) {
      console.log(`Trade execution: ${response.data.data.status}`);
    }
  })
  .catch(error => {
    console.error('Error:', error.response?.data || error.message);
  });
```

## Webhook Integration

### Setting Up a Webhook

```bash
curl -X POST "http://your-server:8000/api/v1/webhooks" \
  -H "X-API-KEY: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/webhook",
    "events": ["trade_executed", "trade_failed", "opportunity_found"],
    "secret": "your_webhook_secret"
  }'
```

Response:
```json
{
  "success": true,
  "data": {
    "id": "webhook-123",
    "url": "https://example.com/webhook",
    "events": ["trade_executed", "trade_failed", "opportunity_found"],
    "active": true,
    "created_at": 1619123456
  },
  "error": null
}
```

### Webhook Payload Example

When a trade is executed, your webhook endpoint will receive a POST request with a payload like this:

```json
{
  "event": "trade_executed",
  "timestamp": 1619123456,
  "data": {
    "trade_id": "trade-123456",
    "status": "success",
    "profit_usd": 42.15,
    "transaction_hash": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
  }
}
```

### Verifying Webhook Signatures

Webhook requests include a signature in the `X-Webhook-Signature` header. You should verify this signature to ensure the request is authentic:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    computed_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed_signature, signature)

# In your webhook handler
def webhook_handler(request):
    payload = request.body
    signature = request.headers.get('X-Webhook-Signature')
    secret = 'your_webhook_secret'
    
    if not verify_signature(payload, signature, secret):
        return {'error': 'Invalid signature'}, 401
    
    # Process the webhook
    data = json.loads(payload)
    event = data['event']
    
    if event == 'trade_executed':
        # Handle trade execution
        pass
    elif event == 'trade_failed':
        # Handle trade failure
        pass
    
    return {'status': 'success'}, 200
```
