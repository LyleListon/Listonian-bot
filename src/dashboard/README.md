# Dashboard Application

## Purpose
The dashboard provides real-time monitoring and control of the arbitrage bot, including:
- Price monitoring across DEXes
- Opportunity tracking
- System performance metrics
- Configuration management

## Components
- Web Server (Flask)
- WebSocket Server
- Frontend
  * Real-time price charts
  * Opportunity tables
  * Performance metrics
  * System status
- API Endpoints
  * Price data
  * Opportunity data
  * System metrics
  * Configuration

## Architecture
```
dashboard/
├── static/         # Frontend assets
│   ├── css/       # Stylesheets
│   ├── js/        # JavaScript files
│   └── img/       # Images
├── templates/      # HTML templates
├── api/           # API endpoints
└── websocket/     # WebSocket handlers
```

## Features
1. Real-time Updates
   - Price movements
   - Opportunity detection
   - Trade execution
   - System metrics

2. Interactive Controls
   - Start/stop trading
   - Update configurations
   - Adjust parameters
   - Emergency controls

3. Data Visualization
   - Price charts
   - Profit graphs
   - Performance metrics
   - System health

## Technical Details
- Port: 5001
- WebSocket Port: 8772
- Authentication required
- CORS configured
- Rate limiting enabled

Last Updated: 2025-02-10