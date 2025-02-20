# Dashboard Integration Guide

## Current Status
We've been working on integrating a dynamic dashboard with real-time updates. Here's what's been done and what needs attention:

### Completed Work
1. Set up basic server structure with FastAPI
2. Implemented WebSocket support for real-time updates
3. Created test page with:
   - Memory bank status display
   - Real-time opportunity tracking
   - Trade history visualization
   - Performance charts
   - Responsive styling
4. Fixed memory bank to use eventlet instead of asyncio
5. Fixed portfolio tracker to prevent recursive nesting of trade data
6. Updated DEX implementations (base_dex.py, baseswap.py, base_dex_v2.py) to use eventlet instead of asyncio

### Current Issues
We're seeing coroutine warnings from several components that need to be converted from asyncio to eventlet:
1. DistributionManager.initialize
2. ExecutionManager.initialize
3. WebSocketServer.initialize
4. create_storage_hub
5. create_gas_optimizer
6. initialize_market_analyzer
7. create_dex_manager

### Next Steps
1. Update app.py to handle component initialization properly:
   - Remove all async/await syntax
   - Use eventlet.sleep(INIT_WAIT) between component initializations
   - Call initialize() methods directly instead of awaiting them
   - Use synchronous versions of create_* functions

2. Key files that need attention:
   - arbitrage_bot/dashboard/app.py (main focus)
   - arbitrage_bot/core/distribution/manager.py
   - arbitrage_bot/core/execution/manager.py
   - arbitrage_bot/dashboard/websocket_server.py
   - arbitrage_bot/core/storage/factory.py
   - arbitrage_bot/core/gas/gas_optimizer.py
   - arbitrage_bot/core/analysis/memory_market_analyzer.py
   - arbitrage_bot/core/dex/dex_manager.py

3. Pattern for converting async code:
   ```python
   # Before:
   async def initialize(self):
       result = await some_async_function()
       return result

   # After:
   def initialize(self):
       result = some_sync_function()
       return result
   ```

4. For component initialization in app.py:
   ```python
   # Before:
   await component.initialize()

   # After:
   component.initialize()
   eventlet.sleep(INIT_WAIT)  # Add delay between initializations
   ```

### Important Notes
1. All async/await code should be converted to use eventlet
2. Add INIT_WAIT (2 seconds) between component initializations
3. Keep error handling and logging in place
4. Maintain the same initialization order of components
5. Verify each component is ready before proceeding
6. Use eventlet.monkey_patch() at the start of app.py

### Testing
After making changes:
1. Run start_dashboard.ps1
2. Check for coroutine warnings
3. Verify all components initialize properly
4. Test WebSocket connections
5. Monitor memory usage for any leaks

### Environment Details
- Working Directory: d:/Listonian-bot
- API Keys and Credentials: Already configured in .env.production
- Base Network RPC URL: https://base-mainnet.g.alchemy.com/v2/[key]
- Dashboard Port: 5001

This should help the next assistant quickly understand the current state and continue the work efficiently.