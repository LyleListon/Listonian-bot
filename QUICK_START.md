# Quick Start Guide

This guide will help you get the arbitrage bot system up and running quickly.

## Prerequisites

- Python 3.9 or higher
- Required Python packages (install using `pip install -r requirements.txt`)
- Ethereum wallet with private key
- RPC endpoints for the blockchain networks you want to monitor

## Step 1: Configure Environment Variables

Create a `.env.production` file in the root directory with the following variables:

```
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY
ETH_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_API_KEY
PRIVATE_KEY=YOUR_PRIVATE_KEY
WALLET_ADDRESS=YOUR_WALLET_ADDRESS
PROFIT_RECIPIENT=YOUR_PROFIT_RECIPIENT_ADDRESS
ALCHEMY_API_KEY=YOUR_ALCHEMY_API_KEY
COINGECKO_API_KEY=YOUR_COINGECKO_API_KEY
DEFILLAMA_API_KEY=YOUR_DEFILLAMA_API_KEY
DEXSCREENER_API_KEY=YOUR_DEXSCREENER_API_KEY
FLASHBOTS_AUTH_KEY=YOUR_FLASHBOTS_AUTH_KEY
MEMORY_BANK_PATH=data/memory_bank
LOG_LEVEL=INFO
SIMULATE_TRADES=true
USE_REAL_DATA_ONLY=true
MAX_CONCURRENT_REQUESTS=10
MIN_PROFIT_ETH=0.01
MAX_SLIPPAGE=0.5
GAS_LIMIT=500000
MAX_PRIORITY_FEE=2
DASHBOARD_PORT=9050
```

Replace the placeholders with your actual values.

## Step 2: Run the System

You can run the entire system using the `run_all.py` script:

```bash
python run_all.py --use-real-data --clear-memory
```

This will:
1. Clear the memory bank (if `--clear-memory` is specified)
2. Start the arbitrage bot
3. Start the dashboard
4. Open the dashboard in your default browser

## Step 3: Access the Dashboard

The dashboard is available at `http://localhost:9050` by default. You can change the port by setting the `DASHBOARD_PORT` environment variable.

## Step 4: Monitor and Configure

1. Use the dashboard to monitor the bot's performance
2. Adjust the configuration in `config.json` as needed
3. Restart the system to apply changes

## Troubleshooting

### Rate Limiting

If you encounter rate limiting issues, try the following:

1. Use multiple RPC providers (Alchemy, Infura, etc.)
2. Reduce the frequency of price checks
3. Implement exponential backoff for retries

### Dashboard Not Loading

If the dashboard is not loading, check the following:

1. Make sure the dashboard process is running
2. Verify the dashboard port (default is 9050)
3. Check the dashboard logs for errors

### Bot Not Finding Opportunities

If the bot is not finding arbitrage opportunities, check the following:

1. Make sure you have configured the correct token pairs
2. Verify that the DEXes you are monitoring have sufficient liquidity
3. Adjust the profit threshold in the configuration

## Next Steps

Once you have the system running, you can:

1. Add more token pairs to monitor
2. Integrate with additional DEXes
3. Implement more sophisticated arbitrage strategies
4. Set up alerts for profitable opportunities
