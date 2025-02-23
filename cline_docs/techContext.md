# Technical Context

## Development Environment
- Python 3.12+ (required for improved async support)
- Web3.py for blockchain interaction
- Pure asyncio for async/await patterns
- VSCode as primary IDE

## Core Dependencies
- web3>=7.0.0 (for blockchain interaction)
- aiohttp>=3.9.0 (for async HTTP and WebSocket)
- asyncio (Python's built-in async library)
- logging (for system logging)
- decimal (for precise calculations)
- typing (for type hints)

## Technical Requirements

### Async Implementation Strategy
IMPORTANT: This project uses pure asyncio/async/await patterns. We DO NOT use eventlet or gevent.

1. Core Async Patterns
   - All I/O operations must be async
   - All contract interactions must be async
   - All file operations must be async
   - Proper async context management
   - Resource cleanup must be async

2. Thread Safety
   - Lock management for shared resources
   - Double-checked locking pattern
   - Resource protection
   - State consistency
   - Concurrent access control

3. Resource Management
   - Async initialization
   - Proper cleanup
   - Resource monitoring
   - Error recovery
   - Performance tracking

### DEX Integration
1. WETH Address Handling
   - Required in base configuration
   - Must be valid checksum address
   - Injected into all DEX instances
   - Used for price calculations
   - Consistent checksumming

2. Contract Interactions
   - Async methods required
   - Retry mechanism with backoff
   - Gas estimation
   - Transaction validation
   - Contract existence verification

3. Event Handling
   - Proper ABI loading required
   - Event filters for monitoring
   - Async event processing
   - Error recovery
   - Performance monitoring

### Configuration Management
1. Required Fields
   - WETH address
   - Router address
   - Factory address
   - Token configurations
   - DEX-specific settings

2. Validation Requirements
   - Address checksum validation
   - Network compatibility check
   - Required field presence
   - Type validation
   - Contract existence check

### Error Handling
1. Standardization
   - Context preservation
   - Proper logging
   - Error categorization
   - Recovery mechanisms
   - Performance impact tracking

2. Retry Logic
   - Exponential backoff
   - Maximum retry limits
   - Timeout handling
   - Error differentiation
   - Performance monitoring

## Technical Constraints

### Network Constraints
- Base network compatibility
- RPC endpoint requirements
- Gas price limitations
- Block time considerations
- Network resilience

### Memory Constraints
- Contract instance caching
- Event filter management
- Price data caching
- State management
- Performance optimization

### Performance Requirements
1. Transaction Speed
   - Quick price checks
   - Efficient path finding
   - Fast execution
   - Low latency
   - Performance monitoring

2. Resource Usage
   - Minimal memory footprint
   - Efficient CPU usage
   - Network optimization
   - Storage efficiency
   - Debug mode control

### Security Requirements
1. Input Validation
   - Address validation
   - Amount validation
   - Path validation
   - Permission checks
   - Token validation

2. Transaction Safety
   - Slippage protection
   - Gas price limits
   - Balance verification
   - Deadline enforcement
   - Quote validation

## Implementation Notes

### Critical Components
1. DEX Manager
   - Central coordination
   - Instance management
   - Configuration handling
   - State tracking
   - Performance monitoring

2. Web3 Manager
   - Contract management
   - Transaction handling
   - Gas optimization
   - Network interaction
   - Address validation

3. Event System
   - Event monitoring
   - State updates
   - Alert generation
   - Data collection
   - Performance tracking

### Integration Points
1. Contract Integration
   - ABI loading
   - Method calls
   - Event handling
   - State tracking
   - Performance monitoring

2. Price Integration
   - Oracle integration
   - Price calculation
   - Impact assessment
   - Validation
   - Performance tracking

3. Network Integration
   - RPC connection
   - Transaction submission
   - Block monitoring
   - Network status
   - Performance optimization

## Testing Requirements

### Unit Testing
- Base class testing
- Method validation
- Error handling
- State management
- Performance testing

### Integration Testing
- Contract interaction
- Event handling
- Price calculation
- Transaction flow
- Performance benchmarking

### Performance Testing
- Response times
- Resource usage
- Network latency
- Transaction speed
- Debug mode impact

### Security Testing
- Input validation
- Transaction safety
- Error handling
- Permission checks
- Token validation

### Async Testing
1. Core Testing
   - Async method testing
   - Lock management testing
   - Resource cleanup testing
   - Error recovery testing
   - Performance testing

2. Concurrency Testing
   - Lock contention testing
   - Race condition testing
   - Resource sharing testing
   - State consistency testing
   - Error propagation testing

3. Resource Testing
   - Resource initialization testing
   - Resource cleanup testing
   - Resource leak testing
   - Performance impact testing
   - Error handling testing

## Migration Notes
As of February 2025, we have migrated from eventlet to pure asyncio/async/await patterns:
- All eventlet code has been removed
- All components use proper async/await
- Thread safety has been implemented
- Resource management has been enhanced
- Performance has been optimized

This migration provides:
- Better async support
- Improved error handling
- Enhanced performance
- Better resource management
- Cleaner code structure

Last Updated: 2025-02-23
