Technical Context

## Core Technologies

### 1. Web3 Stack
- **Web3.py**: Async version for Ethereum interaction
  * Using AsyncWeb3 for all RPC calls
  * Custom retry middleware implementation
  * 60-second timeout configuration
  * Exponential backoff retry pattern

### 2. DEX Integration
- **BaseSwap V2**
  * Contract ABIs in `/abi` directory
  * Token decimal handling (USDC=6, WETH/DAI=18)
  * Reserve calculation with proper ordering
  * Price impact calculations

- **SwapBased**
  * Similar to BaseSwap implementation
  * Factory contract at 0xb5620F90e803C7F957A9EF351B8DB3C746021BEa
  * Custom pair contract handling

### 3. Dashboard
- **WebSocket Server**
  * Real-time price updates
  * Market data streaming
  * Performance metrics
  * Connection management

## Key Files and Their Roles

### Core Web3
1. `web3_manager.py`
   - Manages RPC connections
   - Handles contract interactions
   - Implements retry logic
   - Manages Web3 state

2. `base_dex_v2.py`
   - Base class for V2 DEX implementations
   - Defines common interface
   - Handles price calculations
   - Manages reserves

3. `baseswap.py`
   - Implements BaseSwap V2 interface
   - Handles token decimals
   - Manages pair contracts
   - Calculates prices

### Market Analysis
1. `market_analyzer.py`
   - Processes price data
   - Tracks market conditions
   - Monitors opportunities
   - Calculates metrics

2. `websocket_server.py`
   - Streams market data
   - Handles client connections
   - Manages data flow
   - Monitors performance

## Dependencies and Versions

### Python Packages
```
web3==6.11.3
aiohttp==3.9.1
websockets==11.0.3
```

### Contract Dependencies
1. **Token Standards**
   - ERC20 for token interactions
   - Custom pair contracts for DEXes
   - Factory contracts for pair creation

2. **ABIs**
   - `baseswap_pair.json`: Pair contract ABI
   - `baseswap_factory.json`: Factory contract ABI
   - `ERC20.json`: Token standard ABI

## Configuration

### RPC Settings
```json
{
    "timeout": 60,
    "retries": 3,
    "backoff_factor": 0.5
}
```

### Token Configuration
```json
{
    "WETH": {
        "address": "0x4200000000000000000000000000000000000006",
        "decimals": 18
    },
    "USDC": {
        "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "decimals": 6
    },
    "DAI": {
        "address": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        "decimals": 18
    }
}
```

## Development Setup

### Environment Variables
```bash
BASE_RPC_URL="https://base-mainnet.g.alchemy.com/v2/..."
CHAIN_ID="8453"
WALLET_ADDRESS="0x..."
PRIVATE_KEY="..."
DASHBOARD_PORT="5001"
DASHBOARD_WEBSOCKET_PORT="8772"
```

### Running the System
1. Start the bot:
   ```bash
   python production.py
   ```

2. Monitor the dashboard:
   ```bash
   python start_dashboard.py
   ```

## Common Issues and Solutions

### 1. Price Data Issues
- **Symptom**: Extreme price values
- **Cause**: Token decimal mismatch
- **Solution**: Proper decimal handling in reserves

### 2. RPC Timeouts
- **Symptom**: Request failures
- **Cause**: Network latency
- **Solution**: Retry middleware with backoff

### 3. WebSocket Connection
- **Symptom**: Data not updating
- **Cause**: Connection drops
- **Solution**: Auto-reconnect logic

## Monitoring and Maintenance

### 1. System Health
- Watch RPC success rates
- Monitor memory usage
- Track WebSocket connections
- Check price accuracy

### 2. Performance Metrics
- Request latency
- Price update frequency
- Memory consumption
- CPU utilization

Last Updated: 2025-02-10
