System Startup Guide

## Required Environment Variables

```bash
# Core Configuration
BASE_RPC_URL="https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY"
CHAIN_ID="8453"  # Base mainnet
WALLET_ADDRESS="your_wallet_address"
PRIVATE_KEY="your_private_key"

# Dashboard Configuration
DASHBOARD_PORT="5001"
DASHBOARD_WEBSOCKET_PORT="8772"
```

## Key Configuration Files

1. **configs/config.json**
   - Main configuration file
   - Contains DEX settings
   - Network parameters
   - Trading pairs

2. **configs/wallet_config.json**
   - Wallet configuration
   - Gas settings
   - Transaction parameters

3. **arbitrage_bot/configs/data/dex_config.json**
   - DEX-specific settings
   - Contract addresses
   - Trading parameters

## Core Components and Dependencies

### 1. Web3 Layer
```
arbitrage_bot/core/web3/web3_manager.py
├── Handles RPC connections
├── Manages contract interactions
└── Implements retry logic
```

### 2. DEX Integration
```
arbitrage_bot/core/dex/
├── base_dex_v2.py (Base class)
├── baseswap.py (BaseSwap implementation)
└── swapbased.py (SwapBased implementation)
```

### 3. Market Analysis
```
arbitrage_bot/core/
├── analysis/market_analyzer.py
├── models/opportunity.py
└── execution/detect_opportunities.py
```

### 4. Dashboard
```
arbitrage_bot/dashboard/
├── app.py (Flask application)
├── run.py (Dashboard startup)
└── websocket_server.py (Real-time updates)
```

## Startup Sequence

1. **Initialize Configuration**
   ```bash
   # Verify config files exist and are properly formatted
   configs/config.json
   configs/wallet_config.json
   arbitrage_bot/configs/data/dex_config.json
   ```

2. **Start Main Bot**
   ```bash
   # Start the main arbitrage bot
   python production.py
   ```

3. **Start Dashboard**
   ```bash
   # In a separate terminal
   python start_dashboard.py
   ```

## Component Initialization Order

1. **Web3 Manager**
   - Establishes RPC connection
   - Verifies chain connection
   - Sets up retry middleware

2. **DEX Initialization**
   - Loads contract ABIs from /abi directory
   - Verifies contract addresses
   - Sets up price feeds

3. **Market Analyzer**
   - Begins monitoring pairs
   - Starts opportunity detection
   - Initializes performance tracking

4. **Dashboard**
   - Starts Flask server
   - Initializes WebSocket
   - Begins data streaming

## Common Issues and Solutions

### 1. RPC Connection
If RPC connection fails:
- Verify BASE_RPC_URL is correct
- Check API key validity
- Ensure network connectivity
- Monitor rate limits

### 2. Contract Verification
If contract verification fails:
- Check contract addresses in config
- Verify ABI files exist in /abi
- Confirm chain ID matches network
- Check contract deployment status

### 3. Price Data
If price data is incorrect:
- Verify token decimals in configs
- Check pair contract addresses
- Monitor reserve updates
- Validate price calculations

### 4. Dashboard Connection
If dashboard won't connect:
- Check port availability
- Verify WebSocket port is open
- Monitor memory usage
- Check log files

## Monitoring and Verification

### 1. System Health
```bash
# Check container health
python test_container_health.py

# Monitor system resources
python start_monitoring.py
```

### 2. Log Files
Important log locations:
```
logs/            # System logs
monitoring_data/ # Performance data
analytics/       # Trading analytics
```

### 3. Dashboard Access
Once running, access:
- Main dashboard: http://localhost:5001
- WebSocket status: http://localhost:5001/status
- Performance metrics: http://localhost:5001/metrics

## Required Files Checklist

### Core Files
- [x] production.py
- [x] start_dashboard.py
- [x] configs/config.json
- [x] configs/wallet_config.json
- [x] arbitrage_bot/configs/data/dex_config.json

### Contract ABIs
- [x] abi/baseswap_pair.json
- [x] abi/baseswap_factory.json
- [x] abi/swapbased_factory.json
- [x] abi/swapbased_pair.json
- [x] abi/ERC20.json

### Core Components
- [x] arbitrage_bot/core/web3/web3_manager.py
- [x] arbitrage_bot/core/dex/base_dex_v2.py
- [x] arbitrage_bot/core/dex/baseswap.py
- [x] arbitrage_bot/core/dex/swapbased.py
- [x] arbitrage_bot/core/analysis/market_analyzer.py
- [x] arbitrage_bot/dashboard/app.py
- [x] arbitrage_bot/dashboard/websocket_server.py

Last Updated: 2025-02-10