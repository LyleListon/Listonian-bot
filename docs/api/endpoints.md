# API Documentation

## Overview
The API provides access to the arbitrage bot's functionality, monitoring, and control features.

## Base URL
```
http://localhost:5001/api/v1
```

## Authentication
```http
Authorization: Bearer <api-key>
```

## REST Endpoints

### System Status

#### GET /status
Get current system status.

```http
GET /api/v1/status
```

Response:
```json
{
  "status": "running",
  "uptime": "2d 3h 45m",
  "version": "1.0.0",
  "health": {
    "blockchain": "connected",
    "monitoring": "active",
    "trading": "enabled"
  }
}
```

### Trading

#### GET /opportunities
Get current arbitrage opportunities.

```http
GET /api/v1/opportunities
```

Response:
```json
{
  "opportunities": [
    {
      "id": "opp-123",
      "path": ["WETH", "USDC", "DAI"],
      "profit": "5.23",
      "currency": "USDC",
      "confidence": 0.95,
      "timestamp": "2025-02-10T05:52:00Z"
    }
  ],
  "total": 1
}
```

#### POST /trading/start
Start trading operations.

```http
POST /api/v1/trading/start
```

Request:
```json
{
  "pairs": ["WETH-USDC", "USDC-DAI"],
  "min_profit": 5.0
}
```

Response:
```json
{
  "status": "started",
  "timestamp": "2025-02-10T05:52:00Z",
  "config": {
    "pairs": ["WETH-USDC", "USDC-DAI"],
    "min_profit": 5.0
  }
}
```

### Monitoring

#### GET /metrics
Get system metrics.

```http
GET /api/v1/metrics
```

Response:
```json
{
  "system": {
    "cpu_usage": 45.2,
    "memory_usage": 512.3,
    "disk_usage": 78.5
  },
  "trading": {
    "opportunities_found": 156,
    "trades_executed": 23,
    "success_rate": 95.6
  },
  "network": {
    "latency": 120,
    "requests_per_second": 45
  }
}
```

#### GET /alerts
Get system alerts.

```http
GET /api/v1/alerts
```

Response:
```json
{
  "alerts": [
    {
      "id": "alert-123",
      "level": "warning",
      "message": "High gas prices detected",
      "timestamp": "2025-02-10T05:52:00Z"
    }
  ],
  "total": 1
}
```

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8772/ws');
```

### Authentication
```javascript
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your-api-key'
}));
```

### Subscriptions

#### Price Updates
```javascript
// Subscribe
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'prices',
  pairs: ['WETH-USDC', 'USDC-DAI']
}));

// Message Format
{
  "type": "price_update",
  "data": {
    "pair": "WETH-USDC",
    "price": "1850.45",
    "timestamp": "2025-02-10T05:52:00Z"
  }
}
```

#### Opportunity Updates
```javascript
// Subscribe
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'opportunities'
}));

// Message Format
{
  "type": "opportunity",
  "data": {
    "id": "opp-123",
    "path": ["WETH", "USDC", "DAI"],
    "profit": "5.23",
    "timestamp": "2025-02-10T05:52:00Z"
  }
}
```

## Error Handling

### HTTP Status Codes
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Too Many Requests
- 500: Internal Server Error

### Error Response Format
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": {
      "limit": 100,
      "reset": "2025-02-10T06:52:00Z"
    }
  }
}
```

## Rate Limiting
- Default: 100 requests per minute
- Websocket: 10 subscriptions per connection
- Headers:
  * X-RateLimit-Limit
  * X-RateLimit-Remaining
  * X-RateLimit-Reset

## Data Models

### Opportunity
```typescript
interface Opportunity {
  id: string;
  path: string[];
  profit: string;
  currency: string;
  confidence: number;
  timestamp: string;
}
```

### Alert
```typescript
interface Alert {
  id: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  timestamp: string;
}
```

Last Updated: 2025-02-10