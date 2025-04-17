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
python -m new_dashboard.run_dashboard
```

Command line options:

```bash
--host HOST           Host to bind to (default: 0.0.0.0)
--port PORT           Port to run the dashboard on (default: 9050)
--reload              Enable auto-reload on code changes
--debug               Enable debug mode
--find-port           Find an available port automatically
```

Example with custom settings:

```bash
python -m new_dashboard.run_dashboard --port 9060 --debug --reload
```

Or programmatically:

```python
from new_dashboard.dashboard import start_dashboard

await start_dashboard(config_path="configs/dashboard_config.json")
```

### Accessing the Dashboard

Open a web browser and navigate to:

```text
http://localhost:9050
```

### Testing WebSocket Connection

The dashboard includes a WebSocket test page that can be accessed at:

```text
http://localhost:9050/websocket-test
```

This page allows you to:
- Test WebSocket connections
- Send custom messages
- View received messages
- Debug connection issues

### Generating Test Data

To generate test data for the dashboard without running the actual arbitrage bot:

```bash
python -m new_dashboard.generate_test_data
```

Command line options:

```bash
--output-dir OUTPUT_DIR  Directory to save test data to (default: memory-bank)
--interval INTERVAL      Interval between data updates in seconds (default: 1.0)
--duration DURATION      Duration to run for in seconds, or None to run indefinitely
```

### Testing WebSocket from Command Line

To test the WebSocket connection from the command line:

```bash
python -m new_dashboard.test_websocket
```

Command line options:

```bash
--url URL               WebSocket URL to connect to (default: ws://localhost:9050/ws/metrics)
--timeout TIMEOUT       Test duration in seconds (default: 60)
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
python -m new_dashboard.run_dashboard --debug --reload
```

This enables:

- Hot reloading of template changes
- Detailed error messages
- Development console

## Debugging

### WebSocket Debugging

The dashboard includes a WebSocket debugging tool that can be accessed by:

1. Pressing `Ctrl+Shift+D` while on the dashboard page
2. Clicking the gear icon in the bottom right corner

The debugging tool provides:

- Connection status
- Message logs
- Timing information
- Error details

### Browser Console

Check the browser console (F12) for detailed logs about:

- WebSocket connections
- Data updates
- Errors

### Server Logs

Server logs are stored in the `logs` directory and provide information about:

- Server startup
- WebSocket connections
- API requests
- Errors

## Troubleshooting

### WebSocket Connection Issues

If the dashboard is not updating in real-time:

1. Check the connection status indicator in the top right corner
2. Open the WebSocket debugging tool (Ctrl+Shift+D)
3. Check the browser console for connection errors
4. Verify that the WebSocket server is running
5. Try the WebSocket test page to diagnose connection issues

### Data Not Displaying

If data is not displaying correctly:

1. Check that the memory-bank directory exists and contains data files
2. Run the test data generator to create sample data
3. Check the browser console for parsing errors
4. Verify that the data format matches what the dashboard expects
