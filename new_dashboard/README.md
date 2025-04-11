# Dashboard Module

The dashboard module provides real-time monitoring and visualization for the Listonian Arbitrage Bot. It displays critical metrics, market data, and system status information.

## Features

- **Real-time Metrics**: Live updates of bot performance metrics
- **Market Data**: Current prices, liquidity, and trading volumes
- **System Status**: Health monitoring of all bot components
- **Arbitrage Opportunities**: Visualization of detected arbitrage opportunities
- **Historical Performance**: Charts and graphs of historical performance
- **Alert System**: Notifications for critical events

## Architecture

The dashboard follows a modern web architecture:

- **Backend**: Python-based API server using FastAPI
- **Frontend**: Responsive web interface using HTML, CSS, and JavaScript
- **WebSocket**: Real-time data updates via WebSocket connections
- **Data Storage**: Time-series data for historical analysis

## Components

### Dashboard Server

The main server component that handles API requests and serves the dashboard interface:

```python
from new_dashboard.dashboard import DashboardServer

# Initialize the dashboard server
dashboard = DashboardServer(
    port=3000,
    host="0.0.0.0",
    config=dashboard_config
)

# Start the dashboard
await dashboard.start()
```

### Data Services

Services that collect and process data for the dashboard:

- **SystemMonitor**: Monitors system health and resource usage
- **MarketDataService**: Collects and processes market data
- **PerformanceTracker**: Tracks bot performance metrics
- **AlertService**: Generates alerts based on configurable thresholds

### WebSocket Routes

WebSocket endpoints for real-time data updates:

- `/ws/system`: System status updates
- `/ws/market`: Market data updates
- `/ws/performance`: Performance metric updates
- `/ws/alerts`: Real-time alerts

## Usage

### Starting the Dashboard

```bash
python run_dashboard.py
```

Or programmatically:

```python
from new_dashboard.dashboard import start_dashboard

await start_dashboard(config_path="configs/dashboard_config.json")
```

### Accessing the Dashboard

Open a web browser and navigate to:

```
http://localhost:3000
```

### Configuration

The dashboard is configured through the `dashboard_config.json` file:

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 3000,
    "debug": false
  },
  "data": {
    "refresh_interval": 5,
    "history_length": 1000
  },
  "alerts": {
    "enabled": true,
    "channels": ["web", "email"]
  }
}
```

## Customization

The dashboard can be customized through:

- **Themes**: Custom CSS themes in the `static/css` directory
- **Widgets**: Add or remove widgets in the `templates/widgets` directory
- **Data Sources**: Configure additional data sources in `services/data_sources.py`

## Development

For development purposes, you can run the dashboard in debug mode:

```bash
python run_dashboard.py --debug
```

This enables:
- Hot reloading of template changes
- Detailed error messages
- Development console