# Listonian Arbitrage Bot

A sophisticated arbitrage system for capturing profit opportunities across decentralized exchanges with dynamic balance allocation, MEV protection, and flash loan integration.

## Quick Start

To deploy the arbitrage system to production:

```bash
# Using PowerShell
pwsh -ExecutionPolicy Bypass -File .\deploy_production.ps1

# Using Command Prompt
.\start_production.bat
```

## Key Features

- **Dynamic Balance Allocation** - Automatically scales position sizes based on available funds
- **MEV Protection** - Defends against front-running and sandwich attacks
- **Flash Loan Integration** - Utilizes flash loans for capital-efficient arbitrage
- **Multi-DEX Support** - Works with multiple decentralized exchanges
- **Safety-First Design** - Multiple layers of protection to ensure profitability

## System Components

- **PathFinder** - Discovers optimal arbitrage paths
- **BalanceAllocator** - Manages dynamic position sizing
- **AsyncFlashLoanManager** - Handles flash loan operations
- **MEV Protection Optimizer** - Secures transactions against MEV
- **Web3Manager** - Manages blockchain interactions
- **DexManager** - Coordinates DEX operations

## Monitoring Dashboard

The system includes a comprehensive monitoring dashboard:

```bash
# Start the dashboard
python start_dashboard.py
# Or use the batch file
.\start_dashboard.bat
```

Dashboard features:
- Real-time arbitrage opportunity tracking
- Balance and allocation monitoring
- Historical trade performance analytics
- DEX pricing and liquidity analysis
- System status and health monitoring

## Configuration

The system is highly configurable through JSON configuration files:

```
configs/example_production_config.json  # Example config with documentation
```

Key configuration sections:

1. **Dynamic Allocation** - Controls trade sizing based on wallet balance
2. **Flash Loans** - Sets profit thresholds and slippage tolerance
3. **MEV Protection** - Configures transaction protection parameters

## Documentation

Comprehensive documentation is available in the `cline_docs` directory:

- [Configuration Guide](cline_docs/arbitrage_configuration_guide.md) - Detailed parameter explanations
- [Implementation Summary](cline_docs/implementation_summary.md) - System architecture overview
- [Supported DEXes](cline_docs/supported_dexes.md) - Details on integrated exchanges
- [Active Context](cline_docs/activeContext.md) - Current project state
- [Progress](cline_docs/progress.md) - Implementation status

## Utility Scripts

- `deploy_production.ps1` - Full production deployment
- `run_test.ps1` - Run system tests
- `start_dashboard.bat` - Start the monitoring dashboard
- `start_production.bat` - Start the system in production mode

## Safety Features

The system implements multiple layers of protection:

1. **Profit Validation** - Ensures trades remain profitable after all costs
2. **Slippage Control** - Enforced at smart contract level
3. **Balance Management** - Reserves funds for operational safety
4. **Transaction Simulation** - Pre-validates outcomes before execution

## System Requirements

- Python 3.12+
- Web3.py
- Ethereum node access
- Sufficient ETH for gas and initial trades

## License

See [LICENSE](LICENSE) file for details.

## Acknowledgements

- Uniswap/Sushiswap/etc for DEX protocols
- Flashbots for MEV protection
- Balancer for flash loan capabilities
