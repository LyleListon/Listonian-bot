System Patterns

## Core Architecture

### Web3 Layer
1. **Web3 Manager Pattern**
   ```
   Web3Manager
   ├── Connection Management
   │   ├── Retry Middleware
   │   ├── Timeout Configuration
   │   └── Error Handling
   ├── Contract Interaction
   │   ├── Sync Methods
   │   └── Async Methods
   └── State Management
       ├── Chain ID
       └── Account Info
   ```

2. **DEX Abstraction Layers**
   ```
   BaseDEX
   └── BaseDEXV2
       ├── BaseSwapDEX
       ├── SwapBasedDEX
       └── PancakeSwapDEX
   ```

### Output Management Pattern
1. **Terminal Output Control**
   ```
   Output Manager
   ├── Log Rotation
   │   ├── Size-based rotation
   │   └── Time-based rotation
   ├── Output Filtering
   │   ├── Debug level control
   │   └── Category filtering
   └── Context Management
       ├── Buffer size monitoring
       └── Cleanup triggers
   ```

2. **Context Window Protection**
   - Monitor output volume
   - Implement log rotation
   - Use selective logging
   - Clean old logs regularly
   - Prevent context overflow

### Data Flow Patterns
1. **Price Data Pipeline**
   ```
   Web3 RPC
   ↓
   DEX Contract
   ↓
   Reserve Data
   ↓
   Price Calculation
   ↓
   Market Analysis
   ↓
   WebSocket
   ↓
   Dashboard
   ```

2. **Error Handling Pattern**
   ```
   Try Operation
   ↓
   Catch Error
   ↓
   Log Error
   ↓
   Retry Logic
   ↓
   Fallback/Recovery
   ```

## Key Design Patterns

### 1. Retry Pattern
- Exponential backoff (0.5s, 1s, 2s)
- Maximum 3 retries
- Status code based retry decisions
- Error logging at each attempt

### 2. Token Handling Pattern
```python
# Token Order Resolution
if token0_addr.lower() == token0.lower():
    reserve0 = reserves[0]
    reserve1 = reserves[1]
else:
    reserve0 = reserves[1]
    reserve1 = reserves[0]

# Decimal Adjustment
adjusted_amount = Decimal(amount) / Decimal(10 ** decimals)
```

### 3. Price Calculation Pattern
```python
# Base Price
price = reserve_out / reserve_in

# With Impact
impact = (expected_out - actual_out) / expected_out
adjusted_price = price * (1 - impact)
```

## Implementation Guidelines

### 1. Web3 Interactions
- Always use retry middleware
- Handle timeouts gracefully
- Log all RPC interactions
- Verify chain ID matches
- Check contract addresses

### 2. DEX Integration
- Verify token ordering
- Handle decimals properly
- Check reserves exist
- Validate price calculations
- Monitor price impact

### 3. Error Recovery
- Use exponential backoff
- Log error details
- Maintain state consistency
- Provide fallback options
- Monitor retry patterns

### 4. Output Management
- Implement log rotation
- Use selective logging levels
- Monitor context window size
- Clean logs periodically
- Filter debug output

## Best Practices

### 1. Token Operations
- Always use checksummed addresses
- Verify token existence
- Check decimal places
- Handle zero reserves
- Validate pair contracts

### 2. Price Data
- Sanity check values
- Compare across DEXes
- Monitor for outliers
- Track historical data
- Validate calculations

### 3. RPC Requests
- Use appropriate timeouts
- Implement retries
- Monitor rate limits
- Log request patterns
- Track success rates

### 4. Terminal Output
- Minimize debug output
- Rotate logs regularly
- Filter unnecessary info
- Monitor output size
- Clean old logs

## System Constraints

### 1. Technical Limits
- RPC rate limits
- Contract call gas costs
- WebSocket connection limits
- Memory usage bounds
- CPU utilization caps
- Context window size

### 2. Business Rules
- Minimum profit thresholds
- Maximum price impact
- Slippage tolerance
- Gas price limits
- Trade size bounds

Last Updated: 2025-02-10
