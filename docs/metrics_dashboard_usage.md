# Metrics Dashboard Usage Guide

This guide explains how to use the metrics dashboard for the Listonian Arbitrage Bot.

## Overview

The metrics dashboard provides real-time monitoring of the bot's performance, system resources, and trade history. It comes in two forms:

1. **Web Dashboard** - A browser-based dashboard accessible via HTTP
2. **Terminal Dashboard** - A text-based dashboard that runs in your terminal

Both dashboards provide similar information but in different formats.

## Starting the Dashboards

### Web Dashboard

To start the web dashboard:

```bash
python Listonian-bot/run_dashboard.py
```

This will start the dashboard server on port 9051. You can access it by opening a web browser and navigating to:

```
http://localhost:9051
```

### Terminal Dashboard

To start the terminal dashboard:

```bash
python Listonian-bot/terminal_dashboard.py
```

This will open a text-based dashboard directly in your terminal.

## Dashboard Features

### Web Dashboard

The web dashboard provides the following features:

1. **System Metrics** - CPU, memory, disk, and network usage
2. **Financial Metrics** - Total profit, success rate, average profit, etc.
3. **Trade History** - Recent trades with details
4. **DEX Performance** - Performance metrics for different DEXes
5. **Flash Loan Metrics** - Flash loan usage and performance
6. **Execution Metrics** - Execution time and success rate
7. **Token Performance** - Performance metrics for different tokens

You can access these metrics through different tabs in the web interface.

### Terminal Dashboard

The terminal dashboard provides:

1. **System Status** - Current status, uptime, block number, and wallet balance
2. **System Resources** - CPU, memory, disk, and network usage with visual indicators
3. **Financial Metrics** - Key financial metrics like total profit and success rate
4. **Recent Trades** - List of recent trades with profit/loss indicators

The terminal dashboard uses keyboard shortcuts:
- `q` - Quit the dashboard
- `r` - Refresh the metrics
- `h` - Show help

## WebSocket Endpoints

For developers who want to integrate with the dashboard, the following WebSocket endpoints are available:

- `/ws/metrics` - All metrics
- `/ws/profitability` - Profitability metrics
- `/ws/dex-performance` - DEX performance metrics
- `/ws/flash-loans` - Flash loan metrics
- `/ws/execution` - Execution metrics
- `/ws/token-performance` - Token performance metrics
- `/ws/system-performance` - System performance metrics
- `/ws/system` - Basic system metrics
- `/ws/detailed-system` - Detailed system metrics
- `/ws/trades` - Trade history
- `/ws/market` - Market data

## REST API Endpoints

The dashboard also provides REST API endpoints:

- `/api/metrics` - Get all metrics
- `/api/status` - Get system status
- `/api/system/detailed` - Get detailed system metrics
- `/api/trades` - Get trade history

## Troubleshooting

### Dashboard Not Starting

If the dashboard fails to start, check:

1. Make sure the port 9051 is not in use by another application
2. Ensure all dependencies are installed
3. Check the logs for any error messages

### No Data Showing

If the dashboard starts but no data is showing:

1. Make sure the bot is running
2. Check that the bot and dashboard are properly connected
3. Verify that the memory bank is accessible

### Terminal Dashboard Display Issues

If the terminal dashboard has display issues:

1. Make sure your terminal supports rich text
2. Try resizing your terminal window
3. Check that the required Python packages are installed

## Requirements

The dashboard requires:

- Python 3.8 or higher
- FastAPI
- Uvicorn
- Textual (for terminal dashboard)
- aiohttp
- psutil

These should be included in the project's requirements.txt file.