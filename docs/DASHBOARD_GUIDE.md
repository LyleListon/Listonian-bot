# Arbitrage Monitoring Dashboard Guide

## Overview

The arbitrage monitoring dashboard provides real-time visibility into the arbitrage bot's operations, market conditions, and system performance. It offers a comprehensive view of price movements, trading opportunities, and system health metrics.

## Features

### Real-time Price Monitoring

- **Token Pairs Tracked**:
  - WETH/USDC
  - WETH/DAI
  - USDC/DAI

- **Exchanges Monitored**:
  - BaseSwap
  - Aerodrome

- **Price Data Display**:
  - Current prices from each exchange
  - Spread percentage calculations
  - Last update timestamps
  - Automatic updates via WebSocket

### System Status

- **Resource Monitoring**:
  - CPU usage percentage
  - Memory usage percentage
  - Network I/O statistics
  - Active connections count

- **Health Indicators**:
  - Overall system status
  - Warning indicators for high resource usage
  - Error rate monitoring
  - Performance alerts

### Trading Performance

- **Opportunity Tracking**:
  - Total opportunities identified
  - Average spread percentages
  - Potential profit calculations
  - Executed trades count

- **Profit Monitoring**:
  - Total profit tracking
  - Average profit per trade
  - Gas cost analysis
  - Net profit calculations

## Technical Implementation

### Architecture

- **Frontend**:
  - HTML5 with real-time updates
  - WebSocket connection for live data
  - Responsive design for various screen sizes
  - Automatic data refresh

- **Backend**:
  - Flask web server
  - Flask-SocketIO for real-time communication
  - Gevent for async operations
  - Modular monitoring system

### Data Flow

1. Price data collection from DEXes
2. System metrics gathering
3. Performance calculations
4. WebSocket broadcast to connected clients
5. Real-time UI updates

## Running the Dashboard

1. **Start the Dashboard**:
   ```bash
   python -m dashboard.enhanced_app
   ```

2. **Access the Interface**:
   - Open a web browser
   - Navigate to http://localhost:5002
   - Dashboard will automatically connect and start displaying data

3. **Monitor Updates**:
   - Price data updates every few seconds
   - System metrics refresh continuously
   - Performance stats update in real-time

## Configuration

### Environment Variables

- `PORT`: Dashboard port (default: 5002)
- `HOST`: Host address (default: 127.0.0.1)
- `NETWORK`: Target network (default: base)

### Network Settings

- Configured in `configs/networks/`
- Supports multiple networks
- Easy to add new DEXes

## Troubleshooting

### Common Issues

1. **Connection Problems**:
   - Check if the dashboard server is running
   - Verify port availability
   - Ensure WebSocket connection is not blocked

2. **Data Not Updating**:
   - Check console for WebSocket errors
   - Verify monitoring system is active
   - Check network connectivity

3. **High Resource Usage**:
   - Monitor system metrics
   - Check for memory leaks
   - Verify data collection intervals

### Logging

- Dashboard logs available in console
- System metrics logged to monitoring system
- WebSocket events logged for debugging

## Best Practices

1. **Regular Monitoring**:
   - Check system health frequently
   - Monitor resource usage trends
   - Track performance metrics

2. **Performance Optimization**:
   - Adjust update intervals as needed
   - Clean up old data periodically
   - Monitor memory usage

3. **Security**:
   - Access control implementation
   - Regular security updates
   - Network security best practices

## Future Enhancements

- Additional trading pair support
- Enhanced analytics features
- Historical data visualization
- Custom alert configurations
- Performance optimization tools
