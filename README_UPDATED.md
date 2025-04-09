# Listonian Arbitrage Bot

A high-performance arbitrage bot for Base mainnet that uses:
- Balancer for flash loans
- Flashbots for MEV protection
- Multi-path arbitrage optimization
- Real-time monitoring
- MCP servers for data and analysis

## Quick Start

1. Double-click `start_arbitrage_bot.bat` to begin. The script will:
   - Check Python installation (requires Python 3.12+)
   - Create .env.production from template if needed
   - Initialize secure storage for sensitive data
   - Start the bot with automatic restart on crashes
   - Open a log viewer window

2. Alternatively, use the PowerShell script:
   ```powershell
   .\scripts\start_bot_with_dashboard.ps1
   ```

3. To start the MCP servers:
   ```powershell
   python scripts\manage_mcp_servers.py start-all
   ```

## Configuration

### Required Environment Variables
Copy `.env.production.template` to `.env.production` and fill in:

```bash
# Get from https://www.alchemy.com/
ALCHEMY_API_KEY=your-api-key

# Your wallet's private key (with 0x prefix)
PRIVATE_KEY=0xyour-private-key

# Your wallet addresses
WALLET_ADDRESS=0xYour-Wallet-Address
PROFIT_RECIPIENT=0xProfit-Recipient-Address

# Flashbots Configuration
# Keep this as $SECURE:PRIVATE_KEY
FLASHBOTS_AUTH_KEY=$SECURE:PRIVATE_KEY

# This tells the bot to use your wallet's private key for Flashbots
# authentication
```

### Production Settings
The bot is configured in `configs/production.json` with:
- Base mainnet RPC endpoints
- Flashbots integration
- Balancer flash loan settings
- Token addresses (WETH, USDC)
- Gas and profit thresholds

## Features

- **Flash Loans**: Uses Balancer as primary provider with Aave as fallback
- **MEV Protection**: Integrates with Flashbots for private transaction routing
- **Multi-Path Arbitrage**: Optimizes across multiple DEX paths
- **Real-time Monitoring**: Automatic log viewer window
- **Auto-Recovery**: Restarts automatically after crashes
- **Secure Storage**: Encrypts sensitive data like private keys
- **MCP Servers**: Provides data and analysis through Model Context Protocol

## Components

### Arbitrage Bot
The core arbitrage bot is responsible for finding and executing arbitrage opportunities. It consists of:
- Discovery Manager: Finds arbitrage opportunities across DEXes
- Execution Manager: Executes trades using various strategies
- Analytics Manager: Records and analyzes trade performance
- Market Data Provider: Provides market data for decision making

### Dashboard
The dashboard provides a web interface for monitoring and controlling the bot. It consists of:
- FastAPI Backend: Handles API requests and serves the UI
- WebSocket Server: Provides real-time updates
- Templates: UI components and pages
- Static Assets: CSS, JavaScript, and images

### MCP Servers
The MCP (Master Control Program) servers provide data and analysis for the arbitrage bot:
- Base DEX Scanner: Monitors the Base blockchain for DEXes and pools
- Crypto Price: Provides cryptocurrency price data
- Market Analysis: Analyzes market conditions and trends

## Monitoring

The bot creates two windows:
1. Main bot window showing startup progress
2. Log viewer window showing real-time operation

Monitor `logs/arbitrage.log` for detailed operation information.

You can also access the dashboard at http://localhost:9050 for a web-based monitoring interface.

## Troubleshooting

If the bot fails to start:
1. Ensure Python 3.12+ is installed and in PATH
2. Verify all environment variables are set correctly
3. Check log files for detailed error messages
4. Ensure you have sufficient funds for gas
5. Verify RPC endpoints are accessible

For MCP server issues:
1. Check that the servers are running using `python scripts/manage_mcp_servers.py list`
2. Verify that the environment variables are set correctly
3. Check the server logs for error messages
4. Restart the servers using `python scripts/manage_mcp_servers.py stop-all` followed by `python scripts/manage_mcp_servers.py start-all`

## Security Notes

- Private keys are stored encrypted in the `secure` directory
- Use a dedicated wallet for the bot
- Monitor gas usage and profit thresholds
- Test with small amounts first

## Augment Integration

This project is integrated with the Augment extension. The configuration files are located in the `.augment` directory:
- `config.json`: Main configuration file
- `mcp_config.json`: MCP server configuration
- `mcp_helper.py`: Helper script for MCP servers

For more information on MCP integration, see [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md).
