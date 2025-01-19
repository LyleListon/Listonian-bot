# Arbitrage Bot


An advanced cryptocurrency arbitrage bot with ML-driven decision-making and sophisticated risk management.

## Features

- Multi-DEX Integration (V2/V3 protocols)
  - PancakeSwap V3
  - BaseSwap
  - Support for multiple DEX protocols
  - Unified interface for all DEXs

- Market Analysis System
  - Real-time price monitoring via MCP servers
  - Market condition assessment
  - Volatility analysis
  - Liquidity depth tracking

- Advanced Gas Optimization
  - Market-based gas price adjustment
  - Volatility-aware gas calculations
  - Dynamic fee tier selection
  - Gas usage analytics

- Real-time Monitoring
  - WebSocket-based updates (port 8771)
  - Transaction tracking
  - Performance metrics
  - System health monitoring

- Analytics Integration
  - MCP server connectivity
  - Historical data analysis
  - Risk metrics calculation
  - Performance tracking

## Requirements

- Python 3.9+
- Node.js (for contract compilation)
- Web3 Provider (Infura/Alchemy)
- 2GB RAM minimum
- SSD Storage
- Stable network connection

## Security Setup (IMPORTANT)

1. Create a new secure wallet for the bot:
```bash
# DO NOT use any previously exposed wallets
# Generate a new wallet using a secure method
```

2. Set up environment variables:
```bash
# Copy the template (NEVER commit the actual .env file)
cp .env.template .env

# Edit .env with your secure data:
# - New wallet private key
# - RPC endpoints
# - API keys
```

3. Verify security:
```bash
# Check that .env is in .gitignore
cat .gitignore | grep .env

# Verify no sensitive data in config files
grep -r "0x" configs/
```

4. Regular security checks:
```bash
# Check for sensitive data in git history
git log -p | grep -i "private"
git log -p | grep "0x"

# Review current files for sensitive data
find . -type f -exec grep -l "0x" {} \;
```

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd arbitrage-bot
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies:
```bash
npm install
```

4. Create and configure environment file:
```bash
cp .env.template .env
# Edit .env with your configuration
```

## Configuration

1. Set up your Web3 provider and API keys in `.env`:
```
WEB3_PROVIDER_URI=your_provider_url
OPENWEATHER_API_KEY=your_api_key  # For MCP servers
```

2. Configure trading parameters in `configs/trading_config.json`:
```json
{
  "max_position_size": 0.1,
  "min_profit_threshold": 0.001,
  "gas_price_limit": 100,
  "update_interval": 60,
  "websocket_port": 8771
}
```

3. Configure MCP servers in `cline_mcp_settings.json`:
```json
{
  "mcpServers": {
    "crypto-price": {
      "command": "node",
      "args": ["path/to/server/index.js"],
      "env": {
        "API_KEY": "${API_KEY}"  // Use environment variable
      }
    }
  }
}
```

4. Set up DEX configurations in `configs/dex_config.json`

## Usage

1. Start in production mode (includes all systems):
```bash
python start_production.py
```

2. Start in monitoring-only mode:
```bash
python start_monitoring.py
```

3. Start with specific components:
```bash
# Just the bot
python start_bot.py

# Just the dashboard
python -m arbitrage_bot.dashboard.run

# Custom configuration
python main.py --config path/to/config.json
```

4. Access the dashboard:
```
Dashboard: http://localhost:5000
WebSocket: ws://localhost:8771
```

## Architecture

- Core Systems
  - DEX Integration Layer
    * Base DEX interface
    * Protocol-specific implementations (V2/V3)
    * Multi-DEX management
  - Market Analysis System
    * Price monitoring
    * Market condition assessment
    * Opportunity detection
  - Analytics System
    * Performance tracking
    * Risk assessment
    * Historical analysis

- Supporting Systems
  - Gas Optimizer
    * Market-based pricing
    * Volatility adjustment
    * Usage analytics
  - MCP Servers
    * Price data service
    * Market analysis service
  - WebSocket Server
    * Real-time updates
    * System monitoring

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

Run performance tests:
```bash
python -m pytest tests/performance/
```

## Security Best Practices

1. Wallet Security
   - Generate new wallets securely offline
   - Never reuse compromised wallets
   - Use hardware wallets when possible
   - Regularly rotate API keys

2. Environment Variables
   - Use .env files for all sensitive data
   - Never commit .env files
   - Use .env.template as a guide
   - Regularly audit environment variables

3. Git Security
   - Use .gitignore properly
   - Check commits before pushing
   - Regular git history audits
   - Use git hooks to prevent sensitive data commits

4. Operational Security
   - Regular security audits
   - Monitor system logs
   - Use secure RPC endpoints
   - Implement rate limiting
   - Monitor wallet activity

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes (check for sensitive data!)
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational purposes only. Use at your own risk. The authors and contributors are not responsible for any financial losses incurred while using this software.
