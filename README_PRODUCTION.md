"...readyan Arbitrage Bot - Production Guide

This guide provides instructions for running the Listonian Arbitrage Bot in production mode with real blockchain data.

## Overview

The Listonian Arbitrage Bot is designed to detect and execute arbitrage opportunities on the Base blockchain. It scans for DEXes, finds pools, and identifies price discrepancies that can be exploited for profit.

## Current Configuration

The bot is currently configured with the following settings:

- **Environment**: Production with real blockchain data
- **Blockchain**: Base (Chain ID: 8453)
- **Wallet**: 0x257a30645bF0C91BC155bd9C01BD722322050F7b
- **RPC Providers**: 
  - Primary: Alchemy (https://base-mainnet.g.alchemy.com/v2/...)
  - Fallback: Infura (https://base-mainnet.infura.io/v3/...)
- **DEXes Monitored**: BaseSwap, Aerodrome, SushiSwap
- **Trading Parameters**:
  - Minimum Profit Threshold: $0.25 (execute any trade that equals to or exceeds a $0.25 net profit)
  - Maximum Position Size: 1.0 ETH
  - Slippage Tolerance: 0.5%
  - Gas Price Multiplier: 1.1 (10% above base gas price)
  - Maximum Gas Price: 100 GWEI

## Running the Bot

### Starting the Bot

To start the bot in production mode:

```bash
python Listonian-bot/scripts/run_production.py
```

This script will:
1. Load environment variables from `.env.production`
2. Stop any running MCP servers
3. Test the blockchain connection
4. Start the MCP server with production configuration
5. Test the MCP server
6. Keep the script running to maintain the MCP server

### Stopping the Bot

To stop the bot, press `Ctrl+C` in the terminal where it's running.

### Testing the Bot

To test if the bot is working correctly:

```bash
python Listonian-bot/scripts/test_production.py
```

This script will:
1. Test the API connection
2. Test the scan_dexes tool
3. Test the get_factory_pools tool

### Testing Blockchain Connection

To test the blockchain connection:

```bash
python Listonian-bot/scripts/test_blockchain_connection.py
```

This script will:
1. Test the primary RPC connection
2. Test the fallback RPC connection
3. Test the wallet connection
4. Test the Basescan API

## Monitoring

### Health Monitoring

To monitor the health of the bot:

```bash
python Listonian-bot/scripts/monitor_health.py
```

This script will:
1. Check if the process is running
2. Check if the service is active
3. Check if the API is healthy
4. Check if the logs are fresh

### Logs

The bot logs are stored in the `logs` directory. You can view them with:

```bash
tail -f Listonian-bot/logs/base_dex_scanner_mcp.log
```

## Configuration

The bot's configuration is stored in the `.env.production` file. You can modify this file to change the bot's behavior.

### Important Settings

- `MIN_PROFIT_THRESHOLD_USD`: The minimum profit threshold in USD. The bot will only execute trades that exceed this threshold.
- `MAX_POSITION_SIZE_ETH`: The maximum position size in ETH. The bot will not execute trades larger than this.
- `SLIPPAGE_TOLERANCE`: The slippage tolerance in basis points (1/100 of a percent).
- `GAS_PRICE_MULTIPLIER`: The gas price multiplier. The bot will use this to calculate the gas price for transactions.
- `MAX_GAS_PRICE_GWEI`: The maximum gas price in GWEI. The bot will not execute trades if the gas price exceeds this.

## Troubleshooting

### Common Issues

- **API Connection Failed**: Make sure the MCP server is running and the API endpoint is correct.
- **Blockchain Connection Failed**: Make sure the RPC endpoints are correct and accessible.
- **Wallet Connection Failed**: Make sure the wallet address and private key are correct.
- **No Pools Found**: This is normal when the bot is first starting up. It will take some time to index all the pools.
- **No Arbitrage Opportunities Found**: This is normal. The bot will only find arbitrage opportunities when there are price discrepancies between DEXes.

### Restarting the Bot

If you encounter issues, you can restart the bot by:

1. Stopping the current process with `Ctrl+C`
2. Starting a new process with `python Listonian-bot/scripts/run_production.py`

## Security Considerations

- **Private Key**: The private key is stored in the `.env.production` file. Make sure this file is secure and not accessible to unauthorized users.
- **API Key**: The API key is also stored in the `.env.production` file. This key is used to authenticate API requests.
- **Firewall**: If you're exposing the API to the internet, make sure to configure your firewall to only allow access from trusted IPs.

## Conclusion

The Listonian Arbitrage Bot is now configured to run in production mode with real blockchain data. It will continuously scan for arbitrage opportunities and execute trades when profitable opportunities are found.

For more detailed information, refer to the [Production Deployment Guide](./docs/PRODUCTION_DEPLOYMENT.md).