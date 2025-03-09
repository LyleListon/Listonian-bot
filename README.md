# Arbitrage Bot

A Python-based arbitrage bot with Flashbots integration for MEV protection.

## Features

- Flash loan arbitrage execution
- Flashbots RPC integration
- MEV protection
- Multi-path arbitrage optimization
- Price impact analysis
- Gas optimization
- Thread-safe operations
- Async/await patterns

## Requirements

- Python 3.12+
- Web3.py
- Aiohttp
- Ethereum node access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/listonian/arbitrage-bot.git
cd arbitrage-bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate.bat  # Windows
```

3. Install dependencies:
```bash
pip install -e .
```

## Configuration

1. Create a `configs/config.json` file with your settings:
```json
{
    "provider_url": "YOUR_ETH_NODE_URL",
    "chain_id": 8453,  # Base mainnet
    "private_key": "YOUR_PRIVATE_KEY",
    "tokens": {
        "WETH": "0x4200000000000000000000000000000006",
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    }
}
```

2. Set up Flashbots authentication:
```json
{
    "flashbots": {
        "relay_url": "https://relay.flashbots.net",
        "auth_signer_key": "YOUR_FLASHBOTS_KEY"
    }
}
```

## Usage

Run the example script:
```bash
python complete_arbitrage_example.py
```

## Architecture

The bot follows a modular architecture:

- `core/`: Core functionality
  - `web3/`: Web3 interactions
  - `dex/`: DEX integrations
  - `flash_loan_manager.py`: Flash loan management
- `integration/`: External integrations
  - `flashbots_integration.py`: Flashbots RPC
  - `mev_protection.py`: MEV protection
- `utils/`: Utility modules
  - `config_loader.py`: Configuration
  - `async_manager.py`: Async operations

## Development

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Format code:
```bash
black .
isort .
```

4. Type checking:
```bash
mypy .
```

## License

MIT License. See LICENSE file for details.
