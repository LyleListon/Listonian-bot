# Arbitrage Bot Dashboard

A real-time monitoring dashboard for the arbitrage bot system, built with FastAPI and WebSocket for live updates.

## Features

### 1. Blockchain Monitoring
- Real-time block number tracking
- Gas price monitoring
- Network connection status
- Chain ID verification

### 2. Cache System Metrics
- Cache hit ratio tracking
- Cache size monitoring
- TTL eviction statistics
- Performance optimization insights

### 3. Performance Monitoring
- Memory usage tracking
- CPU utilization
- Active connection count
- Batch operation statistics

### 4. Security Metrics
- Slippage violation tracking
- Transaction validation status
- Suspicious transaction detection
- Risk assessment metrics

### 5. DEX Integration Status
- Active pool monitoring
- Total liquidity tracking
- Price update frequency
- Integration health checks

## Technology Stack

- **Backend**: FastAPI + Python 3.12+
- **Frontend**: HTML + JavaScript
- **Real-time Updates**: WebSocket
- **Blockchain**: Web3.py
- **Monitoring**: psutil

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```env
# Network Configuration
RPC_URL=https://mainnet.base.org
CHAIN_ID=8453

# Dashboard Configuration
DASHBOARD_HOST=127.0.0.1
DASHBOARD_PORT=3000

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/dashboard.log
```

3. Start the dashboard:
```bash
./start_dashboard.ps1  # Windows
# or
./start_dashboard.sh   # Linux/Mac
```

4. Access the dashboard:
```
http://127.0.0.1:3000
```

## API Endpoints

### WebSocket
- `/ws` - Real-time metric updates

### REST API
- `GET /api/status` - Overall system status
- `GET /api/metrics` - Detailed system metrics
- `GET /api/cache` - Cache system metrics
- `GET /api/performance` - Performance metrics
- `GET /api/security` - Security metrics
- `GET /api/dex` - DEX integration metrics
- `GET /health` - Health check endpoint

## Architecture

The dashboard follows a modular architecture:

1. **Web3 Layer**
   - Blockchain connection management
   - Transaction monitoring
   - Gas price tracking

2. **Metrics Collection**
   - System resource monitoring
   - Cache performance tracking
   - Security metric aggregation

3. **Real-time Updates**
   - WebSocket communication
   - Event-driven updates
   - Connection management

4. **Frontend**
   - Responsive design
   - Real-time data visualization
   - Status indicators

## Security Considerations

- Environment variables for sensitive configuration
- CORS protection
- Error handling and logging
- Rate limiting (TODO)
- Authentication (TODO)

## Development

### Adding New Metrics

1. Add metric to the metrics dictionary in `app.py`:
```python
metrics = {
    'new_category': {
        'metric_name': initial_value
    }
}
```

2. Create corresponding API endpoint:
```python
@app.get("/api/new_category")
async def get_new_category_metrics():
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics['new_category']
    }
```

3. Update the frontend to display the new metrics in `index.html`

### Testing

Run the development server with auto-reload:
```bash
python -m uvicorn app:app --reload --port 3000
```

## Contributing

1. Follow the project's async/await patterns
2. Maintain error handling standards
3. Update documentation for new features
4. Add appropriate logging
5. Test thoroughly before submitting changes

## License

MIT License - See LICENSE file for details