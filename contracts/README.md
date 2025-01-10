# Smart Contracts Directory

## Structure

- `v2/`, `v3/`, `v4/` - Historical versions of the arbitrage bot
- `ArbitrageBotV5.sol` - Current production version
- `interfaces/` - Contract interfaces and external contract definitions
- `utils/` - Utility contracts and libraries
- `dex/` - DEX-specific implementations
- `monitoring/` - Monitoring and safety contracts
- `mocks/` - Mock contracts for testing

## Version History

### V5 (Current)
- Enhanced security features
- Circuit breaker implementation
- Flash loan integration
- Emergency withdrawal system
- Gas optimization improvements

### V4
- Initial flash loan implementation
- Basic security features
- Multi-DEX support

### V3
- Multiple token pair support
- Basic profit calculation

### V2
- Initial implementation
- Single token pair support

## Development Guidelines

1. All new features should be added to V5
2. Maintain backward compatibility when possible
3. Document all state variables and functions
4. Include events for important state changes
5. Add comprehensive test coverage for new features

## Security Considerations

- All contracts must pass security audit before mainnet deployment
- Follow the security checklist in SECURITY_CHECKLIST.json
- Implement proper access controls
- Use SafeERC20 for token transfers
- Include circuit breakers and pause mechanisms
