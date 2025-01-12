# Technical Context

## Technology Stack

### Core Technologies
- Python 3.9+
- Node.js (for contract compilation)
- Web3.py (for blockchain interaction)
- Flask (for dashboard)
- WebSocket (for real-time updates)
- SQLite (for local data storage)

### External Services
- Web3 Provider (Alchemy)
- MCP Servers
  - crypto-price (price data service)
  - market-analysis (market analysis service)

### Smart Contract Integration
- EVM Compatible
- Support for multiple DEX protocols:
  - PancakeSwap V3
  - BaseSwap
  - Extensible architecture for additional DEXs

## Development Setup

### Environment Requirements
- 2GB RAM minimum
- SSD Storage
- Stable network connection
- Environment variables configured in .env
- MCP server settings in cline_mcp_settings.json

### Key Configuration Files
1. .env
   - Web3 provider URI
   - Wallet configuration
   - Network settings
   - API keys

2. configs/trading_config.json
   - Trading parameters
   - Risk limits
   - Performance thresholds

3. configs/dex_config.json
   - DEX-specific settings
   - Contract addresses
   - Protocol configurations

## System Architecture

### Core Components
1. DEX Integration Layer
   - base_dex.py: Base interface
   - base_dex_v2.py: V2 protocol support
   - base_dex_v3.py: V3 protocol support
   - dex_manager.py: Multi-DEX coordination

2. Market Analysis
   - market_analyzer.py: Price analysis
   - analytics_system.py: Performance tracking
   - metrics_manager.py: System metrics

3. Trade Execution
   - trade_executor.py: Trade execution
   - arbitrage_executor.py: Arbitrage logic
   - gas_optimizer.py: Gas optimization

4. Monitoring & Analytics
   - transaction_monitor.py: Transaction tracking
   - alert_system.py: System alerts
   - websocket_server.py: Real-time updates

### Supporting Systems
1. Dashboard
   - app.py: Main Flask application
   - run.py: Dashboard server
   - WebSocket on port 8771

2. Machine Learning
   - ml_system.py: ML predictions
   - monte_carlo.py: Simulation system

3. Data Management
   - database.py: Local data storage
   - Historical data in /data
   - Analytics in /analytics

## Technical Constraints

### Performance Requirements
- Sub-second response time for price updates
- Maximum 3-second latency for trade execution
- Real-time WebSocket updates (< 100ms)
- Efficient memory usage (< 2GB RAM)

### Network Requirements
- Stable connection to Web3 provider
- WebSocket server capacity
- MCP server connectivity
- DEX API rate limits

### Security Considerations
- Private key management
- Transaction signing
- API key protection
- Rate limiting
- Error handling

## Monitoring & Maintenance

### Health Checks
- WebSocket connectivity
- DEX connection status
- Database integrity
- Memory usage
- Network latency

### Logging
- System logs in /logs
- Transaction history
- Performance metrics
- Error tracking

### Backup & Recovery
- Configuration backups
- Database backups
- State recovery procedures
- Error handling protocols
