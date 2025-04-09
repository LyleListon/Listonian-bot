# Listonian Arbitrage Bot

A sophisticated cryptocurrency arbitrage system designed to identify and execute profitable trading opportunities across decentralized exchanges (DEXes) on the Base network.

## Project Overview

The Listonian Arbitrage Bot is a comprehensive system that:

- Monitors multiple DEXes on the Base network for price discrepancies
- Identifies profitable arbitrage opportunities
- Executes trades using flash loans for capital efficiency
- Provides real-time monitoring through a web dashboard
- Uses MCP (Master Control Program) servers for data and analysis

## Project Structure

The project is organized into the following main components:

```
Listonian-bot/
├── arbitrage_bot/         # Core arbitrage bot package
├── new_dashboard/         # Dashboard implementation
├── configs/               # Configuration files
├── scripts/               # Helper scripts
├── memory-bank/           # Shared data storage
├── secure/                # Secure storage for sensitive data
├── .augment/              # Augment extension configuration
├── docs/                  # Documentation
├── tests/                 # Tests
├── logs/                  # Log files
└── mcp_servers/           # MCP server implementations
```

For more details on the project structure, see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+ (for some scripts)
- Git

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/LyleListon/Listonian-bot.git
   cd Listonian-bot
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your API keys and settings (optional):
   ```bash
   cp .env.production.template .env
   # Edit .env with your API keys and settings
   ```
   If you don't have a `.env` file, the bot will use default values for some settings.

### Configuration

The bot uses a layered configuration approach:
1. Default configuration from `configs/default.json`
2. User configuration from `config.json`
3. Environment variables from `.env`

Required environment variables:
```
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/your-api-key
PRIVATE_KEY=your-private-key
WALLET_ADDRESS=your-wallet-address
PROFIT_RECIPIENT=profit-recipient-address
FLASHBOTS_AUTH_KEY=your-flashbots-auth-key
ALCHEMY_API_KEY=your-alchemy-api-key
```

## Usage

### Starting the Bot

```bash
python run_bot.py
```

### Starting the Dashboard

```bash
python run_dashboard.py
```

### Starting Both Bot and Dashboard

```bash
# Windows
scripts\start_bot_with_dashboard.bat

# PowerShell
.\scripts\start_bot_with_dashboard.ps1
```

### Starting MCP Servers

```bash
python scripts\manage_mcp_servers.py start-all
```

## Dashboard

The dashboard provides a web interface to monitor the bot's performance and manage its operations.
- URL: http://localhost:9050
- Features:
  - Real-time monitoring
  - Trade history
  - Performance metrics
  - System status

## MCP Servers

The MCP (Master Control Program) servers provide data and analysis for the arbitrage bot:
- Base DEX Scanner: Monitors the Base blockchain for DEXes and pools
- Crypto Price: Provides cryptocurrency price data
- Market Analysis: Analyzes market conditions and trends

For more information on MCP integration, see [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md).

## Project Maintenance

### Cleaning Up the Project

To identify unused files and clean up the project:

```bash
python scripts\cleanup_project.py
```

### Reorganizing the Project

To reorganize the project according to the ideal structure:

```bash
python scripts\reorganize_project.py
```

## Troubleshooting

If you encounter issues:

1. Check the log files in the `logs/` directory
2. Verify your API keys and environment variables
3. Ensure all required directories exist
4. Check the memory bank for data integrity

## License

Proprietary - All rights reserved
