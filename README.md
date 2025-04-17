# Listonian Arbitrage Bot

A high-performance arbitrage bot for cryptocurrency markets, focusing on flash loan-based arbitrage opportunities across multiple DEXes.

## Architecture

The Listonian Arbitrage Bot is built with a modular architecture that separates concerns and allows for easy extension:

- **Core Components**: The foundation of the system, including WebSocket handling, flash loan management, and blockchain interaction.
- **DEX Integrations**: Adapters for various decentralized exchanges.
- **Execution Engine**: Handles the execution of arbitrage opportunities.
- **Monitoring**: Real-time monitoring and alerting for the bot's operation.

## Key Features

- **Unified Flash Loan Management**: Consolidated flash loan functionality for better maintainability
- **Stable WebSocket Connections**: Enhanced WebSocket handling with automatic reconnection
- **Multi-DEX Support**: Support for multiple DEXes including Uniswap, PancakeSwap, and more
- **MEV Protection**: Integration with Flashbots to protect against MEV attacks
- **Real-time Monitoring**: Dashboard for monitoring bot performance and market conditions

## Getting Started

### Prerequisites

- Python 3.10+
- Web3.py
- Asyncio

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Listonian-bot.git
   cd Listonian-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the bot:
   ```bash
   cp configs/default.json configs/config.json
   # Edit config.json with your settings
   ```

### Running the Bot

You can run the entire system using the `run_all.py` script:

```bash
python run_all.py --use-real-data --clear-memory
```

Command-line arguments:
- `--use-real-data`: Use real data instead of mock data
- `--clear-memory`: Clear the memory bank before starting

Alternatively, you can run each component separately:

1. Run the arbitrage bot:
```bash
python run_bot.py
```

2. Run the dashboard:
```bash
python run_dashboard.py
```

## Configuration

The bot is configured through JSON files in the `configs/` directory. The main configuration file is `config.json`, which includes settings for:

- Network connections
- DEX settings
- Flash loan parameters
- Gas price strategies
- Profit thresholds

## Dashboard

The bot includes a real-time dashboard for monitoring performance:

```bash
python run_dashboard.py
```

The dashboard is available at `http://localhost:9050` by default. You can change the port by setting the `DASHBOARD_PORT` environment variable.

## Testing

Run the test suite with:

```bash
python -m pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
