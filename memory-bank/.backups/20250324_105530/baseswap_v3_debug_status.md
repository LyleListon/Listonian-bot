# BaseSwap V3 Integration Debug Status

## Current State
- Investigating issues with BaseSwap V3 pool queries on Base chain
- Getting "execution reverted" errors when calling getPool function

## Contract Addresses (Verified by User)
Factory: 0x327Df1E6de05895d2ab08513aaDD9313Fe505d86
Router: 0x257a30645bF0C91BC155bd9C01BD722322050F7b
Quoter: 0x0C1Ef7cA95C6C2CeF48eDFc51CE1BeB2Aa2D8410

## Investigation Progress

1. Initial Problem:
   - Web3 calls to getPool function returning '0x' (no contract code)
   - Found we were using wrong factory address

2. After Address Fix:
   - Contract exists (no more '0x' code response)
   - Function calls now revert with "execution reverted" error
   - Error occurs for all fee tiers (100, 500, 3000)

3. Current Focus:
   - Investigating parameter mismatch between ABI and contract
   - ABI shows parameters as "tokenA" and "tokenB"
   - Code currently passes as "token0" and "token1"

## Next Steps for Investigation
1. Verify BaseSwap V3 factory interface matches our ABI
2. Check if token ordering (token0/token1) is correct
3. Validate fee tier values are supported
4. Consider if initialization is needed for pools

## Files Modified
1. config.json - Updated contract addresses
2. web3_manager.py - Added debug logging

## Relevant Logs
```
2025-03-24 10:40:48,604 - DEBUG - Getting pool for tokens 0x4200...0006, 0x8335...2913 with fee 100
2025-03-24 10:40:48,905 - ERROR - execution reverted
```

## Notes for Next Assistant
- The contract addresses have been verified by user
- We're getting execution reverted errors, not invalid function signature errors
- Parameter names in ABI (tokenA/tokenB) don't match code usage (token0/token1)
- Consider checking BaseSwap V3 documentation or similar implementations for correct interface