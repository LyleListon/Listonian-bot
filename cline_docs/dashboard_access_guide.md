# Dashboard Access Guide

This document provides instructions for accessing and using the arbitrage system's monitoring dashboard.

## Dashboard Overview

The arbitrage system includes a comprehensive monitoring dashboard that provides real-time insights into system performance, arbitrage opportunities, and trade execution. The dashboard runs on a web server that you can access through any modern web browser.

## Dashboard Options

There are two dashboard implementations available:

1. **Minimal Dashboard** (Recommended) - A lightweight Flask-based dashboard
2. **Full Dashboard** - A feature-rich aiohttp-based dashboard (may require additional dependencies)

## Starting the Minimal Dashboard

The minimal dashboard is a lightweight, easy-to-use interface that requires minimal dependencies.

### Method 1: Using the batch file

```bash
.\start_minimal_dashboard.bat
```

This will start the minimal dashboard server with default settings.

### Method 2: Using Python directly

```bash
python minimal_dashboard.py
```

### Command Line Options for Minimal Dashboard

```bash
python minimal_dashboard.py --host=0.0.0.0 --port=5000 --debug
```

Available options:
- `--host`: Host interface to listen on (default: "localhost")
- `--port`: Port to listen on (default: 5000)
- `--debug`: Enable debug mode

## Accessing the Minimal Dashboard

By default, the minimal dashboard is accessible at:

**URL:** http://localhost:5000

If you've changed the host or port using command-line options, adjust the URL accordingly.

## Starting the Full Dashboard

The full dashboard provides more advanced features but may require additional dependencies.

### Method 1: Using the batch file

```bash
.\start_dashboard.bat
```

### Method 2: Using Python directly

```bash
python start_dashboard.py
```

### Command Line Options for Full Dashboard

```bash
python start_dashboard.py --host=0.0.0.0 --port=8080 --debug
```

Available options:
- `--host`: Host interface to listen on (default: "localhost")
- `--port`: Port to listen on (default: 8080)
- `--debug`: Enable debug mode
- `--config`: Path to configuration file (default: "configs/production.json")

## Accessing the Full Dashboard

By default, the full dashboard is accessible at:

**URL:** http://localhost:8080

However, if you encounter issues with the full dashboard, please use the minimal dashboard instead.

## Minimal Dashboard Features

The minimal dashboard provides:

1. **System Overview**
   - Current system status
   - Uptime monitoring
   - Wallet balance (placeholder)
   - Total profit tracking (placeholder)

2. **DEX Integration Status**
   - Status of all 5 integrated DEXes
   - Activity indicators

3. **Dynamic Allocation Status**
   - Min/max percentage settings
   - Concurrent trades configuration
   - Reserve percentage

4. **Configuration Viewer**
   - Current system configuration
   - JSON format for easy review

## Full Dashboard Features (When Available)

The full dashboard provides all features of the minimal dashboard plus:

1. **Advanced Analytics**
   - Price comparisons across DEXes
   - Liquidity visualization
   - Trading volume metrics
   - Fee analysis

2. **Risk Management**
   - MEV risk assessment
   - Slippage monitoring
   - Transaction security metrics
   - Flash loan exposure

3. **Real-time Updates**
   - WebSocket-based live data
   - Event-driven updates

## Security Considerations

The dashboard's default configuration only allows access from the local machine (localhost). If you need to access the dashboard from other machines:

1. Start the dashboard with the `--host` option:
   ```bash
   python minimal_dashboard.py --host=0.0.0.0
   ```

2. Adjust your firewall to allow access to the dashboard port.

3. Consider setting up HTTPS and authentication for secure remote access.

## Troubleshooting

- **Dashboard won't start**: Check if another service is using the port. You can specify a different port with the `--port` option.
- **Can't connect to dashboard**: Ensure the dashboard server is running and check your firewall settings.
- **Full dashboard not loading**: Try the minimal dashboard instead, which has fewer dependencies.
- **Missing data**: Verify that the arbitrage system is running and connected to the Ethereum network.