# Listonian Bot Setup Guide

## Prerequisites

Before setting up the Listonian Bot, ensure you have the following prerequisites:

1. **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows 10/11
2. **Python**: Version 3.9 or higher
3. **Node.js**: Version 14 or higher (for dashboard components)
4. **Git**: For cloning the repository
5. **Ethereum Wallet**: With sufficient funds for gas fees
6. **API Keys**: For blockchain providers (Infura, Alchemy, etc.)
7. **Hardware**: Minimum 4GB RAM, 2 CPU cores, 50GB storage

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-organization/Listonian-bot.git
cd Listonian-bot
```

### 2. Create and Activate Virtual Environment

#### For Linux/macOS:
```bash
python -m venv venv
source venv/bin/activate
```

#### For Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Node.js Dependencies

```bash
npm install
```

### 5. Configure Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Blockchain Providers
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/YOUR_API_KEY
BSC_RPC_URL=https://bsc-dataseed.binance.org/
BASE_RPC_URL=https://mainnet.base.org

# Wallet Configuration
WALLET_PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=your_wallet_address_here

# API Keys
INFURA_API_KEY=your_infura_api_key
ALCHEMY_API_KEY=your_alchemy_api_key

# MEV Protection
FLASHBOTS_RELAY_URL=https://relay.flashbots.net/

# Flash Loan Providers
AAVE_LENDING_POOL_ADDRESS=0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9

# Bot Configuration
MIN_PROFIT_THRESHOLD=0.5
MAX_SLIPPAGE=1.0
GAS_PRICE_MULTIPLIER=1.1
MAX_TRADE_AMOUNT=1.0

# Dashboard Configuration
DASHBOARD_PORT=8080
API_PORT=8000
ENABLE_AUTHENTICATION=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure_password_here

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/bot.log
```

### 6. Initialize the Database

```bash
python scripts/init_db.py
```

### 7. Run Initial Tests

```bash
pytest tests/
```

## Starting the Bot

### Start the Dashboard

```bash
python run_dashboard.py
```

The dashboard will be available at `http://localhost:8080`

### Start the API Server

```bash
python bot_api_server.py
```

The API will be available at `http://localhost:8000`

### Start the Bot

```bash
python run_bot.py
```

## Verifying Installation

1. Open the dashboard in your browser: `http://localhost:8080`
2. Log in with the admin credentials set in your `.env` file
3. Check the "System Status" section to ensure all components are running
4. Review the "Logs" section for any errors or warnings

## Troubleshooting

### Common Issues

#### Connection Errors
- Verify your RPC URLs and API keys
- Check your internet connection
- Ensure the blockchain nodes are operational

#### Authentication Issues
- Reset your admin password using `python scripts/reset_password.py`
- Check for correct environment variables

#### Performance Issues
- Increase the hardware resources
- Adjust the bot configuration for lower frequency trading
- Check for memory leaks using `python scripts/memory_check.py`

### Getting Help

If you encounter issues not covered in this guide:

1. Check the logs in the `logs/` directory
2. Review the [Troubleshooting Guide](troubleshooting.md)
3. Open an issue on the GitHub repository
4. Contact support at support@listonian-bot.com

## Next Steps

After successful installation:

1. [Configure the bot](configuration.md) for your specific trading strategy
2. Set up [monitoring and alerts](monitoring.md)
3. Learn about [deployment options](deployment.md) for production environments
4. Explore [advanced features](advanced_features.md)
