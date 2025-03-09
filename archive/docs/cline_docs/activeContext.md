Active Context

## Current State
- System operational with verified container health and data persistence.
- Fixed Dockerfile and devcontainer.json configuration.
- Addressing price data and RPC reliability issues in DEX integrations.

## Memory Bank Initialization
- Memory bank initialized on 2025-02-09

## System Startup Instructions
1. **Environment Setup**
   - Required environment variables in .env.production:
     ```
     BASE_RPC_URL="https://base-mainnet.g.alchemy.com/v2/..."
     CHAIN_ID="8453"
     WALLET_ADDRESS="0x..."
     PRIVATE_KEY="..."
     DASHBOARD_PORT="5001"
     DASHBOARD_WEBSOCKET_PORT="8772"
     ```

2. **Configuration Verification**
   - Check configs/config.json for:
     * Active DEXes:
       - BaseSwap (enabled)
       - SwapBased (enabled)
       - PancakeSwap (enabled)
       - Others disabled (Uniswap V3, RocketSwap, Aerodrome)
     * Token Settings:
       ```
       WETH: 0x4200...0006 (18 decimals, 0.001-10.0 limits)
       USDC: 0x8335...2913 (6 decimals, 1.0-50000.0 limits)
       DAI:  0x50c5...0Cb (18 decimals, 1.0-50000.0 limits)
       ```
     * Process Settings:
       - Dashboard ports: 5000-5010
       - WebSocket ports: 8771-8780
       - Max instances: 3
       - Max memory: 1024MB
       - Max CPU: 50%

3. **Starting the Bot**
   ```bash
   # Start the main arbitrage bot
   python production.py
   ```

4. **Starting the Dashboard**
   ```bash
   # Launch monitoring dashboard
   python start_dashboard.py
   ```

5. **Verification Steps**
   - Check container health: `python test_container_health.py`
   - Verify WebSocket connection on port 8772
   - Monitor dashboard on port 5001
   - Check logs for proper price data and RPC connections
   - Verify active DEXes:
     * BaseSwap router: 0x327Df1E6de05895d2ab08513aaDD9313Fe505d86
     * SwapBased factory: 0xb5620F90e803C7F957A9EF351B8DB3C746021BEa
     * PancakeSwap router: 0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86

## Active Development
1. **Price Data Issues** (IN PROGRESS)
   - **Problem:** Incorrect price data from DEX pairs, especially USDC pairs showing extreme values
   - **Root Cause:** 
     * Token ordering not properly handled in reserves calculation
     * Token decimals not properly adjusted
     * RPC timeouts causing data fetch failures
   - **Solution Progress:**
     * Added proper token decimal handling in BaseSwapDEX
     * Fixed token ordering in reserves calculation
     * Implemented retry middleware for RPC calls
     * Added exponential backoff for failed requests
     * Enhanced error handling and logging

2. **RPC Reliability** (IN PROGRESS)
   - **Problem:** RPC requests timing out and failing
   - **Solution:**
     * Increased timeout to 60 seconds
     * Added retry middleware with exponential backoff
     * Improved error handling and logging
     * Added request retries for contract calls

## Component Relationships
For the next assistant, here's how the key components interact:

1. **Web3 Layer**
   - `web3_manager.py`: Core Web3 interaction layer
     * Handles RPC connections and retries
     * Manages contract interactions
     * Provides both sync and async methods

2. **DEX Layer**
   - `base_dex_v2.py`: Base class for V2 DEX implementations
     * Defines common DEX functionality
     * Handles price calculations and reserves
   - `baseswap.py`: BaseSwap DEX implementation
     * Extends base_dex_v2
     * Handles token decimals and ordering
     * Implements retry logic for contract calls

3. **Data Flow**
   ```
   web3_manager.py
      ↓
   base_dex_v2.py
      ↓
   baseswap.py
      ↓
   market_analyzer.py
      ↓
   websocket_server.py
      ↓
   dashboard
   ```

## Current Focus
- Testing price data accuracy after fixes
- Monitoring RPC reliability with new retry system
- Validating token decimal handling

## Next Steps
1. **Immediate Tasks**
   - Test price data accuracy for all token pairs
   - Monitor RPC connection stability
   - Verify proper decimal handling
   - Test retry system under load

2. **Technical Monitoring**
   - Track RPC request success rates
   - Monitor price data accuracy
   - Check token decimal calculations
   - Verify proper error handling

## Notes
- Token decimals must be handled carefully (USDC=6, WETH/DAI=18)
- RPC requests use exponential backoff (0.5s, 1s, 2s)
- Price calculations depend on correct token ordering
- Always verify reserves match on-chain data
- Minimum profit threshold: 0.05 USD
- Maximum price impact: 1%
- Slippage tolerance: 0.1%

Last Updated: 2025-02-10
