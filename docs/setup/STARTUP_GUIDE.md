# Quick Start Guide: Listonian Arbitrage Bot

This guide provides step-by-step instructions for setting up and running the Listonian Arbitrage Bot with all its components.

## 1. Environment Setup

```bash
# Create and activate Python environment
python -m venv venv
.\venv\Scripts\activate  # On Windows
# OR
source venv/bin/activate  # On Unix/Linux

# Install dependencies
pip install -r requirements.txt
```

## 2. Configuration

1. Create a `.env` file in the root directory:

```
# Network Configuration
RPC_URL=https://your-rpc-provider.com/your-api-key
CHAIN_ID=1  # Ethereum Mainnet (use 8453 for Base)

# Wallet Configuration
PRIVATE_KEY=your_private_key_here
PROFIT_RECIPIENT=0xYourAddressHere

# Flashbots Configuration
FLASHBOTS_RELAY_URL=https://relay.flashbots.net
FLASHBOTS_AUTH_KEY=your_flashbots_auth_key

# API Keys
DEFILLAMA_API_KEY=your_defillama_api_key
DEXSCREENER_API_KEY=your_dexscreener_api_key
DEFIPULSE_API_KEY=your_defipulse_api_key
```

2. Update `config.json` with your trading parameters:

```json
{
  "trading": {
    "min_profit_threshold_usd": 10.0,
    "max_trade_size_eth": 5.0,
    "slippage_tolerance": 0.5,
    "max_gas_price_gwei": 50
  },
  "discovery": {
    "discovery_interval_seconds": 3600,
    "auto_validate": true,
    "storage_dir": "data/dexes",
    "storage_file": "dexes.json"
  },
  "flashbots": {
    "use_flashbots": true,
    "max_block_number_target": 3,
    "priority_fee_gwei": 2
  },
  "analytics": {
    "profit_tracking_enabled": true,
    "alert_threshold_usd": 100.0,
    "journal_enabled": true
  },
  "performance": {
    "max_concurrent_tasks": 10,
    "memory_limit_mb": 1024,
    "cache_ttl_seconds": 60,
    "use_shared_memory": true
  }
}
```

## 3. Starting the Bot

### Option 1: All-in-One Startup

```bash
# Start the bot with dashboard
python start_bot_with_dashboard.py
```

### Option 2: Component-by-Component Startup

1. Start the Dashboard (Terminal 1):
```bash
.\venv\Scripts\activate
python run_dashboard.py
```

2. Start the Bot (Terminal 2):
```bash
.\venv\Scripts\activate
python run_bot.py
```

## 4. Accessing the Dashboard

1. Open your browser and navigate to `http://localhost:3000`
2. The dashboard provides:
   - Real-time profit tracking
   - System performance metrics
   - DEX discovery status
   - Arbitrage opportunity visualization
   - Trading journal and analytics

## 5. Verification

1. Dashboard:
   - Check console for successful startup
   - Verify WebSocket connections
   - Monitor system metrics display
   - Check DEX discovery status

2. Bot:
   - Verify DEX discovery is working
   - Check Flashbots integration
   - Monitor arbitrage opportunity detection
   - Verify trade execution

3. Common Checks:
   - Network connectivity
   - WebSocket status
   - Memory and CPU usage
   - Log output

## 6. Component Testing

You can test individual components using the example scripts:

1. DEX Discovery:
```bash
python run_dex_discovery_example.py
```

2. Flashbots Integration:
```bash
python run_flashbots_example.py
```

3. Real-Time Metrics:
```bash
python run_real_time_metrics_example.py
```

4. Performance Optimization:
```bash
python run_performance_optimization_example.py
```

5. Multi-Path Arbitrage:
```bash
python run_multi_path_arbitrage_example.py
```

6. Advanced Analytics:
```bash
python run_advanced_analytics_example.py
```

## 7. Common Issues

1. RPC Connection Issues:
   - Check your RPC provider status
   - Verify API key and rate limits
   - Consider using a backup RPC provider

2. WebSocket Connection Issues:
   - Check port availability
   - Verify network connectivity
   - Check for firewall restrictions

3. Memory Usage Issues:
   - Adjust `memory_limit_mb` in config.json
   - Monitor memory usage with dashboard
   - Check for memory leaks in logs

4. Performance Issues:
   - Adjust `max_concurrent_tasks` in config.json
   - Monitor CPU usage with dashboard
   - Optimize resource-intensive operations

## 8. Monitoring

- Dashboard logs: Check terminal output
- System metrics: Available in dashboard UI
- Bot logs: `logs/arbitrage.log`
- Error logs: `logs/error.log`
- Trading journal: `data/journal/`

## Important Notes

1. The dashboard runs on http://localhost:3000
2. Keep terminals running for live updates
3. Monitor system resources
4. Check WebSocket connections
5. Review trade history in dashboard
6. Backup your private keys and configuration

## Troubleshooting

If you encounter issues:
1. Check terminal output for errors
2. Verify environment variables
3. Check log files in the `logs/` directory
4. Verify network connectivity
5. Check system resources
6. Restart components if necessary

For more detailed troubleshooting, see [TROUBLESHOOTING.md](../TROUBLESHOOTING.md).
