Dashboard Integration Guide

## Overview
The dashboard provides real-time monitoring of market data, price feeds, and system performance through WebSocket integration.

## Architecture

### Data Flow
```
Market Analyzer → WebSocket Server → Dashboard
     ↑               ↑                  ↑
Price Data     Real-time Updates    User Interface
```

### Components

1. **WebSocket Server**
   - Port: 8772 (configurable)
   - Handles client connections
   - Streams market data
   - Manages connection state

2. **Dashboard Frontend**
   - Real-time price charts
   - Market pair overview
   - Performance metrics
   - System status

3. **Data Pipeline**
   - Price updates every second
   - Performance stats every 5 seconds
   - System health checks every minute

## Integration Points

### 1. Market Data
```python
# Data format
{
    "type": "price_update",
    "data": {
        "pair": "WETH/USDC",
        "price": "2650.42",
        "timestamp": "2025-02-10T00:31:44Z"
    }
}
```

### 2. Performance Metrics
```python
# Metrics format
{
    "type": "performance",
    "data": {
        "memory_usage": 205.90,
        "cpu_usage": 25.5,
        "network_rx": 1.2,
        "network_tx": 0.8
    }
}
```

### 3. System Status
```python
# Status format
{
    "type": "status",
    "data": {
        "dexes": ["baseswap", "swapbased"],
        "pairs_monitored": 6,
        "last_update": "2025-02-10T00:31:44Z"
    }
}
```

## Implementation Details

### 1. WebSocket Connection
```javascript
// Client-side connection
const ws = new WebSocket('ws://localhost:8772');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateDashboard(data);
};
```

### 2. Data Processing
```python
# Server-side processing
async def process_market_data():
    while True:
        data = await get_market_data()
        await broadcast_to_clients(data)
        await asyncio.sleep(1)
```

### 3. Error Handling
- Connection retry logic
- Data validation
- Error reporting
- State recovery

## Configuration

### 1. Environment Variables
```bash
DASHBOARD_PORT=5001
DASHBOARD_WEBSOCKET_PORT=8772
```

### 2. WebSocket Settings
```python
# Server configuration
websocket_config = {
    "ping_interval": 30,
    "ping_timeout": 10,
    "max_connections": 100
}
```

## Monitoring

### 1. Connection Health
- Track client connections
- Monitor message latency
- Log connection events
- Watch error rates

### 2. Data Quality
- Validate price updates
- Check data freshness
- Monitor update frequency
- Track data gaps

### 3. Performance
- Message throughput
- Connection count
- Memory usage
- CPU utilization

## Troubleshooting

### Common Issues

1. **Connection Drops**
   - Check network stability
   - Verify port availability
   - Monitor server resources
   - Review client logs

2. **Data Delays**
   - Check market analyzer
   - Verify WebSocket server
   - Monitor network latency
   - Review queue size

3. **High Resource Usage**
   - Check connection count
   - Monitor message size
   - Review update frequency
   - Optimize data structure

Last Updated: 2025-02-10