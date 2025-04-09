# Project Integration Guide

This document explains how all components of the Listonian Arbitrage Bot work together and how to integrate them properly.

## System Architecture

```
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  Arbitrage Bot      │◄────►│  Dashboard          │
│  (run_bot.py)       │      │  (run_dashboard.py) │
│                     │      │                     │
└─────────────────────┘      └─────────────────────┘
          ▲                             ▲
          │                             │
          ▼                             ▼
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  Core Components    │      │  Web Interface      │
│  - Path Finding     │      │  - Monitoring       │
│  - Execution        │      │  - Analytics        │
│  - Analytics        │      │  - Configuration    │
│                     │      │                     │
└─────────────────────┘      └─────────────────────┘
          ▲                             ▲
          │                             │
          ▼                             ▼
┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │
│  Blockchain         │      │  Memory Bank        │
│  - Web3 Connection  │      │  - Trade History    │
│  - DEX Interaction  │      │  - Metrics          │
│  - Flash Loans      │      │  - System State     │
│                     │      │                     │
└─────────────────────┘      └─────────────────────┘
```

## Component Integration

### 1. Arbitrage Bot Core

The arbitrage bot core is responsible for finding and executing arbitrage opportunities. It consists of:

- **Discovery Manager**: Finds arbitrage opportunities across DEXs
- **Execution Manager**: Executes trades using various strategies
- **Analytics Manager**: Records and analyzes trade performance
- **Market Data Provider**: Provides market data for decision making

These components are initialized and managed in `run_bot.py`.

### 2. Dashboard

The dashboard provides a web interface for monitoring and controlling the bot. It consists of:

- **FastAPI Backend**: Handles API requests and serves the UI
- **WebSocket Server**: Provides real-time updates
- **Templates**: UI components and pages
- **Static Assets**: CSS, JavaScript, and images

The dashboard is started using `run_dashboard.py`.

### 3. Data Flow

1. **Bot to Dashboard**:
   - The bot writes trade data to the memory bank
   - The dashboard reads from the memory bank to display information
   - Real-time updates are sent via WebSocket

2. **Dashboard to Bot**:
   - Configuration changes made in the dashboard are saved to config files
   - Control commands (start/stop/pause) are sent via API endpoints

### 4. Configuration Integration

The configuration system uses a layered approach:

1. **Base Configuration**: `configs/default.json`
2. **User Configuration**: `config.json`
3. **Environment Variables**: `.env` and `.env.production`

Environment variables take precedence over configuration files.

## Integration Steps

### 1. Environment Setup

1. Create `.env` file with required credentials
2. Create memory bank directories
3. Ensure log directories exist

### 2. Start the Bot

```bash
python run_bot.py
```

This initializes all core components and starts the arbitrage system.

### 3. Start the Dashboard

```bash
python run_dashboard.py
```

This starts the dashboard server on port 9051.

### 4. Alternative: Use Start Scripts

For convenience, use the provided scripts:

- Windows: `scripts/start_bot_with_dashboard.bat`
- PowerShell: `scripts/start_bot_with_dashboard.ps1`

These scripts handle environment setup, process management, and error handling.

## Troubleshooting Integration Issues

### 1. Communication Issues

If the dashboard cannot communicate with the bot:
- Ensure both are running
- Check that they're using the same memory bank path
- Verify WebSocket connection is established

### 2. Configuration Issues

If configuration changes don't take effect:
- Check the configuration loading order
- Verify environment variables are set correctly
- Restart both components after configuration changes

### 3. Data Synchronization

If data is not synchronized between components:
- Check file permissions on memory bank directories
- Verify the memory bank path is consistent
- Check for file locking issues

## Next Steps for Integration

1. **Implement Shared State**: Create a shared state mechanism between bot and dashboard
2. **Enhance Error Handling**: Improve error handling and recovery
3. **Add Authentication**: Implement authentication for dashboard access
4. **Optimize Data Flow**: Reduce latency in data exchange between components
