# System Patterns

## DEX Implementation Architecture

### Inheritance Chain
```
BaseDEX (abstract)
├── BaseDEXV2
│   └── BaseSwap
└── BaseDEXV3
    ├── SwapBased
    ├── RocketSwapV3
    ├── BaseSwapV3
    └── PancakeSwap
```

### Configuration Flow
1. Config loaded from:
   - config.json (main config)
   - dex_config.json (DEX-specific config)
2. Configs merged by ConfigLoader
3. DexManager injects:
   - WETH address
   - Wallet config
   - Token configurations

### Initialization Pattern
1. DexManager loads config
2. For each enabled DEX:
   - Creates clean config
   - Injects required addresses
   - Initializes DEX instance
   - Verifies contracts
   - Sets up event listeners

### Contract Interaction Pattern
1. Base contract methods defined in BaseDEX
2. Version-specific methods in BaseDEXV2/V3
3. DEX-specific implementations override as needed
4. All contract calls use retry mechanism
5. Gas estimation handled by Web3Manager
6. Token addresses always checksummed

### Error Handling Pattern
1. Base error handling in BaseDEX
2. Standardized logging format
3. Error context preservation
4. Retry mechanism for transient failures
5. Validation for quoter responses

### Async Implementation
1. Core Components:
   - All DEX methods are async/await
   - Event handling is async
   - Price updates are async
   - Contract calls use async retry with backoff
   - File operations are async
   - Resource initialization is async
   - Cleanup operations are async

2. Web3 Integration:
   - Contract interactions are async
   - Transaction handling is async
   - Gas estimation is async
   - Event listening is async
   - Network calls are async

3. Memory Management:
   - Cache operations are async
   - State updates are async
   - Resource cleanup is async
   - Initialization sequence is async
   - Error recovery is async

### Thread Safety Pattern
1. Lock Management:
   - Initialization locks
   - Contract access locks
   - Cache access locks
   - Resource locks
   - Transaction nonce locks

2. Resource Protection:
   - Double-checked locking pattern
   - Atomic operations
   - Safe resource sharing
   - Concurrent access control
   - State consistency protection

3. Data Consistency:
   - Cache consistency
   - State consistency
   - Contract state consistency
   - Configuration consistency
   - Transaction ordering

### Resource Management Pattern
1. Initialization:
   - Async resource initialization
   - Proper error handling
   - Resource validation
   - State verification
   - Dependency management

2. Cleanup:
   - Async resource cleanup
   - Proper error recovery
   - Resource deallocation
   - State cleanup
   - Connection cleanup

3. Monitoring:
   - Resource usage tracking
   - Performance monitoring
   - Error tracking
   - State monitoring
   - Health checks

## Web3 Integration

### Web3Manager Pattern
1. Centralized web3 instance management
2. Contract loading and caching
3. Transaction building and sending
4. Gas price management
5. Token address validation

### Contract Loading Pattern
1. ABI files stored in /abi directory
2. Loaded on demand by Web3Manager
3. Cached for reuse
4. Version-specific ABIs supported
5. Contract existence verification

## Configuration Management

### Config Structure
1. Base configuration
   - Network settings
   - Global parameters
2. DEX configuration
   - Router addresses
   - Factory addresses
   - Fee structures
3. Token configuration
   - Token addresses
   - Decimals
   - WETH address

### Config Validation
1. Required fields checked
2. Address validation
3. Network compatibility check
4. Fee validation
5. Token address checksumming

## Memory Management

### Caching Pattern
1. Contract instances cached
2. ABI definitions cached
3. Token information cached
4. Price data cached with TTL
5. Gas estimates cached

### State Management
1. DEX state tracked
2. Initialization state verified
3. Enabled/disabled state managed
4. Error state tracking
5. Performance metrics tracked

## Monitoring and Metrics

### Logging Pattern
1. Standardized log format
2. Context-aware logging
3. Error tracking
4. Performance monitoring
5. Debug mode configuration

### Performance Tracking
1. Gas usage tracking
2. Transaction success rate
3. Price impact monitoring
4. Liquidity depth tracking
5. Slow operation detection

## Security Patterns

### Input Validation
1. Address validation
2. Amount validation
3. Path validation
4. Fee validation
5. Token address checksumming

### Transaction Safety
1. Slippage protection
2. Gas price limits
3. Transaction deadlines
4. Balance verification
5. Quote validation

## Testing Patterns

### Test Categories
1. Unit tests for base classes
2. Integration tests for DEX implementations
3. Contract interaction tests
4. Configuration tests
5. Performance tests

### Test Data
1. Mock contracts
2. Test networks
3. Sample configurations
4. Transaction scenarios
5. Performance benchmarks

### Async Testing
1. Async test cases
2. Concurrent operation testing
3. Resource cleanup verification
4. Lock management testing
5. Error recovery testing
