# System Architecture Patterns

## Configuration Management
- Production config in configs/production.json
- Required sections:
  * web3: RPC and chain settings
  * flashbots: Authentication and relay settings
  * balancer: Vault addresses
  * tokens: Token addresses and decimals
- Validation through config_loader.py
- Default values for optional settings

## Authentication Patterns
1. Wallet Authentication:
   - Private key in web3.wallet_key
   - Used for transaction signing
   - Requires ETH for gas
   - Implemented through SignerMiddleware

2. Flashbots Authentication:
   - Separate key in flashbots.auth_key
   - Used only for bundle signing
   - No funds required
   - Generated through scripts/generate_flashbots_auth.py

## Middleware Patterns
1. Transaction Signing:
   - Class-based SignerMiddleware
   - make_request method implementation
   - Transaction parameter modification
   - Raw transaction signing
   - Error propagation

2. Web3 Integration:
   - Middleware registration
   - Chain-specific configuration
   - Error handling
   - State management
   - Request modification

3. Request Flow:
   - Parameter validation
   - Transaction signing
   - Request modification
   - Response handling
   - Error propagation

## Integration Patterns
1. Flash Loan Integration:
   - Balancer as primary provider
   - Async transaction building
   - Profit validation before execution
   - Resource cleanup after use

2. Flashbots Integration:
   - Private transaction routing
   - Bundle optimization
   - MEV protection
   - Profit simulation

3. DEX Integration:
   - Base class inheritance
   - V2/V3 specialization
   - Async pool discovery
   - Price impact calculation

## Resource Management
1. Initialization:
   - Web3 client setup
   - DEX manager creation
   - Flash loan setup
   - Flashbots provider initialization
   - Middleware registration

2. Cleanup:
   - Resource release
   - Connection cleanup
   - Lock management
   - Error handling

## Error Handling
1. Configuration Errors:
   - Missing fields validation
   - Type checking
   - Format validation
   - Default values

2. Runtime Errors:
   - Transaction failures
   - Network issues
   - Liquidity problems
   - Price impact limits
   - Middleware errors

3. Recovery Patterns:
   - Retry mechanisms
   - Fallback options
   - State preservation
   - Logging and monitoring

## Security Patterns
1. Key Management:
   - Separate authentication keys
   - Secure storage
   - Access control
   - Key rotation

2. Transaction Security:
   - Slippage protection
   - Price validation
   - Gas optimization
   - MEV protection
   - Middleware validation

3. Error Prevention:
   - Input validation
   - State verification
   - Balance checks
   - Profit confirmation
   - Middleware checks

## Performance Patterns
1. Async Operations:
   - Pure asyncio implementation
   - Parallel processing
   - Batch operations
   - Resource pooling
   - Middleware efficiency

2. Caching:
   - Price data caching
   - Pool information
   - Token data
   - Configuration
   - Transaction data

3. Optimization:
   - Gas usage
   - Path finding
   - Bundle submission
   - Flash loan execution
   - Middleware overhead

## Monitoring Patterns
1. Logging:
   - Structured logging
   - Error tracking
   - Performance metrics
   - Success rates
   - Middleware events

2. Metrics:
   - Profit tracking
   - Gas usage
   - Execution time
   - Success rate
   - Middleware performance

Remember: These patterns should be consistently applied across all new development and updates to maintain system integrity and performance.
