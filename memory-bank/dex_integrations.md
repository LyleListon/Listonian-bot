# DEX Integrations Status

## Currently Active DEXes (Base Network)

### 1. Aerodrome (V2)
- **Status**: Active
- **Factory**: 0x420DD381b31aEf6683db6B902084cB0FFECe40Da
- **Router**: 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43
- **Fee**: 30 bps
- **Features**: Standard V2 AMM

### 2. BaseSwap (V2)
- **Status**: Active
- **Factory**: 0xFDa619b6d20975be80A10332cD39b9a4b0FAa8BB
- **Router**: 0x327Df1E6de05895d2ab08513aaDD9313Fe505d86
- **Fee**: 30 bps
- **Features**: Standard V2 AMM

### 3. SwapBased (V2)
- **Status**: Active
- **Factory**: 0x36218B2F8dC32D43fb5EcF45F2E6113cd52Cc5B9
- **Router**: 0x36218B2F8dC32D43fb5EcF45F2E6113cd52Cc5B9
- **Fee**: 30 bps
- **Features**: Standard V2 AMM

## Supported But Not Currently Active

### 1. PancakeSwap (V3)
- **Status**: Supported but not configured
- **Features**: 
  * Concentrated liquidity
  * Multiple fee tiers
  * Advanced routing

### 2. Uniswap V3
- **Status**: Supported but not configured
- **Features**:
  * Concentrated liquidity
  * Multiple fee tiers
  * Advanced routing

### 3. RocketSwap (V2)
- **Status**: Supported but not configured
- **Features**: Standard V2 AMM

## Integration Details

### Protocol Types
- **V2 Protocol**: Standard AMM with constant product formula
- **V3 Protocol**: Concentrated liquidity with multiple fee tiers

### Common Features
- Async/await implementation
- Thread-safe operations
- Error handling with retries
- Balance verification
- Slippage protection

### Monitoring
- Health checks every 60 seconds
- Automatic recovery attempts
- Error tracking and reporting
- Performance metrics collection

## Token Support

### Active Tokens
- **WETH**: 0x4200000000000000000000000000000000000006
- **USDC**: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
- **USDT**: 0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb
- **DAI**: 0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb

## Performance Settings

### Path Finding
- Max Path Length: 4
- Min Profit Threshold: 0.001
- Max Paths to Check: 100
- Min Liquidity Ratio: 1.5
- Max Price Impact: 5%
- Parallel Search: Enabled
- Cache TTL: 30s

### Rate Limits
- Requests per Second: 5
- Max Backoff: 60s
- Batch Size: 10
- Cache TTL: 30s