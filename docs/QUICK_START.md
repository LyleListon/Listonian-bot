# Quick Start Guide

## Prerequisites
- Python 3.8 or higher
- Git (for cloning the repository)
- Node.js and npm (for web3 dependencies)

## Configuration

1. Create `configs/config.json` with your settings:
```json
{
    "network": {
        "rpc_url": "YOUR_RPC_URL",
        "chain_id": 8453,  // Base chain ID
        "ws_url": "YOUR_WSS_URL"  // Optional WebSocket URL
    },
    "trading": {
        "min_profit_usd": 5.0,
        "max_trade_size_usd": 1000.0,
        "safety": {
            "protection_limits": {
                "max_slippage_percent": 1.0
            }
        }
    },
    "dexes": {
        "baseswap": {
            "router": "0x327Df1E6de05895d2ab08513aaDD9313Fe505d86",
            "factory": "0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB"
        },
        "swapbased": {
            "router": "0x12345...",  // Add your SwapBased router
            "factory": "0x67890..."  // Add your SwapBased factory
        },
        "aerodrome": {
            "router": "0xabcde...",  // Add your Aerodrome router
            "factory": "0xfghij..."  // Add your Aerodrome factory
        }
    }
}
```

2. Create `configs/wallet_config.json` with your wallet details:
```json
{
    "address": "YOUR_WALLET_ADDRESS",
    "private_key": "YOUR_PRIVATE_KEY"
}
```

## Starting the Bot

### Windows
```bash
start_all.bat
```

### Linux/Mac
```bash
chmod +x start_all.sh
./start_all.sh
```

## Monitoring

1. The dashboard will be available at: `http://localhost:3000`

2. Monitor logs in the `logs` directory:
   - `bot_TIMESTAMP.log` - Main bot logs
   - `dashboard_TIMESTAMP.log` - Dashboard logs
   - `setup_TIMESTAMP.log` - Setup logs
   - `*.err` files contain error logs

## Stopping the Bot

- Windows: Close the command prompt windows or press Ctrl+C in each window
- Linux/Mac: Press Ctrl+C in the terminal running start_all.sh

## Security Notes

1. Never share your private key
2. Use a dedicated wallet for the bot
3. Start with small trade sizes
4. Monitor the logs regularly
5. Keep your RPC endpoints private

## Troubleshooting

1. If the bot fails to start:
   - Check the error logs in `logs/setup_*.err`
   - Verify your Python installation
   - Ensure all config files are present and valid

2. If trades aren't executing:
   - Check RPC connection
   - Verify wallet has sufficient funds
   - Check gas prices
   - Review profit thresholds

3. If dashboard isn't loading:
   - Check if port 3000 is available
   - Review dashboard logs
   - Ensure all dependencies are installed

## Support

For issues and updates, please refer to:
- GitHub repository
- Documentation in `docs/` directory
- System logs in `logs/` directory